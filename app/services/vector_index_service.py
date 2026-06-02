"""Vector indexing service for file uploads."""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from app.services.document_splitter_service import document_splitter_service
from app.services.vector_store_manager import vector_store_manager


class IndexingResult:

    def __init__(self):
        self.success = False
        self.total_files = 0
        self.success_count = 0
        self.fail_count = 0
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.error_message = ""
        self.failed_files: dict[str, str] = {}

    def to_dict(self) -> dict[str, Any]:
        duration_ms = 0
        if self.start_time and self.end_time:
            duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        return {
            "success": self.success,
            "total_files": self.total_files,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "duration_ms": duration_ms,
            "error_message": self.error_message,
            "failed_files": self.failed_files,
        }


class VectorIndexService:

    def __init__(self):
        self.upload_path = "./uploads"

    def index_single_file(self, file_path: str) -> None:
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            raise ValueError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        normalized_path = path.as_posix()
        vector_store_manager.delete_by_source(normalized_path)
        documents = document_splitter_service.split_document(content, normalized_path)
        if documents:
            vector_store_manager.add_documents(documents)
        logger.info(f"Indexed file: {file_path}, chunks: {len(documents)}")


vector_index_service = VectorIndexService()
