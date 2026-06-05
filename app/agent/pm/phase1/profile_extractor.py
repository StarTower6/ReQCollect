"""Lightweight fallback extraction for business requirement profile fields."""

import re

from app.agent.pm.tools import get_profile

BUSINESS_SYSTEMS = [
    "用友", "ERP", "OA", "MES", "HR", "CRM", "WMS", "SCM", "PLM",
    "企业微信", "钉钉", "飞书", "金蝶", "SAP", "Oracle",
]

PROJECT_TYPES = [
    "报销", "审批", "采购", "仓储", "物流", "生产", "质检",
    "财务", "人事", "考勤", "绩效", "培训", "文档", "合同",
]

LIST_SPLIT_RE = re.compile(r"[、,，;/；\s]+")
SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;\\n]")


def _first_sentence(text: str) -> str:
    for part in SENTENCE_SPLIT_RE.split(text):
        value = part.strip(" ，,：:")
        if value:
            return value
    return text.strip()


def _split_items(raw: str) -> list[str]:
    items = []
    for item in LIST_SPLIT_RE.split(raw):
        value = item.strip(" ：:。,.，")
        if 1 < len(value) <= 30:
            items.append(value)
    return items


def _merge_strings(existing: list, values: list[str]) -> list:
    seen = {str(item) for item in existing}
    merged = list(existing)
    for value in values:
        if value and value not in seen:
            merged.append(value)
            seen.add(value)
    return merged


def _merge_role_objects(existing: list, roles: list[str]) -> list:
    seen = {item.get("role", "") if isinstance(item, dict) else str(item) for item in existing}
    merged = list(existing)
    for role in roles:
        if role and role not in seen:
            merged.append({"role": role})
            seen.add(role)
    return merged


def _extract_project_name(message: str) -> str:
    patterns = [
        r"(?:项目|系统)?(?:叫|名称是|名字是)[:：]?\s*([^，。；;\\n]{2,40})",
        r"(?:我想|想要|准备|计划|需要)?(?:做|建设|开发|搭建|搞)(?:一个|一套)?([^，。；;\\n]{2,40}?(?:系统|平台|工具|功能|模块))",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ，,。")
    return ""


def _extract_list_after_keywords(message: str, keywords: list[str]) -> list[str]:
    keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
    pattern = rf"(?:{keyword_pattern})[^。；;\\n]*?(?:包括|有|是|为|涉及)[:：]?\s*([^。；;\\n]+)"
    match = re.search(pattern, message)
    if not match:
        return []
    return _split_items(match.group(1))


def apply_profile_hints(thread_id: str, message: str) -> list[str]:
    """Extract obvious profile fields from user text when tool calls miss them.

    This is intentionally conservative. It only fills empty scalar fields and
    merges list fields, leaving model tool updates as the primary source.
    """
    text = message.strip()
    if not text:
        return []

    profile = get_profile(thread_id)
    changed: list[str] = []

    # project_name
    if not profile.get("project_name"):
        project_name = _extract_project_name(text)
        if project_name:
            profile["project_name"] = project_name
            changed.append("project_name")

    # business_background
    if not profile.get("business_background") and re.search(r"痛点|问题|麻烦|现状|目前|现在|困扰|效率低|手工|纸质|烦", text):
        profile["business_background"] = _first_sentence(text)
        changed.append("business_background")

    # current_process
    if not profile.get("current_process") and re.search(r"流程|步骤|手工|纸质|Excel|邮件|OA|系统", text):
        profile["current_process"] = _first_sentence(text)
        changed.append("current_process")

    # existing_systems
    found_systems = [sys for sys in BUSINESS_SYSTEMS if sys in text]
    if found_systems:
        before = len(profile.get("existing_systems", []))
        profile["existing_systems"] = _merge_strings(profile.get("existing_systems", []), found_systems)
        if len(profile["existing_systems"]) > before:
            changed.append("existing_systems")

    # user_roles
    roles = _extract_list_after_keywords(text, ["主要用户", "使用角色", "角色", "部门", "面向", "谁用"])
    if roles:
        before = len(profile.get("user_roles", []))
        profile["user_roles"] = _merge_role_objects(profile.get("user_roles", []), roles)
        if len(profile["user_roles"]) > before:
            changed.append("user_roles")

    # functional_requirements
    modules = _extract_list_after_keywords(text, ["核心功能", "功能需求", "功能", "模块", "需要支持", "要能做"])
    if modules:
        before = len(profile.get("functional_requirements", []))
        existing = profile.get("functional_requirements", [])
        seen = {item.get("module", "") if isinstance(item, dict) else str(item) for item in existing}
        for m in modules:
            if m not in seen:
                existing.append({"module": m})
                seen.add(m)
        profile["functional_requirements"] = existing
        if len(profile["functional_requirements"]) > before:
            changed.append("functional_requirements")

    # business_flow
    if not profile.get("business_flow") and re.search(r"业务流|流程|链路|步骤|先是|然后|最后", text):
        profile["business_flow"] = _first_sentence(text)
        changed.append("business_flow")

    # data_scale
    if not profile.get("data_scale") and re.search(r"数据量|并发|每天|每月|条|用户数|几千|几万|上百", text):
        profile["data_scale"] = _first_sentence(text)
        changed.append("data_scale")

    # constraints
    if re.search(r"约束|限制|预算|工期|周期|上线|必须|不能| deadline|截止", text):
        before = len(profile.get("constraints", []))
        profile["constraints"] = _merge_strings(profile.get("constraints", []), [_first_sentence(text)])
        if len(profile["constraints"]) > before:
            changed.append("constraints")

    # success_criteria
    if not profile.get("success_criteria") and re.search(r"验收|标准|做成|目标|期望|效果|指标| KPI", text):
        profile["success_criteria"] = [_first_sentence(text)]
        changed.append("success_criteria")

    if changed:
        profile["covered_topics"] = _merge_strings(profile.get("covered_topics", []), changed)

    return changed
