"""Phase 1: Conversational requirement mining using ReAct agent (Lite: no Redis checkpoint)."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from app.agent.pm.phase1.sufficiency import evaluate_profile_sufficiency, evaluate_sufficiency
from app.agent.pm.prompts import PM_SYSTEM_PROMPT
from app.agent.pm.tools import (
    get_profile_summary,
    get_workspace_info,
    list_workspace_files,
    read_file_section,
    read_workspace_file,
    reset_current_thread_id,
    search_in_workspace,
    set_current_thread_id,
    set_pending_questions,
    update_requirement_profile,
    write_workspace_file,
)
from app.config import config
from app.core.llm_factory import llm_factory


def get_current_time(query: str = "") -> str:
    """Get the current date and time. Useful for time-sensitive context."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def retrieve_knowledge(query: str, top_k: int = 3) -> str:
    """Search domain knowledge base. (Stub: no vector store deployed.)"""
    return "知识库未部署，当前无法提供检索结果。请按通用产品经理方法继续追问。"


class MiningAgent:

    def __init__(self):
        self.pm_tools = [
            retrieve_knowledge,
            get_current_time,
            update_requirement_profile,
            get_profile_summary,
            set_pending_questions,
            evaluate_sufficiency,
            # 新增文件工具
            list_workspace_files,
            read_workspace_file,
            read_file_section,
            search_in_workspace,
            write_workspace_file,
            get_workspace_info,
        ]
        self.model = llm_factory.create_chat_model(
            model=config.llm_model,
            temperature=0.7,
            streaming=True,
        )
        # Use in-memory checkpoint instead of Redis
        self._checkpointer = MemorySaver()
        self._agent = None

    async def _get_agent(self):
        if self._agent is None:
            self._agent = create_react_agent(
                self.model,
                tools=self.pm_tools,
                checkpointer=self._checkpointer,
            )
        return self._agent

    async def chat(
        self,
        message: str,
        thread_id: str = "default",
        force_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a user message and yield SSE events."""
        async for event in self.chat_with_context(
            message=message,
            thread_id=thread_id,
            force_knowledge=force_knowledge,
        ):
            yield event

    async def chat_with_context(
        self,
        message: str,
        thread_id: str = "default",
        system_prompt_override: str | None = None,
        context_messages: list[dict] | None = None,
        force_knowledge: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a user message with optional context injection.

        Args:
            message: The user's current message.
            thread_id: Session/thread identifier.
            system_prompt_override: If provided, replaces the default PM_SYSTEM_PROMPT.
            context_messages: Additional messages to prepend (e.g. document content
                              as SystemMessage or HumanMessage). Each dict must have
                              'role' ('system'|'user'|'assistant') and 'content' keys.
            force_knowledge: Whether to force knowledge retrieval.

        Yields SSE event dicts.
        """
        context_token = set_current_thread_id(thread_id)
        try:
            agent = await self._get_agent()
            config_dict = {
                "configurable": {
                    "thread_id": thread_id,
                }
            }

            user_message = message
            if force_knowledge:
                yield {
                    "type": "knowledge",
                    "data": {"status": "searching", "query": message},
                }
                knowledge_context = await asyncio.to_thread(retrieve_knowledge, message)
                yield {
                    "type": "knowledge",
                    "data": {"status": "done", "count": 0},
                }
                user_message = (
                    "用户开启了知识检索。请优先结合下面的知识库检索结果进行需求挖掘；"
                    "如果没有检索到相关文档，则按通用产品经理方法继续追问。\n\n"
                    f"[知识库检索结果]\n{knowledge_context}\n\n"
                    f"[用户原始消息]\n{message}"
                )

            # Build message list with optional context injection
            messages: list = [
                SystemMessage(content=system_prompt_override or PM_SYSTEM_PROMPT),
            ]

            # Inject context messages (e.g. document content) before user message
            if context_messages:
                for ctx_msg in context_messages:
                    role = ctx_msg.get("role", "user")
                    content = ctx_msg.get("content", "")
                    if role == "system":
                        messages.append(SystemMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
                    else:
                        messages.append(HumanMessage(content=content))

            messages.append(HumanMessage(content=user_message))

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
                        "message": "信息比较充分了，要我生成 PRD 吗？",
                        "score": score,
                    }
                }

        except Exception as e:
            logger.error(f"Mining agent error [thread={thread_id}]: {e}")
            yield {"type": "error", "data": str(e)}
        finally:
            reset_current_thread_id(context_token)

    async def close(self):
        self._agent = None


_mining_agent: MiningAgent | None = None


def get_mining_agent() -> MiningAgent:
    global _mining_agent
    if _mining_agent is None:
        _mining_agent = MiningAgent()
    return _mining_agent
