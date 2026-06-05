#!/usr/bin/env python3
"""One-shot migration: import pm_data/*.json files into MySQL.

Usage:
    python scripts/migrate_json_to_mysql.py [--data-dir ./pm_data]

Requires:
    - MySQL running with credentials in .env or environment
    - Existing pm_data/ directory with profile_{sid}.json and prd_{sid}.json files

Process:
    1. Scan pm_data/ for profile_*.json and prd_*.json files
    2. Extract session_id from filenames
    3. Create sessions, profiles, messages, and PRD records in MySQL
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

# Ensure app module is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger


# ── Helpers ──


def _extract_session_id(filename: str, prefix: str) -> str | None:
    """Extract session ID from filename like 'profile_session-xxx.json' or 'prd_session-xxx.json'."""
    pattern = re.compile(rf"^{re.escape(prefix)}_(.+)\.json$")
    match = pattern.match(filename)
    return match.group(1) if match else None


def _load_json_file(filepath: Path) -> dict | None:
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load {filepath}: {e}")
        return None


# ── Main migration ──


async def migrate(data_dir: str):
    """Migrate all JSON files in data_dir to MySQL."""
    from app.db.database import init_db, get_session_factory
    from app.db.models import Session, RequirementProfile, GeneratedPRD, ChatMessage, User
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession

    logger.info(f"Scanning {data_dir} for JSON files...")
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.error(f"Data directory {data_dir} does not exist")
        return False

    # Initialize DB
    ok = await init_db()
    if not ok:
        logger.error("MySQL connection failed — aborting migration")
        return False

    factory = get_session_factory()
    if factory is None:
        logger.error("Session factory not available")
        return False

    # Scan files
    profile_files = list(data_path.glob("profile_*.json"))
    prd_files = list(data_path.glob("prd_*.json"))

    logger.info(f"Found {len(profile_files)} profile files, {len(prd_files)} PRD files")

    # Also check migrated session files in new sessions/ dir
    session_files = list((data_path / "sessions").glob("*.json"))

    session_ids_migrated = set()

    async with factory() as session:
        # Ensure default user exists
        result = await session.execute(select(User).where(User.username == "default"))
        if result.scalar_one_or_none() is None:
            user = User(username="default", display_name="Migrated User", role="business")
            session.add(user)
            await session.commit()
            logger.info("Created default user")

        # Migrate sessions from existing profile files
        for pf in profile_files:
            sid = _extract_session_id(pf.name, "profile")
            if not sid:
                continue
            logger.info(f"Migrating session {sid}...")

            profile_data = _load_json_file(pf)
            if not profile_data:
                continue

            project_name = profile_data.get("project_name", "")
            sufficiency_score = profile_data.get("sufficiency_score", 0.0)

            # Upsert session
            result = await session.execute(select(Session).where(Session.id == sid))
            sess = result.scalar_one_or_none()
            if sess is None:
                sess = Session(
                    id=sid,
                    user_id="default",
                    project_name=project_name,
                    status="complete" if project_name else "mining",
                    sufficiency_score=sufficiency_score,
                )
                session.add(sess)
                await session.flush()

            # Upsert profile
            result2 = await session.execute(
                select(RequirementProfile).where(RequirementProfile.session_id == sid)
            )
            prof = result2.scalar_one_or_none()
            if prof is None:
                prof = RequirementProfile(session_id=sid)
                session.add(prof)

            for field in (
                "project_name", "business_background", "current_process", "user_roles",
                "business_flow", "functional_requirements", "existing_systems",
                "non_functional", "data_scale", "constraints", "success_criteria",
                "covered_topics", "pending_questions", "sufficiency_score",
            ):
                if field in profile_data:
                    setattr(prof, field, profile_data[field])
            await session.flush()
            session_ids_migrated.add(sid)

        logger.info(f"Migrated {len(session_ids_migrated)} sessions")

        # Migrate PRDs
        prd_count = 0
        for prd_f in prd_files:
            sid = _extract_session_id(prd_f.name, "prd")
            if not sid:
                continue

            prd_data = _load_json_file(prd_f)
            if not prd_data:
                continue

            prd = GeneratedPRD(
                session_id=sid,
                version=1,
                title=prd_data.get("title", "") or prd_data.get("project_name", ""),
                mode=prd_data.get("mode", "one_shot"),
                sections=prd_data.get("sections", []),
                markdown=prd_data.get("markdown", ""),
            )
            session.add(prd)
            prd_count += 1

        await session.commit()
        logger.info(f"Migrated {prd_count} PRDs")

    logger.info("Migration complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data files to MySQL")
    parser.add_argument("--data-dir", default="./pm_data", help="Path to pm_data directory")
    args = parser.parse_args()

    success = asyncio.run(migrate(args.data_dir))
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
