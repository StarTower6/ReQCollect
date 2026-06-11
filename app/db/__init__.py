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
        workspace_id: str | None = None,
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
        workspace_id: str | None = None,
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

    # ── Users ──

    @abstractmethod
    async def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: str = "",
        email: str = "",
        department: str = "",
        role: str = "business",
        source: str = "local",
    ) -> dict:
        """Create a new user. Returns the user dict."""

    @abstractmethod
    async def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username. Returns None if not found."""

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> dict | None:
        """Get user by ID. Returns None if not found."""

    @abstractmethod
    async def list_users(self) -> list[dict]:
        """List all users."""

    @abstractmethod
    async def update_user(self, user_id: str, **kwargs) -> dict | None:
        """Update user fields. Returns updated user or None."""

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user. Returns True if deleted."""

    # ── Import Records ──

    @abstractmethod
    async def save_import_record(
        self,
        session_id: str,
        filename: str,
        file_path: str,
        fields_filled: list[str] | None = None,
    ) -> dict:
        """Record a document import event for audit/source tracing."""

    @abstractmethod
    async def get_import_records(self, session_id: str) -> list[dict]:
        """Get all import records for a session."""

    # ── Workspaces ──

    @abstractmethod
    async def create_workspace(
        self,
        name: str,
        created_by: str,
        code: str = "",
        description: str = "",
    ) -> dict:
        """Create a workspace and return its dict."""

    @abstractmethod
    async def get_workspace(self, workspace_id: str) -> dict | None:
        """Get workspace by ID."""

    @abstractmethod
    async def list_workspaces(self, user_id: str | None = None) -> list[dict]:
        """List all workspaces accessible by user."""

    @abstractmethod
    async def update_workspace(self, workspace_id: str, **kwargs) -> dict | None:
        """Update workspace fields."""

    @abstractmethod
    async def delete_workspace(self, workspace_id: str) -> bool:
        """Delete workspace and all related data."""

    # ── Wiki Pages ──

    @abstractmethod
    async def create_wiki_page(
        self,
        workspace_id: str,
        title: str,
        content: str = "",
        created_by: str = "",
    ) -> dict:
        """Create a wiki page and return its dict."""

    @abstractmethod
    async def get_wiki_page(self, page_id: str) -> dict | None:
        """Get wiki page by ID."""

    @abstractmethod
    async def list_wiki_pages(self, workspace_id: str) -> list[dict]:
        """List all wiki pages in a workspace."""

    @abstractmethod
    async def update_wiki_page(self, page_id: str, **kwargs) -> dict | None:
        """Update wiki page fields."""

    @abstractmethod
    async def delete_wiki_page(self, page_id: str) -> bool:
        """Delete a wiki page."""

    # ── Wiki Links / File Links ──

    @abstractmethod
    async def get_wiki_links(self, page_id: str) -> list[dict]:
        """DEPRECATED: Use get_links(source_ref, "wiki"). Kept for backward compat."""

    @abstractmethod
    async def get_wiki_backlinks(self, page_id: str) -> list[dict]:
        """DEPRECATED: Use get_links(target_ref, "wiki", direction="incoming")."""

    @abstractmethod
    async def save_wiki_links(
        self, source_page_id: str, target_ids: list[str], link_type: str = "reference"
    ) -> None:
        """DEPRECATED: Use save_links(). Kept for backward compat."""

    @abstractmethod
    async def get_links(
        self, workspace_id: str, ref: str, ref_type: str = "wiki",
        direction: str = "outgoing",
    ) -> list[dict]:
        """Get links from/to a reference.
        direction="outgoing": links where source_ref = ref
        direction="incoming": links where target_ref = ref
        """

    @abstractmethod
    async def save_links(
        self, workspace_id: str,
        source_ref: str, source_type: str,
        targets: list[tuple[str, str]],  # [(target_ref, target_type), ...]
        link_type: str = "reference",
    ) -> None:
        """Full-replace: remove old outgoing links from source_ref, insert new ones."""

    @abstractmethod
    async def get_graph_edges(self, workspace_id: str) -> list[dict]:
        """Get ALL links in a workspace — used by graph endpoint."""

    @abstractmethod
    async def delete_links_for_ref(self, ref: str, ref_type: str = "wiki") -> None:
        """Remove all links (outgoing + incoming) for a reference."""

    @abstractmethod
    async def delete_wiki_links_for_page(self, page_id: str) -> None:
        """DEPRECATED: Use delete_links_for_ref(). Kept for backward compat."""

    # ── Workspace Files ──

    @abstractmethod
    async def list_workspace_files(
        self, workspace_id: str, pattern: str = "*", max_results: int = 50
    ) -> list[dict]:
        """List files in workspace."""

    @abstractmethod
    async def add_workspace_file(
        self, workspace_id: str, filename: str, content: bytes, uploaded_by: str = ""
    ) -> dict:
        """Upload and index a file in the workspace."""

    @abstractmethod
    async def read_workspace_file(
        self, workspace_id: str, file_path: str, max_chars: int = 8000
    ) -> dict:
        """Read file content."""

    @abstractmethod
    async def remove_workspace_file(
        self, workspace_id: str, file_path: str
    ) -> bool:
        """Delete a file from workspace."""

    @abstractmethod
    async def search_workspace_files(
        self, workspace_id: str, query: str,
        file_pattern: str = "*.md", max_results: int = 10
    ) -> list[dict]:
        """Full-text search in workspace files."""

    @abstractmethod
    async def write_workspace_file(
        self, workspace_id: str, file_path: str, content: str
    ) -> dict:
        """Write AI-generated file to workspace."""

    @abstractmethod
    async def get_workspace_files_info(self, workspace_id: str) -> dict:
        """Get workspace file overview."""

    @abstractmethod
    async def link_workspace_directory(self, workspace_id: str, dir_path: str) -> dict:
        """Link a server directory to workspace and scan."""

    @abstractmethod
    async def unlink_workspace_directory(self, workspace_id: str) -> dict:
        """Unlink directory and remove linked files."""

    @abstractmethod
    async def sync_workspace_files(self, workspace_id: str) -> dict:
        """Manually sync linked directory."""

    @abstractmethod
    async def get_workspace_linked_status(self, workspace_id: str) -> dict:
        """Get link status."""

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
