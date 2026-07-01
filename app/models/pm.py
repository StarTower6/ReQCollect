"""PM Agent request models (Lite)."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: str = Field(default="default", description="Session ID")
    use_knowledge: bool = Field(default=False, description="Force knowledge retrieval")
    workspace_id: str = Field(default="", description="Workspace ID")
    referenced_files: list[str] = Field(default=[], description="引用的工作区文件路径")

    model_config = {"json_schema_extra": {"example": {
        "message": "我想做一个企业报销审批系统",
        "session_id": "session-001",
        "use_knowledge": True,
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
    use_knowledge: bool = Field(default=False, description="Force knowledge retrieval")
    workspace_id: str = Field(default="", description="Workspace ID")
    referenced_files: list[str] = Field(default=[], description="引用的工作区文件路径")

    model_config = {"json_schema_extra": {"example": {
        "message": "我想做一个企业报销审批系统",
        "session_id": "session-001",
        "mode": "one_shot",
        "use_knowledge": True,
    }}}


class ExtractProposalRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    workspace_id: str = Field(..., description="Workspace ID")

    model_config = {"json_schema_extra": {"example": {
        "session_id": "session-001",
        "workspace_id": "ws-001",
    }}}


class GenerateFromProposalsRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace ID")
    proposal_ids: list[str] = Field(..., description="Approved proposal IDs")
    session_id: str = Field(default="", description="Optional session ID for PRD association")

    model_config = {"json_schema_extra": {"example": {
        "workspace_id": "ws-001",
        "proposal_ids": ["prop-001", "prop-002"],
        "session_id": "session-001",
    }}}
