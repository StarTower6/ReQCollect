"""Phase 1: Conversational requirement mining using ReAct agent."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.prebuilt import create_react_agent
from loguru import logger

from app.agent.pm.phase1.sufficiency import evaluate_profile_sufficiency, evaluate_sufficiency
from app.agent.pm.prompts import PM_SYSTEM_PROMPT
from app.agent.pm.tools import (
    get_profile_summary,
    reset_current_thread_id,
    set_current_thread_id,
    set_pending_questions,
    update_requirement_profile,
)
from app.config import config
from app.core.llm_factory import llm_factory
from app.tools import get_current_time, retrieve_knowledge


class MiningAgent:

    # Isolate fresh runs from older Redis checkpoints that may have been created
    # before DeepSeek thinking mode was disabled for tool-calling requests.
    CHECKPOINT_NS = "thinking-disabled-v1"

    def _checkpoint_thread_id(self, thread_id: str) -> str:
        return f"{self.CHECKPOINT_NS}__{thread_id}"

    def __init__(self):
        self.pm_tools = [
            retrieve_knowledge,
            get_current_time,
            update_requirement_profile,
            get_profile_summary,
            set_pending_questions,
            evaluate_sufficiency,
        ]
        self.model = llm_factory.create_chat_model(
            model=config.rag_model,
            temperature=0.7,
            streaming=True,
        )
        self._checkpointer: AsyncRedisSaver | None = None
        self._checkpointer_cm = None
        self._agent = None

    async def _get_checkpointer(self) -> AsyncRedisSaver:
        if self._checkpointer is None:
            self._checkpointer_cm = AsyncRedisSaver.from_conn_string(config.redis_url)
            self._checkpointer = await self._checkpointer_cm.__aenter__()
        return self._checkpointer

    async def _get_agent(self):
        if self._agent is None:
            checkpointer = await self._get_checkpointer()
            self._agent = create_react_agent(
                self.model,
                tools=self.pm_tools,
                checkpointer=checkpointer,
            )
        return self._agent

    async def _retrieve_knowledge_context(self, message: str) -> tuple[str, int]:
        try:
            context, docs = await asyncio.to_thread(retrieve_knowledge.func, message)
            return context, len(docs)
        except Exception as e:
            logger.warning(f"Forced knowledge retrieval failed [query={message[:80]}]: {e}")
            return f"Search error: {e}", 0

    async def chat(
        self,
        message: str,
        thread_id: str = "default",
        force_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a user message and yield SSE events.

        Args:
            message: User's message
            thread_id: Session thread ID

        Yields:
            Dict events: content, profile_update, sufficiency, ready_to_generate
        """
        context_token = set_current_thread_id(thread_id)
        try:
            agent = await self._get_agent()
            config_dict = {
                "configurable": {
                    "thread_id": self._checkpoint_thread_id(thread_id),
                }
            }

            user_message = message
            if force_knowledge:
                yield {
                    "type": "knowledge",
                    "data": {"status": "searching", "query": message},
                }
                knowledge_context, knowledge_count = await self._retrieve_knowledge_context(message)
                yield {
                    "type": "knowledge",
                    "data": {"status": "done", "count": knowledge_count},
                }
                user_message = (
                    "用户开启了知识检索。请优先结合下面的知识库检索结果进行需求挖掘；"
                    "如果没有检索到相关文档，则按通用产品经理方法继续追问。\n\n"
                    f"[知识库检索结果]\n{knowledge_context}\n\n"
                    f"[用户原始消息]\n{message}"
                )

            messages = [
                SystemMessage(content=PM_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]

            async for token, _metadata in agent.astream(
                input={"messages": messages},
                config=config_dict,
                stream_mode="messages",
            ):
                msg_type = type(token).__name__
                if msg_type in ("AIMessage", "AIMessageChunk"):
                    text = getattr(token, 'content', '')
                    if text and isinstance(text, str):
                        yield {"type": "content", "data": text}

            # Always refresh readiness in code; do not rely on the model to call the tool.
            result = evaluate_profile_sufficiency(thread_id)
            score = result.score

            yield {
                "type": "sufficiency",
                "data": {
                    "score": score,
                    "threshold": config.sufficiency_threshold,
                    "missing_fields": result.missing_fields,
                    "suggested_questions": result.suggested_questions,
                }
            }

            if score >= config.sufficiency_threshold:
                yield {
                    "type": "ready_to_generate",
                    "data": {
                        "message": "Information looks sufficient. Would you like me to generate the PRD?",
                        "score": score,
                    }
                }

        except Exception as e:
            logger.error(f"Mining agent error [thread={thread_id}]: {e}")
            yield {"type": "error", "data": str(e)}
        finally:
            reset_current_thread_id(context_token)

    async def flush_profile_to_checkpoint(self, thread_id: str) -> None:
        """Persist the in-memory profile to the Redis checkpoint state."""
        from app.agent.pm.tools import get_profile
        profile = get_profile(thread_id)
        checkpointer = await self._get_checkpointer()
        config_dict = {
            "configurable": {
                "thread_id": self._checkpoint_thread_id(thread_id),
            }
        }
        await checkpointer.aput(
            config_dict,
            {"profile": profile},
            step=0,
            checkpoint_id=thread_id,
            metadata={},
        )

    async def close(self):
        if self._checkpointer_cm is not None:
            await self._checkpointer_cm.__aexit__(None, None, None)
            self._checkpointer_cm = None
            self._checkpointer = None
            self._agent = None


_mining_agent: MiningAgent | None = None


def get_mining_agent() -> MiningAgent:
    global _mining_agent
    if _mining_agent is None:
        _mining_agent = MiningAgent()
    return _mining_agent
