"""LLM factory using ChatOpenAI via DeepSeek official API."""

from langchain_openai import ChatOpenAI

from app.config import config

DEEPSEEK_EXTRA_BODY = {"thinking": {"type": "disabled"}}


class LLMFactory:

    @staticmethod
    def create_chat_model(
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = True,
    ) -> ChatOpenAI:
        model = model or config.deepseek_model
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=streaming,
            base_url=config.deepseek_base_url,
            api_key=config.deepseek_api_key,
            extra_body=DEEPSEEK_EXTRA_BODY,
        )


llm_factory = LLMFactory()
