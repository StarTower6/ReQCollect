"""Vector search tool for domain knowledge retrieval."""


from langchain_core.documents import Document
from langchain_core.tools import tool
from loguru import logger

from app.config import config
from app.services.vector_store_manager import vector_store_manager


def format_docs(docs: list[Document]) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        metadata = doc.metadata
        source = metadata.get("_file_name", "unknown")
        headers = []
        for key in ["h1", "h2", "h3"]:
            if key in metadata and metadata[key]:
                headers.append(metadata[key])
        header_str = " > ".join(headers) if headers else ""
        formatted = f"[Ref {i}]"
        if header_str:
            formatted += f"\nTitle: {header_str}"
        formatted += f"\nSource: {source}"
        formatted += f"\nContent:\n{doc.page_content}\n"
        parts.append(formatted)
    return "\n".join(parts)


@tool(response_format="content_and_artifact")
def retrieve_knowledge(query: str) -> tuple[str, list[Document]]:
    """Search the knowledge base for relevant domain experience and best practices.

    Use this when you need to reference industry knowledge, similar project
    experiences, or domain-specific requirement patterns.

    Args:
        query: Search query describing what knowledge you need

    Returns:
        Tuple of (formatted context string, list of source documents)
    """
    try:
        logger.info(f"Knowledge search: '{query}'")
        vector_store = vector_store_manager.get_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": config.rag_top_k})
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant documents found.", []
        context = format_docs(docs)
        logger.info(f"Found {len(docs)} relevant documents")
        return context, docs
    except Exception as e:
        logger.error(f"Knowledge search failed: {e}")
        return f"Search error: {str(e)}", []
