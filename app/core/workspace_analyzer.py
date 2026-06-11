"""Background file analyzer — LLM-based summary, tag, domain extraction.

Invoked asynchronously after file upload/write/sync.
Analysis results stored in workspace file index as "analysis" field.
Failures degrade silently — analysis is optional enrichment.
"""

import re
import json
from loguru import logger

# Regex to extract JSON from LLM markdown-wrapped responses
_JSON_IN_MD = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_llm_json(raw: str) -> dict | None:
    """Extract a JSON object from LLM output, tolerating markdown code blocks."""
    if not raw or not raw.strip():
        return None
    m = _JSON_IN_MD.search(raw)
    if m:
        raw = m.group(1)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def analyze_workspace_file(workspace_id: str, file_path: str) -> dict:
    """Analyze file: extract summary, tags, domain via LLM.

    Idempotent: skips if analysis already exists.
    Never raises: returns empty result on any error.
    """
    from app.core.workspace_files import WorkspaceFileManager
    from app.core.llm_factory import llm_factory
    from app.config import config

    fm = WorkspaceFileManager(workspace_id)

    # Skip if already analyzed
    info = fm.get_file_info(file_path)
    if info and info.get("analysis"):
        return info["analysis"]

    try:
        content = fm.read_file(file_path, max_chars=4000)
    except Exception:
        logger.debug(f"[ws analyze] Can't read {workspace_id}/{file_path}")
        fm.upsert_analysis(file_path, {"summary": "", "tags": [], "domain": ""})
        return {"summary": "", "tags": [], "domain": ""}

    text = (content.get("text") or "").strip()
    if not text:
        fm.upsert_analysis(file_path, {"summary": "", "tags": [], "domain": ""})
        return {"summary": "", "tags": [], "domain": ""}

    prompt = (
        "Analyze the following file content. Return ONLY a JSON object:\n"
        '{"summary": "one-sentence summary in Chinese, max 30 characters", '
        '"tags": ["tag1", "tag2", "tag3"], '
        '"domain": "related requirement domain in Chinese (e.g. 审批流系统, 数据治理, 报表)"}\n\n'
        f"File: {file_path}\n\nContent:\n{text[:3000]}"
    )

    try:
        model = llm_factory.create_chat_model(
            model=config.llm_model, temperature=0.1, streaming=False
        )
        response = await model.ainvoke(prompt)
        result_text = response.content if hasattr(response, "content") else str(response)
        result = _parse_llm_json(result_text) or {"summary": "", "tags": [], "domain": ""}
    except Exception as e:
        logger.warning(f"[ws analyze] LLM call failed for {file_path}: {e}")
        result = {"summary": "", "tags": [], "domain": ""}

    fm.upsert_analysis(file_path, result)
    logger.info(f"[ws analyze] {workspace_id}/{file_path}: {result.get('summary')}")
    return result
