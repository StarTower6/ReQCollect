"""Database exceptions."""


class DataStoreError(Exception):
    """Base exception for all DataStore operations."""


class SessionNotFoundError(DataStoreError):
    """Raised when a session is not found."""


class ProfileNotFoundError(DataStoreError):
    """Raised when a requirement profile is not found."""


class PRDNotFoundError(DataStoreError):
    """Raised when a generated PRD is not found."""


class DuplicateSessionError(DataStoreError):
    """Raised when trying to create a session with an existing ID."""


class DatabaseConnectionError(DataStoreError):
    """Raised when MySQL connection fails."""
