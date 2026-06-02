"""Remote embeddings via OpenAI compatible API (e.g. SiliconFlow, local embedding service)."""


from langchain_core.embeddings import Embeddings
from loguru import logger
from openai import OpenAI

from app.config import config


class RemoteEmbeddings(Embeddings):

    def __init__(self, api_key: str, base_url: str, model: str = "BAAI/bge-m3", dimensions: int = 1024):
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY is required")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.dimensions = dimensions
        logger.info(f"RemoteEmbeddings initialized: model={model}, dims={dimensions}, base_url={base_url}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty")
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float",
        )
        return response.data[0].embedding


_embedding_service: RemoteEmbeddings | None = None


def get_embedding_service() -> RemoteEmbeddings:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = RemoteEmbeddings(
            api_key=config.embedding_api_key or config.deepseek_api_key,
            base_url=config.embedding_base_url,
            model=config.embedding_model,
            dimensions=1024,
        )
    return _embedding_service
