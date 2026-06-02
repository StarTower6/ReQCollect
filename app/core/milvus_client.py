"""Milvus client manager."""

from loguru import logger
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    MilvusException,
    connections,
    utility,
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
    _patch_pymilvus_milvus_client_orm_alias._done = True


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
