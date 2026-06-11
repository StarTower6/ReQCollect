"""PM-specific LangChain tools for requirement profile management.

Maintains an in-memory _profile_store for synchronous agent tool access.
DataStore integration: the service syncs profiles to the DataStore after
each chat turn and loads them at session start.
"""

from __future__ import annotations

import json
from contextvars import ContextVar

from langchain_core.tools import tool
from loguru import logger

from app.db import DataStore

# Lazy-import to avoid circular dependency at module level
_datastore: DataStore | None = None

PROFILE_DEFAULTS = {
    "project_name": "",
    "business_background": "",
    "current_process": "",
    "user_roles": [],
    "business_flow": "",
    "functional_requirements": [],
    "existing_systems": [],
    "non_functional": {},
    "data_scale": "",
    "constraints": [],
    "success_criteria": [],
    "covered_topics": [],
    "pending_questions": [],
    "sufficiency_score": 0.0,
}

_profile_store: dict[str, dict] = {}
_current_thread_id: ContextVar[str] = ContextVar("pm_current_thread_id", default="default")


def set_datastore_for_tools(ds: DataStore):
    """Register the DataStore instance so tools can persist profiles."""
    global _datastore
    _datastore = ds


async def sync_profile_from_datastore(thread_id: str):
    """Load a profile from DataStore into the in-memory store."""
    global _datastore
    if _datastore is None:
        return
    try:
        profile = await _datastore.get_profile(thread_id)
        if profile:
            _profile_store[thread_id] = profile
            logger.debug(f"[{thread_id}] Profile loaded from DataStore")
    except Exception as e:
        logger.warning(f"[{thread_id}] Failed to load profile from DataStore: {e}")


def set_current_thread_id(thread_id: str):
    return _current_thread_id.set(thread_id)


def reset_current_thread_id(token) -> None:
    _current_thread_id.reset(token)


def resolve_thread_id(thread_id: str = "default") -> str:
    return _current_thread_id.get() if thread_id == "default" else thread_id


def get_profile_store() -> dict[str, dict]:
    return _profile_store


def remove_profile(thread_id: str) -> None:
    thread_id = resolve_thread_id(thread_id)
    _profile_store.pop(thread_id, None)


def get_profile(thread_id: str) -> dict:
    thread_id = resolve_thread_id(thread_id)
    if thread_id not in _profile_store:
        _profile_store[thread_id] = {
            key: value.copy() if isinstance(value, (list, dict)) else value
            for key, value in PROFILE_DEFAULTS.items()
        }
    return _profile_store[thread_id]


def _is_empty_profile_value(value) -> bool:
    return value is None or value == "" or value == [] or value == {} or value == 0.0


def hydrate_profile(thread_id: str, data: dict | None) -> dict:
    """Merge persisted profile data into the in-memory tool profile."""
    profile = get_profile(thread_id)
    if not data:
        return profile
    for key in PROFILE_DEFAULTS:
        if key in data and data[key] is not None:
            current = profile.get(key)
            incoming = data[key]
            if _is_empty_profile_value(current) or not _is_empty_profile_value(incoming):
                if key == "sufficiency_score":
                    profile[key] = max(float(current or 0.0), float(incoming or 0.0))
                elif not _is_empty_profile_value(incoming):
                    profile[key] = incoming
    return profile


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
            project_name, business_background, current_process,
            user_roles (JSON array string), business_flow,
            functional_requirements (JSON array string),
            existing_systems (JSON array string),
            non_functional (JSON object string), data_scale,
            constraints (JSON array string), success_criteria (JSON array string),
            covered_topics (JSON array string), pending_questions (JSON array string)
        value: The value to set. For list/dict fields, pass a JSON string.
        thread_id: Session thread ID

    Returns:
        Confirmation of what was updated
    """
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)
    list_fields = {"user_roles", "functional_requirements", "existing_systems",
                   "constraints", "success_criteria", "covered_topics", "pending_questions"}
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
    thread_id = resolve_thread_id(thread_id)
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
    thread_id = resolve_thread_id(thread_id)
    profile = get_profile(thread_id)
    try:
        profile["pending_questions"] = json.loads(questions_json)
    except json.JSONDecodeError:
        profile["pending_questions"] = [questions_json]
    return f"Pending questions updated: {len(profile['pending_questions'])} questions."


# ── Workspace File Tools ──

from pathlib import Path
from app.core.workspace_files import WorkspaceFileManager


@tool
def list_workspace_files(
    workspace_id: str,
    pattern: str = "*",
    max_results: int = 50,
) -> str:
    """列出工作区中的文件清单。使用 glob 模式过滤。
    用此工具查看工作区有哪些文件可用。

    Args:
        workspace_id: 工作区 ID
        pattern: 文件名匹配模式，如 "*.md"、"docs/**"、"*需求*"
        max_results: 最多返回数（默认 50，最大 200）

    Returns:
        文件列表文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        files = fm.list_files(pattern, min(max_results, 200))
        if not files:
            return "工作区暂无文件。"
        lines = [f"共 {len(files)} 个文件：", ""]
        for f in files:
            summary = f.get("summary", "")
            summary_fragment = f" — {summary[:60]}" if summary else ""
            lines.append(
                f"- {f['path']} ({f.get('type', '?')}, "
                f"{_fmt_size(f.get('size', 0))})"
                f"{summary_fragment}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_workspace_files error: {e}")
        return f"无法列出工作区文件：{e}"


@tool
def read_workspace_file(
    workspace_id: str,
    file_path: str,
    max_chars: int = 8000,
) -> str:
    """读取工作区中指定文件的内容。
    用此工具获取文件全文来分析。
    .md 文件返回 Markdown 原文，Office 文档返回转换后的文本内容。

    Args:
        workspace_id: 工作区 ID
        file_path: 文件相对路径（从 list_workspace_files 获取）
        max_chars: 最大读取字符数（默认 8000，最大 100000）

    Returns:
        文件内容文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        result = fm.read_file(file_path, min(max_chars, 100000))
        header = f"--- {result['path']} ({_fmt_size(result['size'])}) ---\n"
        if result["truncated"]:
            header += f"[文件过长，仅显示前 {max_chars} 字符]\n"
        return header + result["text"]
    except FileNotFoundError as e:
        return f"文件不存在：{e}"
    except RuntimeError as e:
        return f"无法解析文件：{e}"
    except Exception as e:
        logger.error(f"read_workspace_file error: {e}")
        return f"读取文件失败：{e}"


@tool
def read_file_section(
    workspace_id: str,
    file_path: str,
    start_line: int = 1,
    end_line: int = 100,
) -> str:
    """读取大文件的指定行范围。对超大文件分段分析很有用。
    先看文件总行数再分段读取。

    Args:
        workspace_id: 工作区 ID
        file_path: 文件相对路径
        start_line: 起始行号（从 1 开始）
        end_line: 结束行号

    Returns:
        指定行范围内的文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        result = fm.read_file_section(file_path, start_line, end_line)
        lines_text = "\n".join(str(l) for l in result["lines"])
        return (
            f"--- {result['path']} 第 {result['start_line']}-{result['end_line']} 行 "
            f"(共 {result['total_lines']} 行) ---\n{lines_text}"
        )
    except FileNotFoundError as e:
        return f"文件不存在：{e}"
    except Exception as e:
        return f"读取文件失败：{e}"


@tool
def search_in_workspace(
    workspace_id: str,
    query: str,
    file_pattern: str = "*.md",
    max_results: int = 10,
) -> str:
    """在工作区文件中搜索关键词或短语。
    对 .md 和 .txt 文件做全文搜索。返回匹配文件及上下文片段。

    Args:
        workspace_id: 工作区 ID
        query: 搜索关键词
        file_pattern: 限定文件类型，默认 "*.md"
        max_results: 最多返回结果数（默认 10，最大 50）

    Returns:
        搜索结果文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        results = fm.search_files(query, file_pattern, min(max_results, 50))
        if not results:
            return f"在工作区文件中未找到包含「{query}」的内容。"
        lines = [f"搜索「{query}」共找到 {sum(r['match_count'] for r in results)} 处匹配：", ""]
        for r in results:
            lines.append(f"📄 {r['path']} ({r['match_count']} 处匹配):")
            for m in r["matches"][:5]:
                context = m["text"][:120]
                lines.append(f"  第 {m['line']} 行: {context}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"搜索失败：{e}"


@tool
def write_workspace_file(
    workspace_id: str,
    file_path: str,
    content: str,
) -> str:
    """在工作区中创建或更新文件。
    用于 AI 生成的产出——分析报告、需求总结、会议纪要等。
    文件会自动写入工作区的 _generated/ 子目录。
    如果内容中包含 [[链接]] 语法，会自动建立文件引用关系。

    Args:
        workspace_id: 工作区 ID
        file_path: 文件名（如 "分析报告-20260610.md"）
        content: 文件内容

    Returns:
        写入成功的消息
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        result = fm.write_file(file_path, content)

        # Trigger analysis in background
        try:
            from app.core.workspace_analyzer import _fire
            _fire(workspace_id, file_path)
        except Exception:
            pass

        # Parse [[links]] in content and create file references
        import re
        import asyncio
        WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
        link_titles = [t for t, _ in WIKILINK_RE.findall(content)]
        if link_titles and _datastore:
            targets = []
            all_files = fm.list_files()
            for title in link_titles:
                title = title.strip()
                if not title:
                    continue
                # Try workspace file match (fast, synchronous)
                if any(f["path"] == title for f in all_files):
                    targets.append((title, "file"))
                    continue
                # Try wiki page match (async — fire via ensure_future)
            # Save links asynchronously
            if targets:
                async def _save():
                    await _datastore.save_links(
                        workspace_id, file_path, "file", targets
                    )
                try:
                    asyncio.ensure_future(_save())
                except Exception:
                    pass
            # Wiki page resolution is done via ensure_future separately
            async def _resolve_wiki():
                for title in link_titles:
                    title = title.strip()
                    if not title:
                        continue
                    # Skip if already matched as file
                    if any(f["path"] == title for f in all_files):
                        continue
                    try:
                        page = await _datastore.resolve_wiki_title(workspace_id, title)
                        if page:
                            try:
                                await _datastore.save_links(
                                    workspace_id, file_path, "file",
                                    [(page["id"], "wiki")]
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
            try:
                asyncio.ensure_future(_resolve_wiki())
            except Exception:
                pass

        return f"文件已写入工作区：{result['path']} ({_fmt_size(result['size'])})"
    except Exception as e:
        return f"写入文件失败：{e}"


@tool
def get_workspace_info(workspace_id: str) -> str:
    """获取当前工作区的整体概况。
    返回项目名称、描述、文件总数及类型分布、所有文件清单。

    Args:
        workspace_id: 工作区 ID

    Returns:
        工作区概览文本
    """
    try:
        fm = WorkspaceFileManager(workspace_id)
        info = fm.get_info()
        lines = [
            f"📁 工作区文件概况",
            f"   文件总数: {info['file_count']}",
        ]
        if info["by_type"]:
            type_str = ", ".join(f"{k}: {v}个" for k, v in info["by_type"].items())
            lines.append(f"   类型分布: {type_str}")
        if info["by_source"]:
            src_str = ", ".join(f"{k}: {v}个" for k, v in info["by_source"].items())
            lines.append(f"   来源分布: {src_str}")
        lines.append("")
        if info["files"]:
            lines.append("文件清单：")
            for f in info["files"]:
                summary = f.get("summary", "")
                s = f" - {f['path']} ({f.get('type', '?')})"
                if summary:
                    s += f" — {summary[:80]}"
                lines.append(s)
        else:
            lines.append("（暂无文件）")
        return "\n".join(lines)
    except Exception as e:
        return f"获取工作区信息失败：{e}"


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / 1024 / 1024:.1f}MB"
