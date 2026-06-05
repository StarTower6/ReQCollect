"""LLM factory using ChatOpenAI — compatible with any OpenAI-compatible API.

Explicitly disables proxy to avoid httpx issues with corporate proxy env vars.
"""

import httpx
from langchain_openai import ChatOpenAI

from app.config import config


class LLMFactory:

    @staticmethod
    def create_chat_model(
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = True,
    ) -> ChatOpenAI:
        model = model or config.llm_model
        # Create an httpx client that ignores proxy env vars
        http_client = httpx.Client(
            follow_redirects=True,
            transport=httpx.HTTPTransport(
                proxy=None,  # explicitly disable proxy
                retries=3,
            ),
        )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=streaming,
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            http_client=http_client,
        )


llm_factory = LLMFactory()
