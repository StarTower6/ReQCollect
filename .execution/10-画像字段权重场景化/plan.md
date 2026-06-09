# Plan: 10 — 画像字段权重场景化

## 1. 任务理解
- 需求来源: PRD 场景化动态大纲上线后，画像字段的完整度权重也应随场景调整
- 核心目标: sufficiency.py 的权重根据场景动态变化，不同场景下核心字段权重更高

## 2. 改动清单
- 修改: `app/agent/pm/phase1/sufficiency.py` — 新增场景权重配置 + 运行时识别场景调权
- 不改: 其他任何文件（API 不变、前端不变、service 不变）

## 3. 验收标准
- [ ] P0: 默认（新建系统）权重不变，完整度评分与之前一致
- [ ] P0: 报表场景下 data_scale + functional_requirements 权重提升
- [ ] P0: 审批流场景下 business_flow + user_roles 权重提升
- [ ] P0: 系统改造场景下 existing_systems + current_process 权重提升
- [ ] P0: 所有 evaluate_profile_completeness() 调用方无需改动
- [ ] P1: 其他 4 种场景权重适配

## 4. 实施步骤
1. sufficiency.py — 新增 SCENE_WEIGHT_MAP 配置
2. evaluate_profile_completeness() 加入场景识别调权逻辑
3. 验证各场景权重变化
