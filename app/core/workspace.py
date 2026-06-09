"""Workspace utilities — migration, session association."""

import uuid
from loguru import logger


async def migrate_sessions_to_workspaces(datastore) -> int:
    """One-time migration: group sessions by project_name → create workspaces.

    For each distinct project_name found in sessions, create a workspace
    and assign the workspace_id to those sessions.
    """
    sessions = await datastore.list_sessions(limit=10000)
    if not sessions:
        return 0

    # Group by project_name
    groups: dict[str, list[dict]] = {}
    for s in sessions:
        name = s.get("project_name", "").strip()
        if not name:
            name = "未命名项目"
        if name not in groups:
            groups[name] = []
        groups[name].append(s)

    count = 0
    for name, group_sessions in groups.items():
        # Use the first session's user as creator
        creator = group_sessions[0].get("user_id", "admin")

        # Create workspace
        ws = await datastore.create_workspace(
            name=name,
            created_by=creator,
            description=f"自动迁移自项目「{name}」",
        )

        # Assign workspace_id to each session
        for s in group_sessions:
            sid = s.get("session_id", "")
            if sid:
                await datastore.update_session(sid, workspace_id=ws["id"])
                count += 1

        logger.info(f"Migrated {len(group_sessions)} sessions → workspace '{name}'")

    return count
