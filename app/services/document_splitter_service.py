"""Document splitter using LangChain splitters."""

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config import config


class DocumentSplitterService:

    def __init__(self):
        self.chunk_size = config.chunk_max_size
        self.chunk_overlap = config.chunk_overlap
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2")],
            strip_headers=False,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size * 2,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def split_document(self, content: str, file_path: str = "") -> list[Document]:
        if not content or not content.strip():
            return []
        if file_path.endswith(".md"):
            return self._split_markdown(content, file_path)
        else:
            return self._split_text(content, file_path)

    def _split_markdown(self, content: str, file_path: str) -> list[Document]:
        md_docs = self.markdown_splitter.split_text(content)
        docs = self.text_splitter.split_documents(md_docs)
        final_docs = self._merge_small_chunks(docs, min_size=300)
        for doc in final_docs:
            doc.metadata["_source"] = file_path
            doc.metadata["_extension"] = ".md"
            doc.metadata["_file_name"] = Path(file_path).name
        return final_docs

    def _split_text(self, content: str, file_path: str) -> list[Document]:
        docs = self.text_splitter.create_documents(
            texts=[content],
            metadatas=[{
                "_source": file_path,
                "_extension": Path(file_path).suffix,
                "_file_name": Path(file_path).name,
            }],
        )
        return docs

    def _merge_small_chunks(self, documents: list[Document], min_size: int = 300) -> list[Document]:
        if not documents:
            return []
        merged = []
        current = None
        for doc in documents:
            if current is None:
                current = doc
            elif len(doc.page_content) < min_size and len(current.page_content) < self.chunk_size * 2:
                current.page_content += "\n\n" + doc.page_content
            else:
                merged.append(current)
                current = doc
        if current is not None:
            merged.append(current)
        return merged


document_splitter_service = DocumentSplitterService()
