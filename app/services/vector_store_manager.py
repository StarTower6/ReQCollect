"""Milvus VectorStore wrapper using langchain_milvus."""


from langchain_core.documents import Document
from langchain_milvus import Milvus
from loguru import logger

from app.config import config
from app.core.milvus_client import milvus_manager
from app.services.vector_embedding_service import get_embedding_service

COLLECTION_NAME = "pm_knowledge"


class VectorStoreManager:

    def __init__(self):
        self.collection_name = COLLECTION_NAME
        self.vector_store = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        try:
            milvus_manager.connect()
            connection_args = {"uri": f"http://{config.milvus_host}:{config.milvus_port}"}
            self.vector_store = Milvus(
                embedding_function=get_embedding_service(),
                collection_name=self.collection_name,
                connection_args=connection_args,
                auto_id=False,
                drop_old=False,
                text_field="content",
                vector_field="vector",
                primary_field="id",
                metadata_field="metadata",
            )
            self._initialized = True
            logger.info(f"VectorStore initialized: {self.collection_name}")
        except Exception as e:
            logger.error(f"VectorStore init failed: {e}")
            raise

    def _ensure_initialized(self):
        if not self._initialized:
            self.initialize()

    def add_documents(self, documents: list[Document]) -> list[str]:
        self._ensure_initialized()
        import uuid
        ids = [str(uuid.uuid4()) for _ in documents]
        return self.vector_store.add_documents(documents, ids=ids)

    def delete_by_source(self, file_path: str) -> int:
        self._ensure_initialized()
        try:
            collection = milvus_manager.get_collection()
            expr = f'metadata["_source"] == "{file_path}"'
            result = collection.delete(expr)
            return result.delete_count if hasattr(result, "delete_count") else 0
        except Exception as e:
            logger.warning(f"Delete old data failed (may be first index): {e}")
            return 0

    def get_vector_store(self) -> Milvus:
        self._ensure_initialized()
        return self.vector_store

    def similarity_search(self, query: str, k: int = 3) -> list[Document]:
        self._ensure_initialized()
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []


vector_store_manager = VectorStoreManager()
