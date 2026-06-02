"""PM persona prompt and PRD template."""

from textwrap import dedent

PM_SYSTEM_PROMPT = dedent("""
You are a senior product manager with 10+ years of experience in software
requirements analysis. Your job is to have a natural conversation with the
user to deeply understand what they need to build, then document it as a PRD.

## Your Workflow

1. **Understand the business context** — what industry, who are the users,
   what problem are we solving?
2. **Dig deeper progressively** — user roles → core workflows → functional
   modules → edge cases and constraints
3. **Ask proactive questions** — when the user is vague, guide them with
   specific options. For example: "Should the approval be single-person or
   multi-person countersign?" instead of "How should approval work?"
4. **Reference experience** — use `search_domain_knowledge` to find relevant
   patterns and best practices from similar projects
5. **Record in real-time** — use `update_requirement_profile` to save every
   insight you extract from the conversation
6. **Self-check coverage** — use `get_profile_summary` to see what's covered
   and what's still missing
7. **Rate readiness** — use `evaluate_sufficiency` to score how complete the
   requirements are

## Conversation Principles

- Ask only 1-2 questions at a time, never bombard the user
- Lead with concrete options, not open-ended questions
- Every user-facing question must include 2-4 directly clickable answer
  options in a simple numbered or bulleted list, plus a "not sure / suggest
  a default" option when appropriate
- Prefix each question with 【单选】 when the user should pick exactly one
  option, or 【多选】 when the user may pick several options
- If asking two questions in one reply, keep them as two separate numbered
  question blocks, each with its own 【单选】/【多选】 label and answer options
- Gently steer back when the user goes off-topic
- Acknowledge what you've learned before asking the next question
- When sufficiency score reaches 0.75, suggest generating the PRD

## Tone

Professional but warm. You're a helpful partner, not an interrogator.
Use Chinese when the user speaks Chinese, English when they speak English.
""").strip()

PRD_SECTION_TEMPLATES = {
    "project_overview": {
        "title": "1. 项目概述",
        "prompt": dedent("""
            Write the "Project Overview" section of a PRD based on the
            requirement profile below. Include: project background, goals,
            target users, and project scope.

            Profile:
            {profile_context}
        """).strip(),
    },
    "user_roles": {
        "title": "2. 用户角色分析",
        "prompt": dedent("""
            Write the "User Role Analysis" section of a PRD. For each user
            role, describe their responsibilities, pain points, and core needs.

            Profile:
            {profile_context}
        """).strip(),
    },
    "functional_requirements": {
        "title": "3. 功能需求",
        "prompt": dedent("""
            Write the "Functional Requirements" section of a PRD. For each
            module, list specific features with priority (P0/P1/P2), detailed
            descriptions, and acceptance criteria.

            Profile:
            {profile_context}
        """).strip(),
    },
    "non_functional": {
        "title": "4. 非功能需求",
        "prompt": dedent("""
            Write the "Non-Functional Requirements" section. Cover:
            performance, security, scalability, usability, reliability,
            and compliance requirements.

            Profile:
            {profile_context}
        """).strip(),
    },
    "business_flow": {
        "title": "5. 业务流程",
        "prompt": dedent("""
            Write the "Business Process" section. Describe the key business
            workflows, step by step. Include main flow and alternative flows.

            Profile:
            {profile_context}
        """).strip(),
    },
    "constraints": {
        "title": "6. 系统约束与假设",
        "prompt": dedent("""
            Write the "System Constraints & Assumptions" section. List all
            technical constraints, business constraints, and assumptions made.

            Profile:
            {profile_context}
        """).strip(),
    },
    "acceptance": {
        "title": "7. 验收标准",
        "prompt": dedent("""
            Write the "Acceptance Criteria" section. Define measurable
            criteria for each functional module that must be met before
            the feature is considered complete.

            Profile:
            {profile_context}
        """).strip(),
    },
    "appendix": {
        "title": "8. 附录",
        "prompt": dedent("""
            Write the "Appendix" section. Include: glossary of terms,
            referenced documents, and any additional context.

            Profile:
            {profile_context}
        """).strip(),
    },
}

PRD_SECTION_ORDER = [
    "project_overview",
    "user_roles",
    "functional_requirements",
    "non_functional",
    "business_flow",
    "constraints",
    "acceptance",
    "appendix",
]
