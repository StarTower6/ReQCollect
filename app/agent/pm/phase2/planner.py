"""Phase 2: PRD section planner v2 — scene-aware dynamic outline.

Recognizes project type from profile fields, then selects
matching sections and prompt weights dynamically.
"""

import json
import re
from enum import Enum
from typing import Any

from loguru import logger

from app.agent.pm.prompts import PRD_SECTION_ORDER, PRD_SECTION_TEMPLATES, PRD_SCENE_PROMPT_OVERRIDES


class SceneType(str, Enum):
    NEW_SYSTEM = "新建系统"           # 默认
    SYSTEM_UPGRADE = "系统改造升级"    # 替换/升级/二期
    REPORT_BI = "报表_BI看板"         # 报表/看板/BI
    APPROVAL_FLOW = "审批流系统"      # 审批/审核/会签
    DATA_GOVERNANCE = "数据治理项目"   # 数据质量/清洗/标准
    API_INTEGRATION = "接口集成项目"   # 主要是系统间打通
    SIMPLE_TOOL = "简单工具类"        # 内部小工具


class SectionWeight(str, Enum):
    SKIP = "skip"
    LIGHT = "light"
    NORMAL = "normal"
    HEAVY = "heavy"


def _field_text(profile: dict, *fields: str) -> str:
    """Concatenate multiple profile fields into one text blob for matching."""
    parts = []
    for f in fields:
        v = profile.get(f, "")
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(item) for item in v)
        elif isinstance(v, dict):
            parts.append(str(v))
    return " ".join(parts)


def _count_list(profile: dict, field: str) -> int:
    v = profile.get(field, [])
    return len(v) if isinstance(v, list) else 0


class SceneRecognizer:
    """Identify project scene from requirement profile via keyword matching."""

    def recognize(self, profile: dict) -> SceneType:
        text = _field_text(profile,
            "business_background", "current_process",
            "functional_requirements", "business_flow")
        funcs_text = _field_text(profile, "functional_requirements")
        existing = _field_text(profile, "existing_systems")
        role_count = _count_list(profile, "user_roles")
        func_count = _count_list(profile, "functional_requirements")

        # 系统改造
        if (profile.get("existing_systems")
                and re.search(r"优化|升级|改造|替换|二期|迭代|重构|切换|迁移", text)):
            return SceneType.SYSTEM_UPGRADE

        # 报表/BI 看板
        if re.search(r"报表|看[板幕]|统计|仪表盘|BI|大屏|驾驶舱|趋势图|数据分析", funcs_text):
            if not re.search(r"审批|审核|下单|采购|报销|入库|出库|生产", text):
                return SceneType.REPORT_BI

        # 审批流系统
        if re.search(r"审批|审核|复核|会签|签批|报销|审批流", text) and role_count >= 3:
            return SceneType.APPROVAL_FLOW

        # 数据治理
        if (profile.get("data_scale")
                and re.search(r"数据质量|数据标准|数据迁移|数据治理|数据清洗|数据规范|主数据", text)):
            return SceneType.DATA_GOVERNANCE

        # 接口集成
        if _count_list(profile, "existing_systems") >= 2 and func_count <= 3:
            if not re.search(r"界面|页面|录入|填写|填报", funcs_text):
                return SceneType.API_INTEGRATION

        # 简单工具
        if role_count <= 2 and func_count <= 3 and not profile.get("existing_systems"):
            if not profile.get("business_flow"):
                return SceneType.SIMPLE_TOOL

        return SceneType.NEW_SYSTEM


class DynamicPlanner:
    """Plan PRD sections with scene-aware dynamic selection."""

    def __init__(self):
        self.recognizer = SceneRecognizer()

    def plan(self, profile: dict, mode: str = "one_shot") -> list[dict]:
        scene = self.recognizer.recognize(profile)
        logger.info(f"Scene recognized: {scene.value}")

        # Get scene definition
        scene_config = SCENE_SECTION_MAP.get(scene, SCENE_SECTION_MAP[SceneType.NEW_SYSTEM])
        section_weights: dict[str, SectionWeight] = scene_config["weights"]
        # Apply section order from config, fallback to PRD_SECTION_ORDER
        section_order = scene_config.get("order", PRD_SECTION_ORDER)

        sections = []
        for key in section_order:
            if key not in PRD_SECTION_TEMPLATES:
                continue
            weight = section_weights.get(key, SectionWeight.NORMAL)
            if weight == SectionWeight.SKIP:
                continue

            template = PRD_SECTION_TEMPLATES[key]
            base_prompt = template["prompt"]
            prompt = base_prompt.format(profile_context=self._format_profile(profile))

            # Apply weight override
            override_key = f"{scene.value}_{key}"
            if weight == SectionWeight.HEAVY and override_key in PRD_SCENE_PROMPT_OVERRIDES:
                prompt += "\n\n" + PRD_SCENE_PROMPT_OVERRIDES[override_key]
            elif weight == SectionWeight.LIGHT:
                prompt += "\n\n注意：请精简描述，控制在 200 字以内，突出重点即可。"

            sections.append({
                "key": key,
                "title": template["title"],
                "status": "pending",
                "prompt": prompt,
                "content": "",
            })

        scene_label = scene_config.get("label", scene.value)
        logger.info(f"PRD plan created: {len(sections)} sections, scene={scene_label}, mode={mode}")
        return sections

    def get_scene_label(self, profile: dict) -> str:
        scene = self.recognizer.recognize(profile)
        config = SCENE_SECTION_MAP.get(scene, SCENE_SECTION_MAP[SceneType.NEW_SYSTEM])
        return config.get("label", scene.value)

    @staticmethod
    def _format_profile(profile: dict) -> str:
        return json.dumps(profile, ensure_ascii=False, indent=2)


# ── Scene section maps ──

_SCENE_SECTION_DEFAULTS: dict[str, Any] = {
    "weights": {},
    "order": list(PRD_SECTION_ORDER),
}


def _scene_config(weights: dict[str, SectionWeight],
                  order: list[str] | None = None,
                  label: str | None = None) -> dict[str, Any]:
    return {
        "weights": {k: SectionWeight(v) for k, v in weights.items()},
        "order": order or list(PRD_SECTION_ORDER),
        "label": label,
    }


SCENE_SECTION_MAP: dict[SceneType, dict[str, Any]] = {
    SceneType.NEW_SYSTEM: _scene_config(
        {},
        label="新建系统",
    ),

    SceneType.SYSTEM_UPGRADE: _scene_config(
        {
            "system_integration": "heavy",
            "constraints": "heavy",
            "data_requirements": "light",
        },
        label="系统改造升级",
    ),

    SceneType.REPORT_BI: _scene_config(
        {
            "user_roles": "heavy",
            "data_requirements": "heavy",
            "functional_requirements": "heavy",
            "business_flow": "light",
            "non_functional": "light",
            "constraints": "skip",
        },
        order=["project_overview", "user_roles", "data_requirements",
               "functional_requirements", "existing_systems",
               "non_functional", "acceptance"],
        label="报表/BI 看板",
    ),

    SceneType.APPROVAL_FLOW: _scene_config(
        {
            "business_flow": "heavy",
            "user_roles": "heavy",
            "data_requirements": "skip",
        },
        label="审批流系统",
    ),

    SceneType.DATA_GOVERNANCE: _scene_config(
        {
            "data_requirements": "heavy",
            "existing_systems": "heavy",
            "business_flow": "light",
            "non_functional": "skip",
            "user_roles": "light",
        },
        order=["project_overview", "data_requirements", "existing_systems",
               "functional_requirements", "constraints", "acceptance"],
        label="数据治理项目",
    ),

    SceneType.API_INTEGRATION: _scene_config(
        {
            "existing_systems": "heavy",
            "business_flow": "light",
            "non_functional": "light",
            "data_requirements": "skip",
            "constraints": "skip",
        },
        order=["project_overview", "existing_systems", "functional_requirements",
               "non_functional", "acceptance"],
        label="接口集成项目",
    ),

    SceneType.SIMPLE_TOOL: _scene_config(
        {
            "business_flow": "skip",
            "existing_systems": "skip",
            "non_functional": "skip",
            "data_requirements": "skip",
            "constraints": "skip",
        },
        order=["project_overview", "user_roles", "functional_requirements",
               "constraints", "acceptance"],
        label="简单工具类",
    ),
}


prd_planner = DynamicPlanner()
