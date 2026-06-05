#!/usr/bin/env bash
# GitHub Issue 操作工具集
# 封装常见的 issue 操作：读取、评论、关闭
#
# 使用:
#   export GITHUB_TOKEN=github_pat_xxx
#   ./github-issue.sh get StarTower6/ReQCollect 1
#   ./github-issue.sh close StarTower6/ReQCollect 1 "fix: reason"
#   ./github-issue.sh comment StarTower6/ReQCollect 1 "message"

set -euo pipefail

# Auto-load token from local config files
if [ -z "${GITHUB_TOKEN:-}" ]; then
  if [ -f /home/startower/.claude/.github.env ]; then
    source /home/startower/.claude/.github.env
  elif [ -f ~/.github.env ]; then
    source ~/.github.env
  fi
fi

API_BASE="https://api.github.com"

_require_token() {
  if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ 需要设置 GITHUB_TOKEN 环境变量" >&2
    echo "   获取: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens" >&2
    exit 1
  fi
}

_curl() {
  curl -sf -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" "$@"
}

_usage() {
  echo "用法: $0 <command> <repo> <issue-number> [args...]"
  echo ""
  echo "命令:"
  echo "  get     <repo> <issue>              — 获取 issue 详情"
  echo "  close   <repo> <issue> [comment]    — 关闭 issue（可选附带 comment）"
  echo "  comment <repo> <issue> <body>       — 添加评论"
  echo "  list    <repo>                       — 列出 open issues"
  echo ""
  echo "示例:"
  echo "  $0 get StarTower6/ReQCollect 1"
  echo "  $0 close StarTower6/ReQCollect 1 'fix: 已修复多选bug'"
  echo "  $0 comment StarTower6/ReQCollect 1 '已推送修复'"
  exit 1
}

cmd="${1:-}"
repo="${2:-}"
issue="${3:-}"

_require_token

case "$cmd" in
  get)
    [ -z "$issue" ] && _usage
    echo "📥 Fetching issue #$issue from $repo ..." >&2
    data=$( _curl "$API_BASE/repos/$repo/issues/$issue" )
    echo "$data" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Title: {d[\"title\"]}')
print(f'State: {d[\"state\"]}')
print(f'Labels: {[l[\"name\"] for l in d.get(\"labels\",[])]}')
print(f'--- Body ---')
print(d.get('body','')[:3000])
"
    ;;

  close)
    [ -z "$issue" ] && _usage
    comment_body="${4:-}"
    echo "🔒 Closing issue #$issue in $repo ..." >&2
    result=$( _curl -X PATCH "$API_BASE/repos/$repo/issues/$issue" \
      -H "Content-Type: application/json" \
      -d '{"state":"closed"}' )
    echo "✅ Issue #$(echo "$result" | python3 -c 'import json,sys;print(json.load(sys.stdin)["number"])') → closed"

    if [ -n "$comment_body" ]; then
      comment_result=$( _curl -X POST "$API_BASE/repos/$repo/issues/$issue/comments" \
        -H "Content-Type: application/json" \
        -d "$(python3 -c "import json; print(json.dumps({'body': '$comment_body'}))")" )
      echo "💬 Comment posted"
    fi
    ;;

  comment)
    body="${4:-}"
    [ -z "$body" ] && _usage
    echo "💬 Posting comment on issue #$issue in $repo ..." >&2
    result=$( _curl -X POST "$API_BASE/repos/$repo/issues/$issue/comments" \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "import json; print(json.dumps({'body': '$body'}))")" )
    echo "✅ Comment posted: id=$(echo "$result" | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')"
    ;;

  list)
    echo "📋 Listing open issues for $repo ..." >&2
    _curl "$API_BASE/repos/$repo/issues?state=open&per_page=20" | python3 -c "
import json, sys
issues = json.load(sys.stdin)
for i in issues:
    labels = ' '.join([l['name'] for l in i.get('labels',[])])
    print(f'#{i[\"number\"]:>4}  [{i[\"state\"]:>5}]  {i[\"title\"][:70]}  {labels}')
"
    ;;

  *)
    _usage
    ;;
esac
