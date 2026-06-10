"""AI-enhanced Wiki features: auto-create from session, suggest content, PRD import."""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.llm_factory import llm_factory


def _ds():
    from app.main import get_datastore
    d = get_datastore()
    if d is None:
        raise RuntimeError("DataStore not initialized")
    return d


router = APIRouter()


# ── Models ──


class WikiAIRequest(BaseModel):
    workspace_id: str
    title: str = ""
    context: str = ""


class WikiSuggestRequest(BaseModel):
    page_id: str
    existing_content: str = ""
    title: str = ""


class WikiPRDRequest(BaseModel):
    workspace_id: str
    title: str
    prd_markdown: str


# ── Routes ──


@router.post("/wiki/ai/create")
async def wiki_ai_create(
    body: WikiAIRequest,
    current_user: dict = Depends(get_current_user),
):
    """AI generates a wiki page from session context / description."""
    if not body.context.strip():
        raise HTTPException(status_code=400, detail="Context cannot be empty")

    title = body.title.strip() or "AI 生成文档"
    prompt = (
        f"你是一个需求分析师，请根据以下对话记录/上下文，生成一份结构化 Wiki 文档。\n\n"
        f"## 上下文\n{body.context}\n\n"
        f"## 要求\n"
        f"1. 文档标题：{title}\n"
        f"2. 用 Markdown 格式输出\n"
        f"3. 按以下章节组织（如果相关内容缺失则不写该章节）：\n"
        f"   - ## 需求概述\n"
        f"   - ## 业务背景\n"
        f"   - ## 功能描述\n"
        f"   - ## 约束条件\n"
        f"   - ## 验收标准\n"
        f"4. 语言：中文\n"
        f"5. 不要输出多余的解释，直接输出 Markdown 正文"
    )

    try:
        llm = llm_factory.create_chat_model(temperature=0.5, streaming=False)
        response = llm.invoke(prompt)
        content = response.content.strip()
    except Exception as e:
        logger.error(f"AI wiki create failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI 生成失败: {e}")

    ds = _ds()
    page = await ds.create_wiki_page(
        workspace_id=body.workspace_id,
        title=title,
        content=content,
        created_by=current_user["id"],
    )
    logger.info(f"AI created wiki page: '{page['title']}' by {current_user['username']}")
    return {"success": True, "page": page}


@router.post("/wiki/ai/suggest")
async def wiki_ai_suggest(
    body: WikiSuggestRequest,
    current_user: dict = Depends(get_current_user),
):
    """AI suggests what content to add to an existing wiki page."""
    prompt = (
        f"你是一个需求分析师，请分析以下 Wiki 页面的现有内容，找出缺失的重要章节。\n\n"
        f"## 页面标题\n{body.title}\n\n"
        f"## 现有内容\n{body.existing_content or '(空)'}\n\n"
        f"## 要求\n"
        f"1. 判断哪些标准章节缺失：需求概述、业务背景、功能描述、约束条件、验收标准\n"
        f"2. 对每个缺失的章节，生成一段 Markdown 内容\n"
        f"3. 如果某个章节已有内容则不输出\n"
        f"4. 格式：## 章节标题 + 正文\n"
        f"5. 语言：中文\n"
        f"6. 直接输出建议补充的 Markdown 内容，不要多余解释"
    )

    try:
        llm = llm_factory.create_chat_model(temperature=0.5, streaming=False)
        response = llm.invoke(prompt)
        suggestion = response.content.strip()
    except Exception as e:
        logger.error(f"AI suggest failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI 建议失败: {e}")

    return {"success": True, "suggestion": suggestion}


@router.post("/wiki/ai/from-prd")
async def wiki_ai_from_prd(
    body: WikiPRDRequest,
    current_user: dict = Depends(get_current_user),
):
    """Convert a PRD (Markdown) into a structured wiki page."""
    prompt = (
        f"你是一个需求分析师，请将以下 PRD 文档转换为结构化的 Wiki 页面。\n\n"
        f"## 页面标题\n{body.title}\n\n"
        f"## PRD 原文\n{body.prd_markdown}\n\n"
        f"## 要求\n"
        f"1. 提炼核心内容，去除冗余\n"
        f"2. 用 Markdown 格式输出\n"
        f"3. 按以下章节组织（如果某章节无内容则不写）：\n"
        f"   - ## 需求概述\n"
        f"   - ## 业务背景\n"
        f"   - ## 功能描述\n"
        f"   - ## 约束条件\n"
        f"   - ## 验收标准\n"
        f"4. 语言：中文\n"
        f"5. 不要输出多余解释，直接输出 Markdown 正文"
    )

    try:
        llm = llm_factory.create_chat_model(temperature=0.5, streaming=False)
        response = llm.invoke(prompt)
        content = response.content.strip()
    except Exception as e:
        logger.error(f"AI PRD->wiki failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI 转换失败: {e}")

    ds = _ds()
    page = await ds.create_wiki_page(
        workspace_id=body.workspace_id,
        title=body.title.strip(),
        content=content,
        created_by=current_user["id"],
    )
    logger.info(f"Wiki page from PRD: '{page['title']}' by {current_user['username']}")
    return {"success": True, "page": page}
