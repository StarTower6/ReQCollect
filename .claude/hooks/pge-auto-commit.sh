#!/bin/bash
# pge-auto-commit hook — 评估报告生成后自动提交并推送
# 由 .claude/settings.json 中的 PostToolUse 钩子触发
# 当检测到 report.md 被写入时，自动 commit 所有改动

set -e

# 检查是否是 report.md 写入
if echo "$CLAUDE_FILE_PATHS" | grep -q "report\.md"; then
  # 提取功能名称
  FEATURE=$(echo "$CLAUDE_FILE_PATHS" | grep -oP '\.execution/\K[^/]+(?=/report\.md)')
  
  if [ -n "$FEATURE" ]; then
    # 提交所有改动（plan.md + tasks.md + report.md + 代码）
    cd "$CLAUDE_PROJECT_DIR"
    git add -A
    git commit -m "pge: $FEATURE — complete (plan + generate + evaluate)" 2>/dev/null || true
    git push 2>/dev/null || echo "Push skipped (no changes or network issue)"
    echo "✅ PGE cycle for '$FEATURE' auto-committed and pushed"
  fi
fi
