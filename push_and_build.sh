#!/bin/bash
# ============================================================
#  易经三钱法 — 一键 push + 触发 Windows build + 下载 YiJing.exe
#  用法:GITHUB_TOKEN=ghp_xxx bash push_and_build.sh
#  或:bash push_and_build.sh ghp_xxx
# ============================================================
set -e
cd "$(dirname "$0")"

TOKEN="${GITHUB_TOKEN:-${1:-}}"
if [ -z "$TOKEN" ]; then
  echo "[错误] 需要 token。运行方式:"
  echo "  GITHUB_TOKEN=ghp_xxx bash $0"
  exit 1
fi

API="https://api.github.com"
AUTH="Authorization: token $TOKEN"
VER="Accept: application/vnd.github+json"
GHV="X-GitHub-Api-Version: 2022-11-28"
REPO="${REPO:-yijing}"
WF="build-windows.yml"

echo "==> 1/6  验证 token"
USER_INFO=$(curl -sS -H "$AUTH" -H "$VER" -H "$GHV" "$API/user")
USERNAME=$(printf '%s' "$USER_INFO" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login',''))")
if [ -z "$USERNAME" ]; then
  echo "[错误] token 无效,返回:"
  echo "$USER_INFO"
  exit 1
fi
echo "    登录用户: $USERNAME"

echo "==> 2/6  检查仓库 $USERNAME/$REPO"
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" -H "$AUTH" -H "$VER" -H "$GHV" "$API/repos/$USERNAME/$REPO")
if [ "$HTTP_CODE" = "404" ]; then
  echo "    仓库不存在,正在创建..."
  CREATE_RES=$(curl -sS -X POST -H "$AUTH" -H "$VER" -H "$GHV" \
    -d "{\"name\":\"$REPO\",\"description\":\"易经三钱法 Windows .exe builder\",\"public\":true,\"auto_init\":false}" \
    "$API/user/repos")
  if echo "$CREATE_RES" | grep -q '"message"'; then
    echo "[错误] 仓库创建失败:"
    echo "$CREATE_RES" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('message',''))"
    echo "请手动创建空仓库:https://github.com/new (name=$REPO, public, 不要勾 README/.gitignore/license)"
    echo "然后重跑本脚本。"
    exit 1
  fi
  echo "    已创建"
elif [ "$HTTP_CODE" = "200" ]; then
  echo "    仓库已存在"
else
  echo "[错误] 仓库查询失败 HTTP $HTTP_CODE"
  exit 1
fi

# 沙箱网络对 GitHub 的 HTTP/2 支持有问题,降到 HTTP/1.1
git config --global http.version HTTP/1.1
git config --global http.postBuffer 524288000
REPO_URL="https://x-access-token:$TOKEN@github.com/$USERNAME/$REPO.git"
echo "==> 3/6  push 代码到 $USERNAME/$REPO"
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git branch -M main 2>/dev/null || true
git push -u origin main --force

echo "==> 4/6  触发 workflow build-windows-exe"
DISP=$(curl -sS -X POST -H "$AUTH" -H "$VER" -H "$GHV" \
  -d "{\"ref\":\"main\"}" \
  "$API/repos/$USERNAME/$REPO/actions/workflows/$WF/dispatches")
if [ -n "$DISP" ] && echo "$DISP" | grep -q '"message"'; then
  echo "[错误] 触发失败:$DISP"
  exit 1
fi
echo "    已触发"

echo "==> 5/6  等待 build 完成(最多 8 分钟)..."
RUN_ID=""
for i in $(seq 1 48); do
  sleep 10
  RUNS=$(curl -sS -H "$AUTH" -H "$VER" -H "$GHV" \
    "$API/repos/$USERNAME/$REPO/actions/workflows/$WF/runs?per_page=1")
  READ=$(printf '%s' "$RUNS" | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin)
  rs=d.get('workflow_runs',[])
  if rs:
    print(rs[0]['status'], rs[0]['conclusion'] or '', rs[0]['id'])
  else:
    print('NONE NONE 0')
except: print('PARSE_ERR NONE 0')
" 2>/dev/null)
  STATUS=$(echo "$READ" | awk '{print $1}')
  CONC=$(echo "$READ" | awk '{print $2}')
  RID=$(echo "$READ" | awk '{print $3}')
  printf "    [%02d/48] 状态:%-10s 结论:%-10s\n" "$i" "$STATUS" "$CONC"
  if [ "$STATUS" = "completed" ] && [ "$CONC" = "success" ]; then
    RUN_ID="$RID"
    break
  fi
  if [ "$STATUS" = "completed" ] && [ "$CONC" != "success" ]; then
    echo "[错误] build 失败,查看:https://github.com/$USERNAME/$REPO/actions/runs/$RID"
    exit 1
  fi
done

if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "0" ]; then
  echo "[超时] 请手动查看:https://github.com/$USERNAME/$REPO/actions"
  exit 1
fi

echo "==> 6/6  下载 artifact (run $RUN_ID)"
ART_URL=$(curl -sS -H "$AUTH" -H "$VER" -H "$GHV" \
  "$API/repos/$USERNAME/$REPO/actions/runs/$RUN_ID/artifacts" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); arts=d.get('artifacts',[]); print(arts[0]['archive_download_url'] if arts else '')" 2>/dev/null)
if [ -z "$ART_URL" ]; then
  echo "[错误] 没找到 artifact"
  echo "  https://github.com/$USERNAME/$REPO/actions/runs/$RUN_ID"
  exit 1
fi

mkdir -p dist_win
curl -sS -L -H "$AUTH" -o dist_win/YiJing-windows-exe.zip "$ART_URL"
cd dist_win
unzip -oq YiJing-windows-exe.zip
cd ..

echo
echo "============================================"
if [ -f dist_win/dist/YiJing.exe ]; then
  SIZE=$(stat -f%z dist_win/dist/YiJing.exe 2>/dev/null || stat -c%s dist_win/dist/YiJing.exe 2>/dev/null)
  echo " 完成!YiJing.exe 已生成"
  echo " 路径:$(pwd)/dist_win/dist/YiJing.exe"
  echo " 大小:${SIZE} 字节(约 $((SIZE/1048576)) MB)"
  echo " 直接双击运行,或拷给任何 Windows 用户"
else
  echo " 找到 artifact 但结构异常:"
  find dist_win -type f
fi
echo "============================================"

