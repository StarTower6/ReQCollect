"""Lightweight fallback extraction for requirement profile fields."""

import re

from app.agent.pm.tools import get_profile

PROJECT_TYPES = [
    "SaaS",
    "内部系统",
    "管理系统",
    "Web",
    "网站",
    "移动应用",
    "小程序",
    "APP",
    "平台",
    "工具",
    "Agent",
    "助手",
]

INDUSTRIES = [
    "餐饮",
    "外卖",
    "电商",
    "教育",
    "金融",
    "医疗",
    "制造",
    "物流",
    "零售",
    "人力资源",
    "企业服务",
    "政务",
    "旅游",
    "房产",
]

LIST_SPLIT_RE = re.compile(r"[、,，;/；\s]+")
SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;\n]")


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


def _merge_module_objects(existing: list, modules: list[str]) -> list:
    seen = {
        item.get("module", "") if isinstance(item, dict) else str(item)
        for item in existing
    }
    merged = list(existing)
    for module in modules:
        if module and module not in seen:
            merged.append({"module": module})
            seen.add(module)
    return merged


def _extract_project_name(message: str) -> str:
    patterns = [
        r"(?:项目|产品|系统)?(?:叫|名称是|名字是)[:：]?\s*([^，。；;\n]{2,40})",
        r"(?:我想|想要|准备|计划)?(?:做|开发|建设|打造)(?:一个|一套)?([^，。；;\n]{2,40}?(?:系统|平台|工具|应用|小程序|APP|Agent|助手))",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ，,。")
    return ""


def _extract_list_after_keywords(message: str, keywords: list[str]) -> list[str]:
    keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
    pattern = rf"(?:{keyword_pattern})[^。；;\n]*?(?:包括|有|是|为)[:：]?\s*([^。；;\n]+)"
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

    if not profile.get("project_name"):
        project_name = _extract_project_name(text)
        if project_name:
            profile["project_name"] = project_name
            changed.append("project_name")

    if not profile.get("project_type"):
        for project_type in PROJECT_TYPES:
            if project_type.lower() in text.lower():
                profile["project_type"] = project_type
                changed.append("project_type")
                break

    if not profile.get("industry"):
        industry_match = re.search(r"(?:行业|领域|场景)(?:是|为|：|:)?\s*([^，。；;\n]{2,20})", text)
        if industry_match:
            profile["industry"] = industry_match.group(1).strip()
            changed.append("industry")
        else:
            for industry in INDUSTRIES:
                if industry in text:
                    profile["industry"] = industry
                    changed.append("industry")
                    break

    if not profile.get("elevator_pitch") and re.search(r"痛点|解决|目标|价值|为了|希望", text):
        profile["elevator_pitch"] = _first_sentence(text)
        changed.append("elevator_pitch")

    roles = _extract_list_after_keywords(text, ["主要用户", "用户角色", "用户", "角色", "面向"])
    if roles:
        before = len(profile.get("user_roles", []))
        profile["user_roles"] = _merge_role_objects(profile.get("user_roles", []), roles)
        if len(profile["user_roles"]) > before:
            changed.append("user_roles")

    modules = _extract_list_after_keywords(text, ["核心功能", "功能模块", "功能", "模块"])
    if modules:
        before = len(profile.get("functional_modules", []))
        profile["functional_modules"] = _merge_module_objects(
            profile.get("functional_modules", []),
            modules,
        )
        if len(profile["functional_modules"]) > before:
            changed.append("functional_modules")

    if re.search(r"性能|安全|并发|可用性|稳定性|合规|权限|响应时间", text):
        non_functional = dict(profile.get("non_functional") or {})
        if "raw" not in non_functional:
            non_functional["raw"] = _first_sentence(text)
            profile["non_functional"] = non_functional
            changed.append("non_functional")

    if re.search(r"约束|限制|预算|周期|上线|技术栈|必须|不能", text):
        before = len(profile.get("constraints", []))
        profile["constraints"] = _merge_strings(profile.get("constraints", []), [_first_sentence(text)])
        if len(profile["constraints"]) > before:
            changed.append("constraints")

    if re.search(r"假设|默认|先按|暂定|认为", text):
        before = len(profile.get("assumptions", []))
        profile["assumptions"] = _merge_strings(profile.get("assumptions", []), [_first_sentence(text)])
        if len(profile["assumptions"]) > before:
            changed.append("assumptions")

    if changed:
        profile["covered_topics"] = _merge_strings(profile.get("covered_topics", []), changed)

    return changed
