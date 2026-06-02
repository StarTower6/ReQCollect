# PM Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PM Agent that converses like a senior product manager to mine software requirements, then generates professional PRD documents.

**Architecture:** Two-phase hybrid — Phase 1 uses LangGraph ReAct agent for conversational requirement mining with a shared RequirementProfile state; Phase 2 uses a sequential pipeline to generate PRD sections from the profile. Redis-backed checkpointing for LangGraph session state. MySQL for persistent storage of requirement profiles, generated PRDs, and session metadata. Multi-node Docker deployment with nginx load balancing.

**Tech Stack:** FastAPI, LangGraph, LangChain, DeepSeek V4 (via SiliconFlow OpenAI-compatible API), Milvus, Redis, MySQL, SQLAlchemy (async), sse-starlette, Loguru, Docker, docker-compose, nginx

**Source project for reference:** `D:/WorkProject/super_biz_agent_py-release/super_biz_agent_py-release/`

---

## File Structure Map

```
pm_agent/
├── .env
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
│
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── .env
├── .env.docker
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
│
├── app/
│   ├── __init__.py
│   ├── config.py                          # pydantic-settings
│   ├── main.py                            # FastAPI app entry
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py                    # Async SQLAlchemy engine + session
│   │   ├── models.py                      # SQLAlchemy ORM models
│   │   └── repository.py                  # Data access layer
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm_factory.py                 # ChatOpenAI factory
│   │   └── milvus_client.py               # Milvus client manager
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py                      # Loguru setup
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── knowledge_tool.py              # Vector search tool
│   │   └── time_tool.py                   # Current time tool
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── vector_embedding_service.py    # SiliconFlow embeddings
│   │   ├── vector_store_manager.py        # Milvus VectorStore wrapper
│   │   ├── document_splitter_service.py   # Markdown/text splitter
│   │   ├── vector_index_service.py        # File indexing pipeline
│   │   └── pm_agent_service.py            # Two-phase orchestrator + SSE
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── pm.py                          # Request/response Pydantic models
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── pm.py                          # PM Agent HTTP endpoints
│   │
│   └── agent/
│       └── pm/
│           ├── __init__.py
│           ├── state.py                   # RequirementProfile TypedDict
│           ├── prompts.py                 # PM persona + PRD template
│           ├── tools.py                   # PM-specific @tools
│           │
│           ├── phase1/
│           │   ├── __init__.py
│           │   ├── mining_agent.py        # ReAct PM dialog agent
│           │   └── sufficiency.py         # Information sufficiency evaluator
│           │
│           └── phase2/
│               ├── __init__.py
│               ├── planner.py             # PRD section planner
│               ├── generator.py           # Per-section content generator
│               └── assembler.py           # Markdown assembly + incremental control
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_state.py
│   ├── test_tools.py
│   ├── test_sufficiency.py
│   ├── test_phase1_mining_agent.py
│   ├── test_phase2_planner.py
│   ├── test_phase2_generator.py
│   ├── test_pm_agent_service.py
│   └── test_api_pm.py
│
├── static/
│   └── index.html                         # Chat frontend
│
├── uploads/                               # Uploaded files staging
│
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-05-23-pm-agent-design.md
        └── plans/
            └── 2026-05-23-pm-agent-plan.md
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `pm_agent/.gitignore`
- Create: `pm_agent/.python-version`
- Create: `pm_agent/.env`
- Create: `pm_agent/pyproject.toml`
- Create: `pm_agent/README.md`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/

# Environment
.env
.env.local

# Logs
logs/
*.log

# Uploads
uploads/*

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Milvus
volumes/

# Coverage
htmlcov/
.coverage
```

- [ ] **Step 2: Create .python-version**

```
3.11
```

- [ ] **Step 3: Create .env**

```env
# App
APP_NAME=PM Agent
DEBUG=True
HOST=0.0.0.0
PORT=9900

# SiliconFlow (OpenAI compatible)
SILICONFLOW_API_KEY=sk-your-key-here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V4-Flash
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-m3

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_TIMEOUT=10000

# RAG
RAG_TOP_K=5
RAG_MODEL=deepseek-ai/DeepSeek-V4-Flash

# Document chunking
CHUNK_MAX_SIZE=800
CHUNK_OVERLAP=100

# Redis
REDIS_URL=redis://localhost:6379

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=pm_agent
MYSQL_PASSWORD=pm_agent_pass
MYSQL_DATABASE=pm_agent
DATABASE_URL=mysql+aiomysql://pm_agent:pm_agent_pass@localhost:3306/pm_agent

# PM Agent
SUFFICIENCY_THRESHOLD=0.75
```

- [ ] **Step 4: Create pyproject.toml**

```toml
[project]
name = "pm-agent"
version = "0.1.0"
description = "AI Product Manager Agent - automated requirement mining and PRD generation"
authors = [{name = "chief"}]
readme = "README.md"
requires-python = ">=3.11,<3.14"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sse-starlette>=2.1.0",
    "langchain>=0.1.0",
    "langchain-community>=0.0.20",
    "langchain-core>=0.1.0",
    "langchain-openai>=1.0.0",
    "langgraph>=0.3.0",
    "langgraph-checkpoint-redis>=0.1.0",
    "openai>=1.10.0",
    "pymilvus>=2.3.5",
    "pydantic>=2.5.0,<3.0.0",
    "pydantic-settings>=2.1.0",
    "httpx>=0.26.0",
    "aiohttp>=3.9.0",
    "aiofiles>=23.2.0",
    "python-multipart>=0.0.6",
    "loguru>=0.7.2",
    "python-dotenv>=1.0.0",
    "langchain-milvus>=0.3.3",
    "langchain-text-splitters>=1.1.0",
    "redis>=5.0.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "aiomysql>=0.2.0",
    "alembic>=1.13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.12.0",
    "ruff>=0.1.9",
    "isort>=5.13.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "W", "F", "I", "C", "B", "UP"]
ignore = ["E501", "B008", "C901", "W191"]
exclude = [".git", "__pycache__", ".venv", "venv", "logs", "*.pyc", "*.egg-info"]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]

[tool.pytest.ini_options]
minversion = "7.0"
addopts = ["-ra", "-q", "--strict-markers"]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
asyncio_mode = "auto"
```

- [ ] **Step 5: Create empty directories**

```bash
mkdir -p pm_agent/app/core
mkdir -p pm_agent/app/utils
mkdir -p pm_agent/app/tools
mkdir -p pm_agent/app/services
mkdir -p pm_agent/app/models
mkdir -p pm_agent/app/api
mkdir -p pm_agent/app/agent/pm/phase1
mkdir -p pm_agent/app/agent/pm/phase2
mkdir -p pm_agent/tests
mkdir -p pm_agent/static
mkdir -p pm_agent/uploads
mkdir -p pm_agent/logs
```

- [ ] **Step 6: Create empty __init__.py files**

```bash
touch pm_agent/app/__init__.py
touch pm_agent/app/core/__init__.py
touch pm_agent/app/utils/__init__.py
touch pm_agent/app/tools/__init__.py
touch pm_agent/app/services/__init__.py
touch pm_agent/app/models/__init__.py
touch pm_agent/app/api/__init__.py
touch pm_agent/app/agent/__init__.py
touch pm_agent/app/agent/pm/__init__.py
touch pm_agent/app/agent/pm/phase1/__init__.py
touch pm_agent/app/agent/pm/phase2/__init__.py
touch pm_agent/tests/__init__.py
```

- [ ] **Step 7: Create virtual env and install dependencies**

```bash
cd D:/WorkProject/pm_agent
python -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev]"
```

- [ ] **Step 8: Commit**

```bash
cd D:/WorkProject/pm_agent
git init
git add -A
git commit -m "chore: scaffold pm-agent project with dependencies and config"
```

---

### Task 2: Config and Logger

**Files:**
- Create: `pm_agent/app/config.py`
- Create: `pm_agent/app/utils/logger.py`

- [ ] **Step 1: Write config.py**

```python
"""PM Agent configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PM Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9900

    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "deepseek-ai/DeepSeek-V4-Flash"
    siliconflow_embedding_model: str = "BAAI/bge-m3"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_timeout: int = 10000

    rag_top_k: int = 5
    rag_model: str = "deepseek-ai/DeepSeek-V4-Flash"

    chunk_max_size: int = 800
    chunk_overlap: int = 100

    redis_url: str = "redis://localhost:6379"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "pm_agent"
    mysql_password: str = "pm_agent_pass"
    mysql_database: str = "pm_agent"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    sufficiency_threshold: float = 0.75


config = Settings()
```

- [ ] **Step 2: Write utils/logger.py**

```python
"""Loguru logger setup."""

import sys
from loguru import logger
from app.config import config


def setup_logger():
    logger.remove()

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>.<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level="DEBUG" if config.debug else "INFO",
        colorize=True,
        backtrace=True,
        diagnose=config.debug,
    )

    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}.{function}:{line} | {message}",
    )


setup_logger()
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py app/utils/logger.py
git commit -m "feat: add config and logger modules"
```

---

### Task 3: Core Infrastructure (LLM + Milvus + Embedding)

**Files:**
- Create: `pm_agent/app/core/llm_factory.py`
- Create: `pm_agent/app/core/milvus_client.py`
- Create: `pm_agent/app/services/vector_embedding_service.py`

- [ ] **Step 1: Write core/llm_factory.py**

```python
"""LLM factory using ChatOpenAI via SiliconFlow."""

from langchain_openai import ChatOpenAI
from app.config import config


class LLMFactory:

    @staticmethod
    def create_chat_model(
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = True,
    ) -> ChatOpenAI:
        model = model or config.siliconflow_model
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=streaming,
            base_url=config.siliconflow_base_url,
            api_key=config.siliconflow_api_key,
        )


llm_factory = LLMFactory()
```

- [ ] **Step 2: Write core/milvus_client.py**

Copy from reference project `app/core/milvus_client.py` with collection name changed to `"pm_knowledge"`:

```python
"""Milvus client manager."""

from loguru import logger
from pymilvus import (
    Collection, CollectionSchema, DataType, FieldSchema,
    MilvusClient, connections, utility, MilvusException,
)

try:
    import scipy.sparse  # noqa: F401
    from pymilvus.client.utils import SciPyHelper
    SciPyHelper._init()
except ImportError:
    pass

from app.config import config


def _patch_pymilvus_milvus_client_orm_alias() -> None:
    if getattr(_patch_pymilvus_milvus_client_orm_alias, "_done", False):
        return
    try:
        from pymilvus.milvus_client.milvus_client import MilvusClient
    except ImportError:
        return

    _orig_init = MilvusClient.__init__

    def _wrapped_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        self._using = "default"

    MilvusClient.__init__ = _wrapped_init
    setattr(_patch_pymilvus_milvus_client_orm_alias, "_done", True)


class MilvusClientManager:
    COLLECTION_NAME: str = "pm_knowledge"
    VECTOR_DIM: int = 1024
    ID_MAX_LENGTH: int = 100
    CONTENT_MAX_LENGTH: int = 8000
    DEFAULT_SHARD_NUMBER: int = 2

    def __init__(self) -> None:
        self._client: MilvusClient | None = None
        self._collection: Collection | None = None

    def connect(self) -> MilvusClient:
        if self._collection is not None and self._client is not None:
            logger.debug("Milvus already connected, checking collection load state...")
            self._load_collection()
            return self._client

        try:
            _patch_pymilvus_milvus_client_orm_alias()
            logger.info(f"Connecting to Milvus: {config.milvus_host}:{config.milvus_port}")

            connections.connect(
                alias="default",
                host=config.milvus_host,
                port=str(config.milvus_port),
                timeout=config.milvus_timeout / 1000,
            )

            uri = f"http://{config.milvus_host}:{config.milvus_port}"
            self._client = MilvusClient(uri=uri)
            logger.info("Connected to Milvus")

            if not self._collection_exists():
                logger.info(f"Creating collection '{self.COLLECTION_NAME}'...")
                self._create_collection()
            else:
                self._collection = Collection(self.COLLECTION_NAME)
                schema = self._collection.schema
                for field in schema.fields:
                    if field.name == "vector" and hasattr(field, 'params'):
                        existing_dim = field.params.get('dim')
                        if existing_dim and existing_dim != self.VECTOR_DIM:
                            logger.warning(f"Vector dimension mismatch: {existing_dim} vs {self.VECTOR_DIM}")
                            utility.drop_collection(self.COLLECTION_NAME)
                            self._create_collection()
                        break

            self._load_collection()
            return self._client

        except (MilvusException, ConnectionError) as e:
            logger.error(f"Milvus connection failed: {e}")
            self.close()
            raise RuntimeError(f"Milvus connection failed: {e}") from e

    def _collection_exists(self) -> bool:
        return bool(utility.has_collection(self.COLLECTION_NAME))

    def _create_collection(self) -> None:
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=self.ID_MAX_LENGTH, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.VECTOR_DIM),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=self.CONTENT_MAX_LENGTH),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]
        schema = CollectionSchema(fields=fields, description="PM knowledge collection", enable_dynamic_field=False)
        self._collection = Collection(name=self.COLLECTION_NAME, schema=schema, num_shards=self.DEFAULT_SHARD_NUMBER)
        self._create_index()

    def _create_index(self) -> None:
        if self._collection is None:
            raise RuntimeError("Collection not initialized")
        index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        self._collection.create_index(field_name="vector", index_params=index_params)
        logger.info("Vector index created")

    def _load_collection(self) -> None:
        if self._collection is None:
            self._collection = Collection(self.COLLECTION_NAME)
        try:
            load_state = utility.load_state(self.COLLECTION_NAME)
            state_name = getattr(load_state, "name", str(load_state))
            if state_name != "Loaded":
                self._collection.load()
        except AttributeError:
            try:
                self._collection.load()
            except MilvusException as e:
                if "already loaded" not in str(e).lower():
                    raise

    def get_collection(self) -> Collection:
        if self._collection is None:
            raise RuntimeError("Collection not initialized, call connect() first")
        return self._collection

    def health_check(self) -> bool:
        try:
            if self._client is None:
                return False
            connections.list_connections()
            return True
        except Exception:
            return False

    def close(self) -> None:
        try:
            if self._collection is not None:
                self._collection.release()
                self._collection = None
        except Exception:
            pass
        try:
            if connections.has_connection("default"):
                connections.disconnect("default")
        except Exception:
            pass
        self._client = None


milvus_manager = MilvusClientManager()
```

- [ ] **Step 3: Write services/vector_embedding_service.py**

```python
"""SiliconFlow embeddings via OpenAI compatible API."""

from typing import List
from langchain_core.embeddings import Embeddings
from openai import OpenAI
from loguru import logger
from app.config import config


class SiliconFlowEmbeddings(Embeddings):

    def __init__(self, api_key: str, model: str = "BAAI/bge-m3", dimensions: int = 1024):
        if not api_key:
            raise ValueError("SILICONFLOW_API_KEY is required")
        self.client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")
        self.model = model
        self.dimensions = dimensions
        logger.info(f"SiliconFlowEmbeddings initialized: model={model}, dims={dimensions}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.model, input=texts, dimensions=self.dimensions, encoding_format="float"
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty")
        response = self.client.embeddings.create(
            model=self.model, input=text, dimensions=self.dimensions, encoding_format="float"
        )
        return response.data[0].embedding


vector_embedding_service = SiliconFlowEmbeddings(
    api_key=config.siliconflow_api_key,
    model=config.siliconflow_embedding_model,
    dimensions=1024,
)
```

- [ ] **Step 4: Commit**

```bash
git add app/core/ app/services/vector_embedding_service.py
git commit -m "feat: add LLM factory, Milvus client, and embedding service"
```

---

### Task 4: Vector Store Manager

**Files:**
- Create: `pm_agent/app/services/vector_store_manager.py`

- [ ] **Step 1: Write vector_store_manager.py**

```python
"""Milvus VectorStore wrapper using langchain_milvus."""

from typing import List
from langchain_core.documents import Document
from langchain_milvus import Milvus
from loguru import logger
from app.config import config
from app.core.milvus_client import milvus_manager
from app.services.vector_embedding_service import vector_embedding_service

COLLECTION_NAME = "pm_knowledge"


class VectorStoreManager:

    def __init__(self):
        self.collection_name = COLLECTION_NAME
        self.vector_store = None
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        try:
            milvus_manager.connect()
            connection_args = {"host": config.milvus_host, "port": config.milvus_port}
            self.vector_store = Milvus(
                embedding_function=vector_embedding_service,
                collection_name=self.collection_name,
                connection_args=connection_args,
                auto_id=False,
                drop_old=False,
                text_field="content",
                vector_field="vector",
                primary_field="id",
                metadata_field="metadata",
            )
            logger.info(f"VectorStore initialized: {self.collection_name}")
        except Exception as e:
            logger.error(f"VectorStore init failed: {e}")
            raise

    def add_documents(self, documents: List[Document]) -> List[str]:
        import uuid
        ids = [str(uuid.uuid4()) for _ in documents]
        return self.vector_store.add_documents(documents, ids=ids)

    def delete_by_source(self, file_path: str) -> int:
        try:
            collection = milvus_manager.get_collection()
            expr = f'metadata["_source"] == "{file_path}"'
            result = collection.delete(expr)
            return result.delete_count if hasattr(result, "delete_count") else 0
        except Exception as e:
            logger.warning(f"Delete old data failed (may be first index): {e}")
            return 0

    def get_vector_store(self) -> Milvus:
        return self.vector_store

    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []


vector_store_manager = VectorStoreManager()
```

- [ ] **Step 2: Commit**

```bash
git add app/services/vector_store_manager.py
git commit -m "feat: add VectorStore manager for Milvus"
```

---

### Task 5: Document Splitter and Index Services

**Files:**
- Create: `pm_agent/app/services/document_splitter_service.py`
- Create: `pm_agent/app/services/vector_index_service.py`

- [ ] **Step 1: Write document_splitter_service.py**

```python
"""Document splitter using LangChain splitters."""

from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from loguru import logger
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

    def split_document(self, content: str, file_path: str = "") -> List[Document]:
        if not content or not content.strip():
            return []
        if file_path.endswith(".md"):
            return self._split_markdown(content, file_path)
        else:
            return self._split_text(content, file_path)

    def _split_markdown(self, content: str, file_path: str) -> List[Document]:
        md_docs = self.markdown_splitter.split_text(content)
        docs = self.text_splitter.split_documents(md_docs)
        final_docs = self._merge_small_chunks(docs, min_size=300)
        for doc in final_docs:
            doc.metadata["_source"] = file_path
            doc.metadata["_extension"] = ".md"
            doc.metadata["_file_name"] = Path(file_path).name
        return final_docs

    def _split_text(self, content: str, file_path: str) -> List[Document]:
        docs = self.text_splitter.create_documents(
            texts=[content],
            metadatas=[{
                "_source": file_path,
                "_extension": Path(file_path).suffix,
                "_file_name": Path(file_path).name,
            }],
        )
        return docs

    def _merge_small_chunks(self, documents: List[Document], min_size: int = 300) -> List[Document]:
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
```

- [ ] **Step 2: Write vector_index_service.py**

```python
"""Vector indexing service for file uploads."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict
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
        self.failed_files: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
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
```

- [ ] **Step 3: Commit**

```bash
git add app/services/document_splitter_service.py app/services/vector_index_service.py
git commit -m "feat: add document splitter and vector index services"
```

---

### Task 6: Shared Tools

**Files:**
- Create: `pm_agent/app/tools/__init__.py`
- Create: `pm_agent/app/tools/knowledge_tool.py`
- Create: `pm_agent/app/tools/time_tool.py`

- [ ] **Step 1: Write tools/__init__.py**

```python
from app.tools.knowledge_tool import retrieve_knowledge
from app.tools.time_tool import get_current_time

__all__ = ["retrieve_knowledge", "get_current_time"]
```

- [ ] **Step 2: Write tools/knowledge_tool.py**

```python
"""Vector search tool for domain knowledge retrieval."""

from typing import List, Tuple
from langchain_core.documents import Document
from langchain_core.tools import tool
from loguru import logger
from app.config import config
from app.services.vector_store_manager import vector_store_manager


def format_docs(docs: List[Document]) -> str:
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
def retrieve_knowledge(query: str) -> Tuple[str, List[Document]]:
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
```

- [ ] **Step 3: Write tools/time_tool.py**

```python
"""Current time tool."""

from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool
from loguru import logger


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """Get the current date and time.

    Use this when you need to know the current time, date, or day of week.

    Args:
        timezone: Timezone string, defaults to Asia/Shanghai

    Returns:
        Formatted datetime string
    """
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return now.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception as e:
        logger.error(f"Time tool failed: {e}")
        return f"Failed to get time: {str(e)}"
```

- [ ] **Step 4: Commit**

```bash
git add app/tools/
git commit -m "feat: add shared tools (knowledge search, time)"
```

---

### Task 7: PM Agent State and Prompts

**Files:**
- Create: `pm_agent/app/agent/pm/state.py`
- Create: `pm_agent/app/agent/pm/prompts.py`

- [ ] **Step 1: Write state.py**

```python
"""PM Agent state definitions."""

from typing import List, TypedDict, Annotated
import operator


class RequirementProfile(TypedDict, total=False):
    """Structured requirement profile — the bridge between Phase 1 and Phase 2."""

    project_name: str
    project_type: str
    industry: str
    elevator_pitch: str

    user_roles: list  # [{"role": "admin", "desc": "...", "concerns": [...]}]
    functional_modules: list  # [{"module": "auth", "features": [...], "priority": "P0"}]
    non_functional: dict  # {"performance": "...", "security": "...", ...}

    constraints: List[str]
    assumptions: List[str]

    covered_topics: List[str]
    pending_questions: List[str]
    sufficiency_score: float


class PMState(TypedDict):
    """Full PM Agent session state persisted in Redis checkpoint."""

    messages: Annotated[list, operator.add]
    profile: RequirementProfile
    phase: str  # "mining" | "generating" | "complete"
    generation_mode: str  # "one_shot" | "incremental"
    prd_sections: list  # [{"title": "...", "content": "...", "status": "pending|done"}]
    prd_markdown: str
```

- [ ] **Step 2: Write prompts.py**

```python
"""PM persona prompt and PRD template."""

from textwrap import dedent

PM_SYSTEM_PROMPT = dedent("""
You are a senior product manager with 10+ years of experience in software
requirements analysis. Your job is to have a natural conversation with the
user to deeply understand what they need to build, then document it as a PRD.

## Your Workflow

1. **Understand the business context** — what industry, who are the users,
   what problem are we solving?
2. **Dig deeper progressively** — user roles → core workflows → functional
   modules → edge cases and constraints
3. **Ask proactive questions** — when the user is vague, guide them with
   specific options. For example: "Should the approval be single-person or
   multi-person countersign?" instead of "How should approval work?"
4. **Reference experience** — use `search_domain_knowledge` to find relevant
   patterns and best practices from similar projects
5. **Record in real-time** — use `update_requirement_profile` to save every
   insight you extract from the conversation
6. **Self-check coverage** — use `get_profile_summary` to see what's covered
   and what's still missing
7. **Rate readiness** — use `evaluate_sufficiency` to score how complete the
   requirements are

## Conversation Principles

- Ask only 1-2 questions at a time, never bombard the user
- Lead with concrete options, not open-ended questions
- Gently steer back when the user goes off-topic
- Acknowledge what you've learned before asking the next question
- When sufficiency score reaches 0.75, suggest generating the PRD

## Tone

Professional but warm. You're a helpful partner, not an interrogator.
Use Chinese when the user speaks Chinese, English when they speak English.
""").strip()

PRD_SECTION_TEMPLATES = {
    "project_overview": {
        "title": "1. 项目概述",
        "prompt": dedent("""
            Write the "Project Overview" section of a PRD based on the
            requirement profile below. Include: project background, goals,
            target users, and project scope.

            Profile:
            {profile_context}
        """).strip(),
    },
    "user_roles": {
        "title": "2. 用户角色分析",
        "prompt": dedent("""
            Write the "User Role Analysis" section of a PRD. For each user
            role, describe their responsibilities, pain points, and core needs.

            Profile:
            {profile_context}
        """).strip(),
    },
    "functional_requirements": {
        "title": "3. 功能需求",
        "prompt": dedent("""
            Write the "Functional Requirements" section of a PRD. For each
            module, list specific features with priority (P0/P1/P2), detailed
            descriptions, and acceptance criteria.

            Profile:
            {profile_context}
        """).strip(),
    },
    "non_functional": {
        "title": "4. 非功能需求",
        "prompt": dedent("""
            Write the "Non-Functional Requirements" section. Cover:
            performance, security, scalability, usability, reliability,
            and compliance requirements.

            Profile:
            {profile_context}
        """).strip(),
    },
    "business_flow": {
        "title": "5. 业务流程",
        "prompt": dedent("""
            Write the "Business Process" section. Describe the key business
            workflows, step by step. Include main flow and alternative flows.

            Profile:
            {profile_context}
        """).strip(),
    },
    "constraints": {
        "title": "6. 系统约束与假设",
        "prompt": dedent("""
            Write the "System Constraints & Assumptions" section. List all
            technical constraints, business constraints, and assumptions made.

            Profile:
            {profile_context}
        """).strip(),
    },
    "acceptance": {
        "title": "7. 验收标准",
        "prompt": dedent("""
            Write the "Acceptance Criteria" section. Define measurable
            criteria for each functional module that must be met before
            the feature is considered complete.

            Profile:
            {profile_context}
        """).strip(),
    },
    "appendix": {
        "title": "8. 附录",
        "prompt": dedent("""
            Write the "Appendix" section. Include: glossary of terms,
            referenced documents, and any additional context.

            Profile:
            {profile_context}
        """).strip(),
    },
}

PRD_SECTION_ORDER = [
    "project_overview",
    "user_roles",
    "functional_requirements",
    "non_functional",
    "business_flow",
    "constraints",
    "acceptance",
    "appendix",
]
```

- [ ] **Step 3: Commit**

```bash
git add app/agent/pm/state.py app/agent/pm/prompts.py
git commit -m "feat: add PM agent state definitions and prompts"
```

---

### Task 8: PM Agent Tools

**Files:**
- Create: `pm_agent/app/agent/pm/tools.py`

- [ ] **Step 1: Write agent/pm/tools.py**

```python
"""PM-specific LangChain tools for requirement profile management."""

import json
from typing import Optional
from langchain_core.tools import tool
from loguru import logger


_profile_store: dict[str, dict] = {}


def get_profile_store() -> dict[str, dict]:
    return _profile_store


def get_profile(thread_id: str) -> dict:
    if thread_id not in _profile_store:
        _profile_store[thread_id] = {
            "project_name": "",
            "project_type": "",
            "industry": "",
            "elevator_pitch": "",
            "user_roles": [],
            "functional_modules": [],
            "non_functional": {},
            "constraints": [],
            "assumptions": [],
            "covered_topics": [],
            "pending_questions": [],
            "sufficiency_score": 0.0,
        }
    return _profile_store[thread_id]


@tool
def update_requirement_profile(
    field: str,
    value: str,
    thread_id: str = "default",
) -> str:
    """Update a field in the requirement profile.

    Use this to record every insight you extract from the conversation.
    Call it immediately after the user confirms or clarifies a requirement.

    Args:
        field: The profile field to update. One of:
            project_name, project_type, industry, elevator_pitch,
            user_roles (JSON array string), functional_modules (JSON array string),
            non_functional (JSON object string), constraints (JSON array string),
            assumptions (JSON array string), covered_topics (JSON array string),
            pending_questions (JSON array string)
        value: The value to set. For list/dict fields, pass a JSON string.
        thread_id: Session thread ID

    Returns:
        Confirmation of what was updated
    """
    profile = get_profile(thread_id)
    list_fields = {"user_roles", "functional_modules", "constraints",
                   "assumptions", "covered_topics", "pending_questions"}
    dict_fields = {"non_functional"}

    if field in list_fields:
        try:
            profile[field] = json.loads(value)
        except json.JSONDecodeError:
            profile[field] = [value]
    elif field in dict_fields:
        try:
            profile[field] = json.loads(value)
        except json.JSONDecodeError:
            profile[field] = {"raw": value}
    else:
        profile[field] = value

    logger.info(f"[{thread_id}] Profile updated: {field}")
    return f"Requirement profile field '{field}' updated successfully."


@tool
def get_profile_summary(thread_id: str = "default") -> str:
    """Get a summary of the current requirement profile.

    Use this to check what you've already covered and what's still missing.
    Call it before deciding what to ask next.

    Args:
        thread_id: Session thread ID

    Returns:
        Summary of current profile state
    """
    profile = get_profile(thread_id)
    filled = {k: v for k, v in profile.items()
              if v and v != [] and v != {} and v != 0.0 and k not in ("pending_questions", "covered_topics", "sufficiency_score")}
    empty = [k for k, v in profile.items()
             if (v == "" or v == [] or v == {} or v == 0.0) and k not in ("pending_questions", "covered_topics", "sufficiency_score")]

    lines = ["## Current Requirement Profile Summary", ""]
    lines.append(f"**Score:** {profile.get('sufficiency_score', 0.0):.0%}")
    lines.append("")
    if filled:
        lines.append("### Covered")
        for k, v in filled.items():
            val_str = json.dumps(v, ensure_ascii=False)
            if len(val_str) > 120:
                val_str = val_str[:120] + "..."
            lines.append(f"- **{k}**: {val_str}")
    if empty:
        lines.append("")
        lines.append("### Not Yet Covered")
        for k in empty:
            lines.append(f"- {k}")
    if profile.get("pending_questions"):
        lines.append("")
        lines.append("### Pending Questions")
        for q in profile["pending_questions"]:
            lines.append(f"- {q}")
    return "\n".join(lines)


@tool
def set_pending_questions(questions_json: str, thread_id: str = "default") -> str:
    """Set the list of questions you still need to ask the user.

    Args:
        questions_json: JSON array of question strings
        thread_id: Session thread ID

    Returns:
        Confirmation
    """
    profile = get_profile(thread_id)
    try:
        profile["pending_questions"] = json.loads(questions_json)
    except json.JSONDecodeError:
        profile["pending_questions"] = [questions_json]
    return f"Pending questions updated: {len(profile['pending_questions'])} questions."
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/pm/tools.py
git commit -m "feat: add PM-specific tools for requirement profile management"
```

---

### Task 9: Information Sufficiency Evaluator

**Files:**
- Create: `pm_agent/app/agent/pm/phase1/sufficiency.py`

- [ ] **Step 1: Write phase1/sufficiency.py**

```python
"""Information sufficiency evaluator for requirement profiles."""

from typing import Optional
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from loguru import logger
from app.config import config
from app.agent.pm.tools import get_profile


class SufficiencyResult(BaseModel):
    score: float = Field(description="Sufficiency score 0.0 to 1.0")
    missing_fields: list[str] = Field(description="Fields that still need to be filled")
    suggested_questions: list[str] = Field(description="Suggested questions to ask the user next")
    reasoning: str = Field(description="Brief reasoning for the score")


@tool
def evaluate_sufficiency(thread_id: str = "default") -> str:
    """Evaluate how complete the current requirement profile is.

    Returns a score (0.0-1.0), list of missing fields, and suggested
    next questions. Call this after each round of profile updates to
    decide whether to continue mining or suggest generating the PRD.

    Args:
        thread_id: Session thread ID

    Returns:
        Structured evaluation result
    """
    profile = get_profile(thread_id)
    profile_json = {
        k: v for k, v in profile.items()
        if k != "sufficiency_score"
    }

    evaluator_llm = ChatOpenAI(
        model=config.rag_model,
        api_key=config.siliconflow_api_key,
        base_url=config.siliconflow_base_url,
        temperature=0,
    )

    prompt = f"""Evaluate the completeness of this software requirement profile.

Profile:
{profile_json}

Score from 0.0 to 1.0 based on:
- 0.0-0.3: Only project name/type known, very little detail
- 0.3-0.5: Basic info filled, but user roles and functional modules missing
- 0.5-0.7: User roles defined, some functional modules, non-functional missing
- 0.7-0.85: Most fields populated, minor gaps remain
- 0.85-1.0: Comprehensive, ready for PRD generation

Identify which fields are still missing and suggest 2-3 specific questions
to ask the user next."""

    try:
        structured_llm = evaluator_llm.with_structured_output(SufficiencyResult)
        result: SufficiencyResult = structured_llm.invoke(prompt)

        profile["sufficiency_score"] = result.score

        return (
            f"**Sufficiency Score: {result.score:.0%}**\n"
            f"**Reasoning:** {result.reasoning}\n"
            f"**Missing:** {', '.join(result.missing_fields)}\n"
            f"**Suggested next questions:**\n- "
            + "\n- ".join(result.suggested_questions)
        )
    except Exception as e:
        logger.error(f"Sufficiency evaluation failed: {e}")
        return f"Evaluation error: {str(e)}"
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/pm/phase1/sufficiency.py
git commit -m "feat: add information sufficiency evaluator"
```

---

### Task 10: Phase 1 — Mining Agent (ReAct)

**Files:**
- Create: `pm_agent/app/agent/pm/phase1/mining_agent.py`

- [ ] **Step 1: Write phase1/mining_agent.py**

```python
"""Phase 1: Conversational requirement mining using ReAct agent."""

from typing import AsyncGenerator, Any
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.redis import AsyncRedisSaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from app.config import config
from app.agent.pm.prompts import PM_SYSTEM_PROMPT
from app.agent.pm.tools import (
    update_requirement_profile,
    get_profile_summary,
    set_pending_questions,
)
from app.agent.pm.phase1.sufficiency import evaluate_sufficiency
from app.tools import retrieve_knowledge, get_current_time


class MiningAgent:

    def __init__(self):
        self.pm_tools = [
            retrieve_knowledge,
            get_current_time,
            update_requirement_profile,
            get_profile_summary,
            set_pending_questions,
            evaluate_sufficiency,
        ]
        self.model = ChatOpenAI(
            model=config.rag_model,
            api_key=config.siliconflow_api_key,
            base_url=config.siliconflow_base_url,
            temperature=0.7,
            streaming=True,
        )
        self._checkpointer: AsyncRedisSaver | None = None
        self._agent = None

    async def _get_checkpointer(self) -> AsyncRedisSaver:
        if self._checkpointer is None:
            self._checkpointer = AsyncRedisSaver.from_conn_string(config.redis_url)
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

    async def chat(
        self,
        message: str,
        thread_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process a user message and yield SSE events.

        Args:
            message: User's message
            thread_id: Session thread ID

        Yields:
            Dict events: content, profile_update, sufficiency, ready_to_generate
        """
        try:
            agent = await self._get_agent()
            config_dict = {"configurable": {"thread_id": thread_id}}

            messages = [
                SystemMessage(content=PM_SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]

            async for token, metadata in agent.astream(
                input={"messages": messages},
                config=config_dict,
                stream_mode="messages",
            ):
                msg_type = type(token).__name__
                if msg_type in ("AIMessage", "AIMessageChunk"):
                    text = getattr(token, 'content', '')
                    if text and isinstance(text, str):
                        yield {"type": "content", "data": text}

            # After response, evaluate sufficiency
            from app.agent.pm.tools import get_profile
            profile = get_profile(thread_id)
            score = profile.get("sufficiency_score", 0.0)

            yield {
                "type": "sufficiency",
                "data": {
                    "score": score,
                    "threshold": config.sufficiency_threshold,
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

    async def flush_profile_to_checkpoint(self, thread_id: str) -> None:
        """Persist the in-memory profile to the Redis checkpoint state."""
        from app.agent.pm.tools import get_profile
        profile = get_profile(thread_id)
        checkpointer = await self._get_checkpointer()
        config_dict = {"configurable": {"thread_id": thread_id}}
        await checkpointer.aput(
            config_dict,
            {"profile": profile},
            step=0,
            checkpoint_id=thread_id,
            metadata={},
        )

    async def close(self):
        if self._checkpointer is not None:
            await self._checkpointer.aclose()
            self._checkpointer = None
            self._agent = None


mining_agent = MiningAgent()
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/pm/phase1/mining_agent.py
git commit -m "feat: add Phase 1 mining agent (ReAct with Redis checkpoint)"
```

---

### Task 11: Phase 2 — PRD Planner

**Files:**
- Create: `pm_agent/app/agent/pm/phase2/planner.py`

- [ ] **Step 1: Write phase2/planner.py**

```python
"""Phase 2: PRD section planner."""

from app.agent.pm.prompts import PRD_SECTION_ORDER, PRD_SECTION_TEMPLATES
from loguru import logger


class PRDPlanner:

    def __init__(self):
        self.sections = [
            {
                "key": key,
                "title": PRD_SECTION_TEMPLATES[key]["title"],
                "status": "pending",
            }
            for key in PRD_SECTION_ORDER
        ]

    def plan(self, profile: dict, mode: str = "one_shot") -> list[dict]:
        """Plan PRD sections based on the requirement profile.

        Args:
            profile: The completed RequirementProfile
            mode: "one_shot" or "incremental"

        Returns:
            List of section dicts with key, title, status, and prompt
        """
        sections = []
        for key in PRD_SECTION_ORDER:
            template = PRD_SECTION_TEMPLATES[key]
            prompt = template["prompt"].format(
                profile_context=self._format_profile(profile)
            )
            sections.append({
                "key": key,
                "title": template["title"],
                "status": "pending",
                "prompt": prompt,
                "content": "",
            })
        logger.info(f"PRD plan created: {len(sections)} sections, mode={mode}")
        return sections

    def _format_profile(self, profile: dict) -> str:
        import json
        return json.dumps(profile, ensure_ascii=False, indent=2)


prd_planner = PRDPlanner()
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/pm/phase2/planner.py
git commit -m "feat: add Phase 2 PRD section planner"
```

---

### Task 12: Phase 2 — Generator and Assembler

**Files:**
- Create: `pm_agent/app/agent/pm/phase2/generator.py`
- Create: `pm_agent/app/agent/pm/phase2/assembler.py`

- [ ] **Step 1: Write phase2/generator.py**

```python
"""Phase 2: Per-section PRD content generator."""

from typing import AsyncGenerator
from langchain_openai import ChatOpenAI
from loguru import logger
from app.config import config


class SectionGenerator:

    def __init__(self):
        self.model = ChatOpenAI(
            model=config.rag_model,
            api_key=config.siliconflow_api_key,
            base_url=config.siliconflow_base_url,
            temperature=0.3,
            streaming=True,
        )

    async def generate(
        self,
        section: dict,
    ) -> AsyncGenerator[str, None]:
        """Generate content for a single PRD section.

        Args:
            section: Section dict with 'title', 'prompt'

        Yields:
            Content string chunks (tokens)
        """
        logger.info(f"Generating section: {section['title']}")
        full_prompt = (
            f"Write the following PRD section in professional Markdown.\n"
            f"Section title: {section['title']}\n\n"
            f"{section['prompt']}\n\n"
            f"Output only the section content in Markdown. Start with the "
            f"section heading `## {section['title']}`."
        )

        async for chunk in self.model.astream(full_prompt):
            content = getattr(chunk, 'content', '')
            if content:
                yield content


section_generator = SectionGenerator()
```

- [ ] **Step 2: Write phase2/assembler.py**

```python
"""Phase 2: PRD document assembler with incremental control."""

from typing import AsyncGenerator, Any
from loguru import logger
from app.agent.pm.phase2.generator import section_generator


class PRDAssembler:

    async def assemble(
        self,
        sections: list[dict],
        profile: dict,
        mode: str = "one_shot",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Assemble the full PRD by generating each section.

        Args:
            sections: List of section dicts from planner
            profile: Requirement profile
            mode: "one_shot" or "incremental"

        Yields:
            SSE events: prd_plan, section_start, section_content,
            section_complete, awaiting_approval, prd_complete
        """
        # Emit the plan
        plan_summary = [{"key": s["key"], "title": s["title"]} for s in sections]
        yield {
            "type": "prd_plan",
            "data": {
                "sections": plan_summary,
                "mode": mode,
            }
        }

        # Generate title
        title = f"# {profile.get('project_name', 'Product Requirements Document')}\n\n"
        title += f"> {profile.get('elevator_pitch', '')}\n\n"
        title += "---\n\n"
        full_markdown = title

        for i, section in enumerate(sections):
            yield {
                "type": "section_start",
                "data": {
                    "section_key": section["key"],
                    "title": section["title"],
                    "index": i + 1,
                    "total": len(sections),
                }
            }

            section_content = ""
            async for chunk in section_generator.generate(section):
                section_content += chunk
                yield {"type": "section_content", "data": chunk}

            section["content"] = section_content
            section["status"] = "done"
            full_markdown += section_content + "\n\n"

            yield {
                "type": "section_complete",
                "data": {
                    "section_key": section["key"],
                    "title": section["title"],
                    "content": section_content,
                    "index": i + 1,
                    "total": len(sections),
                }
            }

            if mode == "incremental" and i < len(sections) - 1:
                yield {
                    "type": "awaiting_approval",
                    "data": {
                        "message": f"Section '{section['title']}' complete. Continue to '{sections[i+1]['title']}'?",
                        "next_section": sections[i+1]["title"],
                    }
                }

        yield {
            "type": "prd_complete",
            "data": {
                "markdown": full_markdown,
                "sections": [{"key": s["key"], "title": s["title"], "status": s["status"]}
                           for s in sections],
            }
        }


prd_assembler = PRDAssembler()
```

- [ ] **Step 3: Commit**

```bash
git add app/agent/pm/phase2/generator.py app/agent/pm/phase2/assembler.py
git commit -m "feat: add Phase 2 PRD section generator and assembler"
```

---

### Task 13: PM Agent Service (Multi-Endpoint + Unified Wrapper)

**Files:**
- Create: `pm_agent/app/services/pm_agent_service.py`

- [ ] **Step 1: Write pm_agent_service.py**

```python
"""PM Agent service — individual endpoints for each phase + unified wrapper.

Core endpoints:
  - chat(message, thread_id)        → Phase 1 mining
  - generate_prd(thread_id, mode)   → Phase 2 full generation
  - continue_generation(thread_id)  → Phase 2 incremental next section

Convenience wrapper:
  - handle(message, thread_id, mode) → auto-routes based on intent
"""

from typing import AsyncGenerator, Any
from loguru import logger
from app.config import config
from app.agent.pm.tools import get_profile
from app.agent.pm.phase1.mining_agent import mining_agent
from app.agent.pm.phase2.planner import prd_planner
from app.agent.pm.phase2.assembler import prd_assembler

_session_state: dict[str, dict] = {}


def _get_session(thread_id: str) -> dict:
    if thread_id not in _session_state:
        _session_state[thread_id] = {
            "mode": "one_shot",
            "prd_sections": None,
            "current_section_index": 0,
        }
    return _session_state[thread_id]


def _detect_intent(message: str) -> str:
    """Returns 'generate' | 'continue' | 'chat'."""
    gen_kw = ["生成prd", "生成文档", "生成需求", "写prd", "写文档",
              "出文档", "开始写", "开始生成", "出需求文档", "输出prd", "输出文档"]
    cont_kw = ["继续", "下一章", "next", "继续生成", "下一步"]

    msg = message.strip().lower()
    for kw in cont_kw:
        if kw in msg:
            return "continue"
    for kw in gen_kw:
        if kw in msg:
            return "generate"
    return "chat"


class PMAgentService:

    # ── Core endpoints (individually callable) ──

    async def chat(
        self, message: str, thread_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 1: Conversational requirement mining."""
        logger.info(f"[{thread_id}] Chat: {message[:100]}...")
        async for event in mining_agent.chat(message, thread_id):
            yield event

    async def generate_prd(
        self, thread_id: str = "default", mode: str = "one_shot",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 2: Full PRD generation from current profile."""
        logger.info(f"[{thread_id}] Generate PRD, mode={mode}")
        session = _get_session(thread_id)
        session["mode"] = mode

        profile = get_profile(thread_id)
        sections = prd_planner.plan(profile, mode)
        session["prd_sections"] = sections
        session["current_section_index"] = 0

        async for event in prd_assembler.assemble(sections, profile, mode):
            if event.get("type") == "prd_complete":
                await self._save_prd(thread_id, profile, mode, sections, event["data"]["markdown"])
            yield event

    async def continue_generation(
        self, thread_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Phase 2: Continue incremental generation from last completed section."""
        session = _get_session(thread_id)
        sections = session.get("prd_sections")
        if sections is None:
            async for event in self.generate_prd(thread_id, "incremental"):
                yield event
            return

        idx = session.get("current_section_index", 0)
        if idx >= len(sections):
            yield {"type": "status", "data": {"message": "All sections complete."}}
            return

        yield {"type": "status", "data": {"message": f"Continuing section {idx+1}/{len(sections)}..."}}

        for i in range(idx, len(sections)):
            section = sections[i]
            yield {"type": "section_start", "data": {
                "section_key": section["key"], "title": section["title"],
                "index": i+1, "total": len(sections),
            }}

            from app.agent.pm.phase2.generator import section_generator
            content = ""
            async for chunk in section_generator.generate(section):
                content += chunk
                yield {"type": "section_content", "data": chunk}

            section["content"] = content
            section["status"] = "done"
            session["current_section_index"] = i + 1

            yield {"type": "section_complete", "data": {
                "section_key": section["key"], "title": section["title"],
                "content": content, "index": i+1, "total": len(sections),
            }}

            if i < len(sections) - 1:
                yield {"type": "awaiting_approval", "data": {
                    "message": f"'{section['title']}' done. POST /api/pm/continue to proceed.",
                    "next_section": sections[i+1]["title"], "next_index": i + 1,
                }}
                return

        profile = get_profile(thread_id)
        title = f"# {profile.get('project_name', 'PRD')}\n\n"
        title += f"> {profile.get('elevator_pitch', '')}\n\n---\n\n"
        full_md = title + "\n\n".join(s["content"] for s in sections if s.get("content"))

        await self._save_prd(thread_id, profile, session["mode"], sections, full_md)
        yield {"type": "prd_complete", "data": {
            "markdown": full_md,
            "sections": [{"key": s["key"], "title": s["title"], "status": s.get("status","done")} for s in sections],
        }}

    # ── Convenience wrapper ──

    async def handle(
        self, message: str, thread_id: str = "default", mode: str = "one_shot",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Convenience wrapper: auto-routes based on message intent.

        - "生成PRD" etc. → generate_prd()
        - "继续" etc.    → continue_generation()
        - otherwise       → chat()
        """
        intent = _detect_intent(message)
        logger.info(f"[{thread_id}] handle, intent={intent}")

        if intent == "generate":
            async for event in self.generate_prd(thread_id, mode):
                yield event
        elif intent == "continue":
            async for event in self.continue_generation(thread_id):
                yield event
        else:
            async for event in self.chat(message, thread_id):
                yield event

    # ── Helpers ──

    async def _save_prd(self, thread_id: str, profile: dict, mode: str,
                        sections: list, markdown: str) -> None:
        try:
            from app.db.database import AsyncSessionLocal
            from app.db.repository import PRDRepository
            async with AsyncSessionLocal() as db_session:
                await PRDRepository.save(
                    db_session,
                    session_id=thread_id,
                    title=profile.get("project_name", "PRD"),
                    mode=mode,
                    sections=[{"key": s["key"], "title": s["title"], "status": s["status"]}
                              for s in sections],
                    markdown=markdown,
                )
            logger.info(f"[{thread_id}] PRD saved to MySQL")
        except Exception as e:
            logger.warning(f"[{thread_id}] Failed to save PRD to MySQL: {e}")

    async def get_profile(self, thread_id: str = "default") -> dict:
        return get_profile(thread_id)

    async def cleanup(self):
        await mining_agent.close()


pm_agent_service = PMAgentService()
```

- [ ] **Step 2: Commit**

```bash
git add app/services/pm_agent_service.py
git commit -m "feat: add PM agent service with individual endpoints + unified wrapper"
```

---

### Task 14: API Models and Routes

**Files:**
- Create: `pm_agent/app/models/pm.py`
- Create: `pm_agent/app/api/pm.py`

- [ ] **Step 1: Write models/pm.py**

```python
"""PM Agent request/response models."""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: str = Field(default="default", description="Session ID")

    model_config = {"json_schema_extra": {"example": {
        "message": "我想做一个企业报销审批系统", "session_id": "session-001",
    }}}


class GenerateRequest(BaseModel):
    session_id: str = Field(default="default", description="Session ID")
    mode: str = Field(default="one_shot", description="one_shot | incremental")

    model_config = {"json_schema_extra": {"example": {
        "session_id": "session-001", "mode": "incremental",
    }}}


class ContinueRequest(BaseModel):
    session_id: str = Field(default="default", description="Session ID")

    model_config = {"json_schema_extra": {"example": {
        "session_id": "session-001",
    }}}


class AgentRequest(BaseModel):
    """Convenience wrapper: auto-routes to chat / generate / continue."""
    message: str = Field(..., description="User message")
    session_id: str = Field(default="default", description="Session ID")
    mode: str = Field(default="one_shot", description="one_shot | incremental")

    model_config = {"json_schema_extra": {"example": {
        "message": "我想做一个企业报销审批系统", "session_id": "session-001", "mode": "one_shot",
    }}}
```

- [ ] **Step 2: Write api/pm.py**

```python
"""PM Agent API endpoints.

Core endpoints:
  POST /api/pm/chat       Phase 1: requirement mining dialog (SSE)
  POST /api/pm/generate   Phase 2: PRD generation (SSE)
  POST /api/pm/continue   Phase 2: incremental next section (SSE)
  POST /api/pm/agent      Convenience wrapper: auto-routes (SSE)
  POST /api/pm/upload     Upload domain knowledge docs
  GET  /api/pm/profile/{session_id}  View requirement profile
"""

import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from sse_starlette.sse import EventSourceResponse
from loguru import logger
from app.models.pm import ChatRequest, GenerateRequest, ContinueRequest, AgentRequest
from app.services.pm_agent_service import pm_agent_service
from app.services.vector_index_service import vector_index_service

router = APIRouter()


@router.post("/pm/chat")
async def pm_chat(request: ChatRequest):
    """Phase 1: Requirement mining dialog (SSE)."""
    logger.info(f"[{request.session_id}] Chat: {request.message[:100]}...")

    async def gen():
        async for event in pm_agent_service.chat(request.message, request.session_id):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/generate")
async def pm_generate(request: GenerateRequest):
    """Phase 2: Trigger PRD generation (SSE)."""
    logger.info(f"[{request.session_id}] Generate PRD, mode={request.mode}")

    async def gen():
        async for event in pm_agent_service.generate_prd(request.session_id, request.mode):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/continue")
async def pm_continue(request: ContinueRequest):
    """Phase 2: Continue incremental generation (SSE)."""
    logger.info(f"[{request.session_id}] Continue generation")

    async def gen():
        async for event in pm_agent_service.continue_generation(request.session_id):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/agent")
async def pm_agent(request: AgentRequest):
    """Convenience wrapper: auto-routes chat/generate/continue (SSE)."""
    logger.info(f"[{request.session_id}] Agent: {request.message[:100]}...")

    async def gen():
        async for event in pm_agent_service.handle(request.message, request.session_id, request.mode):
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/pm/upload")
async def pm_upload(file: UploadFile = File(...), session_id: str = Form(default="default")):
    """Upload domain knowledge document to Milvus."""
    try:
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        vector_index_service.index_single_file(str(file_path.resolve()))
        logger.info(f"[{session_id}] Uploaded: {file.filename}")
        return {"success": True, "filename": file.filename, "message": f"'{file.filename}' indexed."}
    except Exception as e:
        logger.error(f"[{session_id}] Upload failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/pm/profile/{session_id}")
async def pm_get_profile(session_id: str):
    """Get current requirement profile."""
    profile = await pm_agent_service.get_profile(session_id)
    return {"success": True, "session_id": session_id, "profile": profile}
```

- [ ] **Step 3: Commit**

```bash
git add app/models/pm.py app/api/pm.py
git commit -m "feat: add multi-endpoint API with convenience wrapper"
```

---

### Task 15: FastAPI App Entry Point

**Files:**
- Create: `pm_agent/app/main.py`

- [ ] **Step 1: Write main.py**

```python
"""PM Agent FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from loguru import logger
from app.config import config
from app.core.milvus_client import milvus_manager
from app.api.pm import router as pm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"Starting {config.app_name} v{config.app_version}...")
    logger.info(f"Environment: {'development' if config.debug else 'production'}")
    logger.info(f"Listening on: http://{config.host}:{config.port}")
    logger.info(f"API docs: http://{config.host}:{config.port}/docs")

    logger.info("Connecting to Milvus...")
    milvus_manager.connect()
    logger.info("Milvus connected")

    logger.info("=" * 60)
    yield

    logger.info("Shutting down...")
    milvus_manager.close()
    logger.info(f"{config.app_name} stopped")


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="AI Product Manager Agent — automated requirement mining and PRD generation",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pm_router, prefix="/api", tags=["PM Agent"])

static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": f"Welcome to {config.app_name} API",
        "version": config.app_version,
        "docs": "/docs",
    }
```

- [ ] **Step 2: Create static/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PM Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #f5f5f5; height: 100vh; display: flex; flex-direction: column; }
        header { background: #1a1a2e; color: white; padding: 16px 24px;
                 font-size: 18px; font-weight: 600; }
        #chat { flex: 1; overflow-y: auto; padding: 24px; max-width: 900px;
                margin: 0 auto; width: 100%; }
        .msg { margin-bottom: 16px; padding: 12px 16px; border-radius: 8px;
               max-width: 80%; line-height: 1.6; }
        .msg.user { background: #e3f2fd; align-self: flex-end; margin-left: auto; }
        .msg.assistant { background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .event { font-size: 12px; color: #666; margin: 8px 0; padding: 8px;
                 background: #fff3e0; border-radius: 4px; }
        #input-area { display: flex; padding: 16px 24px; background: white;
                      border-top: 1px solid #e0e0e0; max-width: 900px;
                      margin: 0 auto; width: 100%; gap: 12px; }
        #input-area input { flex: 1; padding: 12px; border: 1px solid #ddd;
                            border-radius: 6px; font-size: 14px; }
        #input-area button { padding: 12px 24px; background: #1a1a2e; color: white;
                             border: none; border-radius: 6px; cursor: pointer;
                             font-size: 14px; }
        #input-area button:hover { background: #16213e; }
        #mode-toggle { padding: 8px 16px; background: #e0e0e0; border: none;
                       border-radius: 6px; cursor: pointer; font-size: 13px; }
    </style>
</head>
<body>
    <header>PM Agent — AI 产品需求分析助手</header>
    <div id="chat"></div>
    <div id="input-area">
        <button id="mode-toggle" onclick="toggleMode()">模式: 一键生成</button>
        <input type="text" id="msg-input" placeholder="描述你的项目需求，或说"生成PRD"开始生成..."
               onkeypress="if(event.key==='Enter') sendMessage()">
        <button onclick="sendMessage()">发送</button>
    </div>
    <script>
        const sessionId = 'session-' + Date.now();
        let mode = 'one_shot';

        function toggleMode() {
            mode = mode === 'one_shot' ? 'incremental' : 'one_shot';
            document.getElementById('mode-toggle').textContent =
                '模式: ' + (mode === 'one_shot' ? '一键生成' : '增量确认');
        }

        function addMessage(role, text) {
            const div = document.createElement('div');
            div.className = 'msg ' + role;
            div.textContent = text;
            document.getElementById('chat').appendChild(div);
            document.getElementById('chat').scrollTop =
                document.getElementById('chat').scrollHeight;
        }

        function addEvent(text) {
            const div = document.createElement('div');
            div.className = 'event';
            div.textContent = text;
            document.getElementById('chat').appendChild(div);
        }

        async function sendMessage() {
            const input = document.getElementById('msg-input');
            const msg = input.value.trim();
            if (!msg) return;
            input.value = '';
            addMessage('user', msg);

            try {
                const resp = await fetch('/api/pm/agent', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg, session_id: sessionId, mode: mode}),
                });

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let currentDiv = null;
                let currentContent = '';

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    const text = decoder.decode(value);
                    for (const line of text.split('\n')) {
                        if (!line.startsWith('data: ')) continue;
                        const event = JSON.parse(line.slice(6));

                        switch (event.type) {
                            case 'content':
                                currentContent += event.data;
                                if (!currentDiv) {
                                    currentDiv = document.createElement('div');
                                    currentDiv.className = 'msg assistant';
                                    document.getElementById('chat').appendChild(currentDiv);
                                }
                                currentDiv.textContent = currentContent;
                                break;
                            case 'profile_update':
                                addEvent('已更新: ' + event.data);
                                break;
                            case 'sufficiency':
                                addEvent('需求完整度: ' + Math.round(event.data.score * 100) + '%');
                                break;
                            case 'ready_to_generate':
                                addEvent(event.data.message);
                                break;
                            case 'status':
                                addEvent(event.data.message);
                                break;
                            case 'prd_plan':
                                addEvent('PRD 大纲 (' + event.data.mode + '): ' +
                                    event.data.sections.map(s => s.title).join(' → '));
                                break;
                            case 'section_start':
                                addEvent('Writing: ' + event.data.title +
                                    ' (' + event.data.index + '/' + event.data.total + ')');
                                currentDiv = null;
                                currentContent = '';
                                break;
                            case 'section_content':
                                currentContent += event.data;
                                break;
                            case 'section_complete':
                                if (currentContent) {
                                    addMessage('assistant', currentContent);
                                }
                                currentContent = '';
                                currentDiv = null;
                                break;
                            case 'awaiting_approval':
                                addEvent(event.data.message + ' [Reply "continue" to proceed]');
                                break;
                            case 'prd_complete':
                                addEvent('PRD generation complete!');
                                break;
                            case 'error':
                                addEvent('Error: ' + event.data);
                                break;
                        }
                    }
                }
            } catch (e) {
                addEvent('Error: ' + e.message);
            }
            document.getElementById('chat').scrollTop =
                document.getElementById('chat').scrollHeight;
        }
    </script>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py static/index.html
git commit -m "feat: add FastAPI entry point and chat frontend"
```

---

### Task 16: MySQL Database Layer

**Files:**
- Create: `pm_agent/app/db/__init__.py`
- Create: `pm_agent/app/db/database.py`
- Create: `pm_agent/app/db/models.py`
- Create: `pm_agent/app/db/repository.py`

- [ ] **Step 1: Write db/__init__.py**

```python
from app.db.database import get_session, init_db
from app.db.models import Base, RequirementProfileModel, GeneratedPRD
from app.db.repository import ProfileRepository, PRDRepository

__all__ = [
    "get_session", "init_db",
    "Base", "RequirementProfileModel", "GeneratedPRD",
    "ProfileRepository", "PRDRepository",
]
```

- [ ] **Step 2: Write db/database.py**

```python
"""Async SQLAlchemy engine and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from loguru import logger
from app.config import config

engine = create_async_engine(
    config.database_url,
    echo=config.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Create all tables. Call on app startup."""
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("MySQL tables created/verified")


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 3: Write db/models.py**

```python
"""SQLAlchemy ORM models for PM Agent."""

from datetime import datetime
from sqlalchemy import String, Text, Float, JSON, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    pass


class ProfileStatus(str, enum.Enum):
    MINING = "mining"
    READY = "ready"
    GENERATING = "generating"
    COMPLETE = "complete"


class RequirementProfileModel(Base):
    __tablename__ = "requirement_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_name: Mapped[str] = mapped_column(String(200), default="")
    project_type: Mapped[str] = mapped_column(String(100), default="")
    industry: Mapped[str] = mapped_column(String(100), default="")
    elevator_pitch: Mapped[str] = mapped_column(Text, default="")
    user_roles: Mapped[dict] = mapped_column(JSON, default=list)
    functional_modules: Mapped[dict] = mapped_column(JSON, default=list)
    non_functional: Mapped[dict] = mapped_column(JSON, default=dict)
    constraints: Mapped[dict] = mapped_column(JSON, default=list)
    assumptions: Mapped[dict] = mapped_column(JSON, default=list)
    covered_topics: Mapped[dict] = mapped_column(JSON, default=list)
    pending_questions: Mapped[dict] = mapped_column(JSON, default=list)
    sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ProfileStatus] = mapped_column(
        SAEnum(ProfileStatus), default=ProfileStatus.MINING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GeneratedPRD(Base):
    __tablename__ = "generated_prds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    mode: Mapped[str] = mapped_column(String(20), default="one_shot")
    sections: Mapped[dict] = mapped_column(JSON, default=list)
    markdown: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Write db/repository.py**

```python
"""Data access layer for requirement profiles and PRDs."""

import json
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.db.models import RequirementProfileModel, GeneratedPRD, ProfileStatus


class ProfileRepository:

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        session_id: str,
    ) -> RequirementProfileModel:
        result = await session.execute(
            select(RequirementProfileModel).where(
                RequirementProfileModel.session_id == session_id
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = RequirementProfileModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
        return profile

    @staticmethod
    async def update_field(
        session: AsyncSession,
        session_id: str,
        field: str,
        value,
    ) -> RequirementProfileModel:
        profile = await ProfileRepository.get_or_create(session, session_id)
        if hasattr(profile, field):
            setattr(profile, field, value)
            await session.commit()
            await session.refresh(profile)
        return profile

    @staticmethod
    async def update_from_dict(
        session: AsyncSession,
        session_id: str,
        data: dict,
    ) -> RequirementProfileModel:
        profile = await ProfileRepository.get_or_create(session, session_id)
        for key, value in data.items():
            if hasattr(profile, key) and key != "id":
                setattr(profile, key, value)
        await session.commit()
        await session.refresh(profile)
        return profile

    @staticmethod
    async def get_by_session(
        session: AsyncSession,
        session_id: str,
    ) -> Optional[dict]:
        profile = await ProfileRepository.get_or_create(session, session_id)
        return {
            "project_name": profile.project_name,
            "project_type": profile.project_type,
            "industry": profile.industry,
            "elevator_pitch": profile.elevator_pitch,
            "user_roles": profile.user_roles,
            "functional_modules": profile.functional_modules,
            "non_functional": profile.non_functional,
            "constraints": profile.constraints,
            "assumptions": profile.assumptions,
            "covered_topics": profile.covered_topics,
            "pending_questions": profile.pending_questions,
            "sufficiency_score": profile.sufficiency_score,
        }


class PRDRepository:

    @staticmethod
    async def save(
        session: AsyncSession,
        session_id: str,
        title: str,
        mode: str,
        sections: list,
        markdown: str,
    ) -> GeneratedPRD:
        prd = GeneratedPRD(
            id=str(uuid.uuid4()),
            session_id=session_id,
            title=title,
            mode=mode,
            sections=sections,
            markdown=markdown,
        )
        session.add(prd)
        await session.commit()
        await session.refresh(prd)
        return prd

    @staticmethod
    async def list_by_session(
        session: AsyncSession,
        session_id: str,
    ) -> list[GeneratedPRD]:
        result = await session.execute(
            select(GeneratedPRD)
            .where(GeneratedPRD.session_id == session_id)
            .order_by(GeneratedPRD.created_at.desc())
        )
        return list(result.scalars().all())
```

- [ ] **Step 5: Commit**

```bash
git add app/db/
git commit -m "feat: add MySQL database layer with SQLAlchemy async"
```

---

### Task 17: Docker Deployment

**Files:**
- Create: `pm_agent/Dockerfile`
- Create: `pm_agent/docker-compose.yml`
- Create: `pm_agent/nginx.conf`
- Create: `pm_agent/.env.docker`

- [ ] **Step 1: Write Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir aiomysql

COPY . .

RUN mkdir -p uploads logs

EXPOSE 9900

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9900/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9900"]
```

- [ ] **Step 2: Write docker-compose.yml**

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:alpine
    container_name: pm-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - pm-agent
    restart: unless-stopped
    networks:
      - pm-network

  pm-agent:
    build: .
    container_name: pm-agent
    env_file:
      - .env.docker
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      milvus:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - pm-network
    deploy:
      replicas: 2

  mysql:
    image: mysql:8.0
    container_name: pm-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root_pass
      MYSQL_DATABASE: pm_agent
      MYSQL_USER: pm_agent
      MYSQL_PASSWORD: pm_agent_pass
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - pm-network

  redis:
    image: redis:7-alpine
    container_name: pm-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - pm-network

  milvus:
    image: milvusdb/milvus:v2.4.0
    container_name: pm-milvus
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    ports:
      - "19530:19530"
    depends_on:
      etcd:
        condition: service_healthy
      minio:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - pm-network

  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    container_name: pm-etcd
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"
      ETCD_QUOTA_BACKEND_BYTES: "4294967296"
    command: etcd -advertise-client-urls=http://etcd:2379 -listen-client-urls http://0.0.0.0:2379
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - pm-network

  minio:
    image: minio/minio:latest
    container_name: pm-minio
    command: minio server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - pm-network

volumes:
  mysql_data:
  redis_data:

networks:
  pm-network:
    driver: bridge
```

- [ ] **Step 3: Write nginx.conf**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream pm_agent_backend {
        least_conn;
        server pm-agent:9900;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://pm_agent_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # SSE support: disable buffering
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 600s;
            proxy_http_version 1.1;
            proxy_set_header Connection '';
        }

        location /api/pm/ {
            proxy_pass http://pm_agent_backend;
            proxy_set_header Host $host;
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 600s;
            proxy_http_version 1.1;
            proxy_set_header Connection '';
        }
    }
}
```

- [ ] **Step 4: Write .env.docker**

```env
APP_NAME=PM Agent
DEBUG=False
HOST=0.0.0.0
PORT=9900

SILICONFLOW_API_KEY=sk-your-key-here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V4-Flash
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-m3

MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_TIMEOUT=10000

RAG_TOP_K=5
RAG_MODEL=deepseek-ai/DeepSeek-V4-Flash

CHUNK_MAX_SIZE=800
CHUNK_OVERLAP=100

REDIS_URL=redis://redis:6379

MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=pm_agent
MYSQL_PASSWORD=pm_agent_pass
MYSQL_DATABASE=pm_agent
DATABASE_URL=mysql+aiomysql://pm_agent:pm_agent_pass@mysql:3306/pm_agent

SUFFICIENCY_THRESHOLD=0.75
```

- [ ] **Step 5: Add health endpoint to main.py**

Add this route to `app/main.py`:

```python
@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Update main.py lifespan for MySQL init**

Update the lifespan in `app/main.py`:

```python
from app.db.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {config.app_name} v{config.app_version}...")

    logger.info("Connecting to Milvus...")
    milvus_manager.connect()
    logger.info("Milvus connected")

    logger.info("Initializing MySQL...")
    await init_db()
    logger.info("MySQL initialized")

    yield

    milvus_manager.close()
    logger.info(f"{config.app_name} stopped")
```

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml nginx.conf .env.docker app/main.py
git commit -m "feat: add Docker multi-node deployment with MySQL, Redis, Milvus, and nginx"
```

---

### Task 18: Integration Tests

**Files:**
- Create: `pm_agent/tests/conftest.py`
- Create: `pm_agent/tests/test_state.py`
- Create: `pm_agent/tests/test_tools.py`
- Create: `pm_agent/tests/test_sufficiency.py`
- Create: `pm_agent/tests/test_phase2_planner.py`
- Create: `pm_agent/tests/test_phase2_generator.py`
- Create: `pm_agent/tests/test_db_repository.py`
- Create: `pm_agent/tests/test_pm_agent_service.py`
- Create: `pm_agent/tests/test_api_pm.py`

- [ ] **Step 1: Write tests/conftest.py**

```python
import pytest
from app.agent.pm.tools import _profile_store


@pytest.fixture(autouse=True)
def clear_profile_store():
    _profile_store.clear()
    yield
    _profile_store.clear()
```

- [ ] **Step 2: Write tests/test_state.py**

```python
from app.agent.pm.state import RequirementProfile, PMState


def test_requirement_profile_defaults():
    profile: RequirementProfile = {
        "project_name": "",
        "project_type": "",
        "industry": "",
        "elevator_pitch": "",
        "user_roles": [],
        "functional_modules": [],
        "non_functional": {},
        "constraints": [],
        "assumptions": [],
        "covered_topics": [],
        "pending_questions": [],
        "sufficiency_score": 0.0,
    }
    assert profile["project_name"] == ""
    assert profile["sufficiency_score"] == 0.0
    assert len(profile["user_roles"]) == 0


def test_requirement_profile_partial():
    profile: RequirementProfile = {
        "project_name": "Test Project",
        "project_type": "Web App",
        "industry": "Finance",
    }
    assert profile["project_name"] == "Test Project"
    assert profile.get("elevator_pitch", "") == ""
```

- [ ] **Step 3: Write tests/test_tools.py**

```python
import json
from app.agent.pm.tools import (
    get_profile,
    update_requirement_profile,
    get_profile_summary,
)


def test_get_profile_creates_default():
    profile = get_profile("test-thread")
    assert profile["project_name"] == ""
    assert profile["sufficiency_score"] == 0.0


def test_update_profile_string_field():
    update_requirement_profile.invoke({
        "field": "project_name",
        "value": "报销审批系统",
        "thread_id": "test-thread",
    })
    profile = get_profile("test-thread")
    assert profile["project_name"] == "报销审批系统"


def test_update_profile_list_field():
    roles = json.dumps([
        {"role": "员工", "desc": "提交报销申请"},
        {"role": "经理", "desc": "审批报销"},
    ])
    update_requirement_profile.invoke({
        "field": "user_roles",
        "value": roles,
        "thread_id": "test-thread",
    })
    profile = get_profile("test-thread")
    assert len(profile["user_roles"]) == 2
    assert profile["user_roles"][0]["role"] == "员工"


def test_get_profile_summary():
    update_requirement_profile.invoke({
        "field": "project_name",
        "value": "测试项目",
        "thread_id": "summary-test",
    })
    summary = get_profile_summary.invoke({"thread_id": "summary-test"})
    assert "测试项目" in summary
    assert "Not Yet Covered" in summary
```

- [ ] **Step 4: Write tests/test_sufficiency.py**

```python
from app.agent.pm.tools import update_requirement_profile
from app.agent.pm.phase1.sufficiency import evaluate_sufficiency


def test_evaluate_sufficiency_low_for_empty_profile():
    result = evaluate_sufficiency.invoke({"thread_id": "suff-test"})
    assert "Score" in result or "score" in result.lower()


def test_evaluate_sufficiency_improves_with_data():
    tid = "suff-test-2"
    update_requirement_profile.invoke({
        "field": "project_name", "value": "HR管理系统", "thread_id": tid,
    })
    update_requirement_profile.invoke({
        "field": "elevator_pitch", "value": "全流程人力资源管理平台", "thread_id": tid,
    })
    result = evaluate_sufficiency.invoke({"thread_id": tid})
    assert "Score" in result or "score" in result.lower()
```

- [ ] **Step 5: Write tests/test_phase2_planner.py**

```python
from app.agent.pm.phase2.planner import prd_planner


def test_planner_creates_all_sections():
    profile = {
        "project_name": "Test",
        "project_type": "Web",
        "industry": "Tech",
        "elevator_pitch": "A test project",
        "user_roles": [],
        "functional_modules": [],
        "non_functional": {},
        "constraints": [],
        "assumptions": [],
    }
    sections = prd_planner.plan(profile)
    assert len(sections) == 8
    assert sections[0]["title"] == "1. 项目概述"
    assert sections[-1]["title"] == "8. 附录"
    assert all(s["status"] == "pending" for s in sections)


def test_planner_one_shot_vs_incremental():
    profile = {"project_name": "Test"}
    sections_os = prd_planner.plan(profile, "one_shot")
    sections_inc = prd_planner.plan(profile, "incremental")
    assert len(sections_os) == len(sections_inc)
```

- [ ] **Step 6: Write tests/test_phase2_generator.py**

```python
import pytest
from app.agent.pm.phase2.generator import section_generator


@pytest.mark.asyncio
async def test_generator_yields_content():
    section = {
        "key": "project_overview",
        "title": "1. 项目概述",
        "prompt": "Write a brief project overview for a food delivery app.",
    }
    chunks = []
    async for chunk in section_generator.generate(section):
        chunks.append(chunk)
    assert len(chunks) > 0
    full = "".join(chunks)
    assert len(full) > 20


@pytest.mark.asyncio
async def test_generator_starts_with_section_heading():
    section = {
        "key": "acceptance",
        "title": "7. 验收标准",
        "prompt": "Write acceptance criteria for a login system.",
    }
    chunks = []
    async for chunk in section_generator.generate(section):
        chunks.append(chunk)
    full = "".join(chunks)
    assert "##" in full or len(full) > 30
```

- [ ] **Step 7: Write tests/test_db_repository.py**

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.models import Base, RequirementProfileModel
from app.db.repository import ProfileRepository, PRDRepository


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_creates_new_profile(session):
    profile = await ProfileRepository.get_or_create(session, "new-session")
    assert profile is not None
    assert profile.session_id == "new-session"
    assert profile.project_name == ""


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(session):
    p1 = await ProfileRepository.get_or_create(session, "same-session")
    p2 = await ProfileRepository.get_or_create(session, "same-session")
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_update_field(session):
    profile = await ProfileRepository.update_field(
        session, "test-session", "project_name", "HR系统"
    )
    assert profile.project_name == "HR系统"


@pytest.mark.asyncio
async def test_update_from_dict(session):
    profile = await ProfileRepository.update_from_dict(session, "test-session-2", {
        "project_name": "报销系统",
        "industry": "金融",
        "sufficiency_score": 0.8,
    })
    assert profile.project_name == "报销系统"
    assert profile.industry == "金融"
    assert profile.sufficiency_score == 0.8


@pytest.mark.asyncio
async def test_prd_save_and_list(session):
    prd = await PRDRepository.save(
        session,
        session_id="test-prd-session",
        title="HR系统 PRD",
        mode="one_shot",
        sections=[{"key": "overview", "title": "概述", "status": "done"}],
        markdown="# HR系统 PRD\n\n## 概述\n...",
    )
    assert prd.id is not None
    assert prd.title == "HR系统 PRD"

    prds = await PRDRepository.list_by_session(session, "test-prd-session")
    assert len(prds) == 1
    assert prds[0].title == "HR系统 PRD"
```

- [ ] **Step 8: Write tests/test_pm_agent_service.py**

```python
import pytest
from unittest.mock import patch
from app.services.pm_agent_service import pm_agent_service


@pytest.mark.asyncio
async def test_get_profile_returns_default():
    from app.agent.pm.tools import _profile_store
    _profile_store.clear()
    profile = await pm_agent_service.get_profile("test-thread")
    assert profile["project_name"] == ""
    assert profile["sufficiency_score"] == 0.0


@pytest.mark.asyncio
async def test_chat_yields_events():
    from app.agent.pm.tools import _profile_store
    _profile_store.clear()

    with patch.object(pm_agent_service, 'chat', autospec=True) as mock_chat:
        mock_chat.return_value = iter([
            {"type": "content", "data": "你好！"},
            {"type": "sufficiency", "data": {"score": 0.3, "threshold": 0.75}},
        ])
        events = []
        async for event in pm_agent_service.chat("我想做一个系统", "test-thread"):
            events.append(event)
        assert len(events) >= 2
        assert events[0]["type"] == "content"
```

- [ ] **Step 9: Write tests/test_api_pm.py**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_profile_endpoint(client):
    from app.agent.pm.tools import _profile_store
    _profile_store.clear()
    response = await client.get("/api/pm/profile/api-test")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "api-test"
    assert "profile" in data


@pytest.mark.asyncio
async def test_chat_endpoint_returns_sse(client):
    response = await client.post("/api/pm/chat", json={
        "message": "我想做一个外卖系统", "session_id": "api-test-1",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_generate_endpoint_returns_sse(client):
    response = await client.post("/api/pm/generate", json={
        "session_id": "api-test-1", "mode": "one_shot",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_continue_endpoint_returns_sse(client):
    response = await client.post("/api/pm/continue", json={
        "session_id": "api-test-1",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_agent_endpoint_chat_returns_sse(client):
    response = await client.post("/api/pm/agent", json={
        "message": "我想做一个外卖系统", "session_id": "api-test-2", "mode": "one_shot",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_agent_endpoint_generate_returns_sse(client):
    response = await client.post("/api/pm/agent", json={
        "message": "生成PRD", "session_id": "api-test-2", "mode": "one_shot",
    })
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_upload_endpoint_rejects_no_file(client):
    response = await client.post("/api/pm/upload")
    assert response.status_code in (422, 400)
```

- [ ] **Step 10: Run all tests**

```bash
cd D:/WorkProject/pm_agent
pip install aiosqlite httpx
python -m pytest tests/ -v
```

- [ ] **Step 11: Commit**

```bash
git add tests/
git commit -m "test: add comprehensive tests for all modules (state, tools, sufficiency, planner, generator, db, api, service)"
```

---

### Task 19: Final Integration & Verification

- [ ] **Step 1: Verify the full app starts**

```bash
cd D:/WorkProject/pm_agent
python -m app.main
# Check http://localhost:9900/ and http://localhost:9900/docs
```

- [ ] **Step 2: Test individual endpoints**

```bash
# Chat (Phase 1)
curl -X POST "http://localhost:9900/api/pm/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "我想做一个外卖配送系统", "session_id": "test-1"}' \
  --no-buffer

# Generate PRD (Phase 2)
curl -X POST "http://localhost:9900/api/pm/generate" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1", "mode": "one_shot"}' \
  --no-buffer

# Continue (Phase 2 incremental)
curl -X POST "http://localhost:9900/api/pm/continue" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1"}' \
  --no-buffer
```

- [ ] **Step 3: Test convenience wrapper**

```bash
# Convenience: auto-routes chat
curl -X POST "http://localhost:9900/api/pm/agent" \
  -H "Content-Type: application/json" \
  -d '{"message": "我想做一个外卖系统", "session_id": "test-2", "mode": "one_shot"}' \
  --no-buffer

# Convenience: auto-detects "生成PRD"
curl -X POST "http://localhost:9900/api/pm/agent" \
  -H "Content-Type: application/json" \
  -d '{"message": "生成PRD", "session_id": "test-2", "mode": "one_shot"}' \
  --no-buffer
```

- [ ] **Step 4: Test file upload**

```bash
echo "# 外卖行业需求分析经验\n\n## 核心功能\n- 用户端：浏览商家、下单、支付、追踪配送\n- 骑手端：接单、导航、收入统计\n- 商家端：菜品管理、订单处理、数据分析\n- 管理后台：全部管理功能" > /tmp/test_experience.md

curl -X POST "http://localhost:9900/api/pm/upload" \
  -F "file=@/tmp/test_experience.md" \
  -F "session_id=test-1"
```

- [ ] **Step 5: Verify profile endpoint**

```bash
curl "http://localhost:9900/api/pm/profile/test-1"
```

- [ ] **Step 5: Run all tests one final time**

```bash
cd D:/WorkProject/pm_agent
python -m pytest tests/ -v
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: final integration verification"
```

---

## Implementation Order

| Order | Task | Dependencies |
|-------|------|-------------|
| 1 | Project Scaffold | none |
| 2 | Config + Logger | 1 |
| 3 | Core Infrastructure (LLM, Milvus, Embedding) | 2 |
| 4 | Vector Store Manager | 3 |
| 5 | Document Splitter + Index Service | 4 |
| 6 | Shared Tools | 4 |
| 7 | State + Prompts | 2 |
| 8 | PM Tools | 7 |
| 9 | Sufficiency Evaluator | 8 |
| 10 | Phase 1 Mining Agent | 6, 8, 9 |
| 11 | Phase 2 Planner | 7 |
| 12 | Phase 2 Generator + Assembler | 11 |
| 13 | PM Agent Service | 10, 12 |
| 14 | API Models + Routes | 13, 5 |
| 15 | FastAPI Entry Point + Frontend | 14 |
| 16 | MySQL Database Layer | 2 |
| 17 | Docker Deployment | 15, 16 |
| 18 | Integration Tests | 13, 16 |
| 19 | Final Verification | all |

Tasks 1-5 start immediately. Tasks 6-10 are Phase 1 focused. Tasks 11-12 are Phase 2 focused.
Tasks 3-7 can run in parallel (no interdependencies). Task 16 (MySQL) runs in parallel with 3-15.
Task 17 (Docker) runs after MySQL and app are complete.

Tasks 1-5 can start immediately. Tasks 6-10 are phase 1 focused. Tasks 11-12 are phase 2 focused.
Tasks 3-7 can run in parallel since they have no interdependencies.

---

## Redis Setup Note

Before running the app, ensure Redis is available:

```bash
# Docker (recommended for development)
docker run -d --name pm-redis -p 6379:6379 redis:7-alpine

# Or on Windows, install Redis via WSL or use redis-windows
```
