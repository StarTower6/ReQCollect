from app.db.models import Base, ChatMessageModel, GeneratedPRD, RequirementProfileModel
from app.db.repository import ChatHistoryRepository, PRDRepository, ProfileRepository

__all__ = [
    "get_session", "init_db",
    "Base", "RequirementProfileModel", "GeneratedPRD", "ChatMessageModel",
    "ProfileRepository", "PRDRepository", "ChatHistoryRepository",
]


def __getattr__(name: str):
    if name in {"get_session", "init_db"}:
        from app.db.database import get_session, init_db
        return {"get_session": get_session, "init_db": init_db}[name]
    raise AttributeError(f"module 'app.db' has no attribute {name!r}")
