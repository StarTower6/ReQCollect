"""DataStore protocol and factory.

Defines the abstract interface for all data access operations.
MySQLDataStore and FileDataStore implement this protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


# ── DataStore Protocol ──


class DataStore(ABC):
    """Abstract data access layer for ReQCollect.

    All methods are async. Implementations must handle their own connection/session
    lifecycle. This allows seamless swap between MySQL and JSON file backends.
    """

    # ── Sessions ──

    @abstractmethod
    async def create_session(
        self,
        session_id: str,
        user_id: str = "default",
        project_name: str = "",
    ) -> dict:
        """Create a new session and return its dict representation."""

    @abstractmethod
    async def get_session(self, session_id: str) -> dict | None:
        """Get session dict by ID. Returns None if not found."""

    @abstractmethod
    async def list_sessions(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List sessions with optional filters, ordered by updated_at desc."""

    @abstractmethod
    async def update_session(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> dict | None:
        """Update session fields. Returns updated session or None."""

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data. Returns True if deleted."""

    # ── Messages ──

    @abstractmethod
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        event_type: str = "message",
        meta: dict | None = None,
    ) -> dict:
        """Save a chat message and return its dict."""

    @abstractmethod
    async def get_message_history(
        self,
        session_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Get messages for a session, ordered by created_at asc."""

    # ── Requirement Profiles ──

    @abstractmethod
    async def get_profile(self, session_id: str) -> dict:
        """Get requirement profile dict. Returns defaults if none exists."""

    @abstractmethod
    async def save_profile(self, session_id: str, profile: dict) -> dict:
        """Full overwrite save of a requirement profile."""

    @abstractmethod
    async def update_profile_field(
        self, session_id: str, field: str, value: Any
    ) -> dict:
        """Update a single field in a requirement profile."""

    # ── PRDs ──

    @abstractmethod
    async def save_prd(
        self,
        session_id: str,
        project_name: str = "",
        mode: str = "one_shot",
        sections: list | None = None,
        markdown: str = "",
    ) -> dict:
        """Save a generated PRD (auto-increment version). Returns the PRD dict."""

    @abstractmethod
    async def get_prd(
        self, session_id: str, version: int | None = None
    ) -> dict | None:
        """Get latest (or specific version) PRD for a session."""

    @abstractmethod
    async def list_prds(self, session_id: str) -> list[dict]:
        """List all PRD versions for a session."""

    # ── Dashboard / Stats ──

    @abstractmethod
    async def get_dashboard_overview(
        self,
    ) -> dict:
        """Return overview stats: total sessions, by status, avg sufficiency."""

    @abstractmethod
    async def get_trend_data(
        self,
        granularity: str = "day",
        days: int = 30,
    ) -> list[dict]:
        """Return time-series data of session/PRD creation counts."""

    # ── Audit ──

    @abstractmethod
    async def log_audit(
        self,
        action: str,
        user_id: str = "",
        session_id: str = "",
        detail: dict | None = None,
        ip_address: str = "",
    ) -> None:
        """Record an audit log entry."""

    # ── Health ──

    @abstractmethod
    async def health(self) -> dict:
        """Return backend health status."""


def create_datastore(use_mysql: bool) -> DataStore:
    """Factory: returns MySQLDataStore or FileDataStore."""
    if use_mysql:
        from app.db.repository import MySQLDataStore

        return MySQLDataStore()
    from app.db.compat import FileDataStore

    return FileDataStore()
