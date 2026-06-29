#!/bin/bash
# ============================================================
#  一站式: push onedir fix + CI + download + SMB
#  用法:bash ship_windows_oneder.sh
# ============================================================
set -e
cd "$(dirname "$0")"

TOKEN="${GITHUB_TOKEN:-}"
REPO="Felix-GG55/yijing"
API="https://api.github.com"
AUTH="Authorization: token $TOKEN"
VER="Accept: application/vnd.github+json"
GHV="X-GitHub-Api-Version: 2022-11-28"

REQUIRED_SHA="2fee61b"

echo "==> 1/7  本地 HEAD"
HEAD=$(git rev-parse --short HEAD)
echo "    HEAD=$HEAD (no auto-reset; amend loop avoided)"

echo "==> 2/7  push 到 origin"
git config http.version HTTP/1.1
git config http.sslBackend openssl
git config http.postBuffer 524288000

PUSH_OK=0
for TRY in 1 2 3 4 5; do
  echo "    [try $TRY/5]"
  if GIT_TERMINAL_PROMPT=0 git push origin main --force 2>&1 | tail -3; then
    if git ls-remote --heads origin main | grep -q "$REQUIRED_SHA"; then
      PUSH_OK=1
      break
    fi
  fi
  echo "    没推到 $REQUIRED_SHA,等 ${TRY}5s 重试..."
  sleep $((TRY*5))
done
[ "$PUSH_OK" = "1" ] || { echo "[fail] push 5 次都失败"; exit 1; }

echo "==> 3/7  trigger workflow dispatch"
curl -sS -X POST -H "$AUTH" -H "$VER" -H "$GHV" \
  -d "{\"ref\":\"main\"}" \
  "$API/repos/$REPO/actions/workflows/build-windows.yml/dispatches" \
  -w "    HTTP=%{http_code}\n" || true

echo "==> 4/7  等待 build (max 10 min) ..."
RUN_ID=""
for i in $(seq 1 60); do
  sleep 10
  RUNS=$(curl -sS -H "$AUTH" -H "$VER" -H "$GHV" \
    "$API/repos/$REPO/actions/runs?per_page=10")
  SHA=$(printf "%s" "$RUNS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for r in d.get('workflow_runs',[]):
    if r['head_sha'].startswith('$REQUIRED_SHA'):
        print(r['status'], r['conclusion'] or '-', r['id'])
        break
")
  echo "    [$(date +%H:%M:%S)] ${SHA:-not yet}"
  if echo "$SHA" | grep -q "^completed success"; then
    RUN_ID=$(echo "$SHA" | awk "{print \$3}")
    break
  fi
  if echo "$SHA" | grep -q "^completed failure"; then
    RID=$(echo "$SHA" | awk "{print \$3}")
    echo "[fail] build 失败,https://github.com/$REPO/actions/runs/$RID"
    exit 1
  fi
done

if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "0" ]; then
  echo "[timeout] https://github.com/$REPO/actions"
  exit 1
fi

echo "==> 5/7  下载 artifact (run $RUN_ID)"
ART=$(curl -sS -H "$AUTH" -H "$VER" -H "$GHV" \
  "$API/repos/$REPO/actions/runs/$RUN_ID/artifacts" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); [print(a['archive_download_url']) for a in d.get('artifacts',[]) if a['name']=='YiJing-windows-exe']" | head -1)
[ -z "$ART" ] && { echo "[fail] no artifact"; exit 1; }

rm -rf dist_win
mkdir -p dist_win
curl -sS -L -H "$AUTH" -o dist_win/YiJing-windows-exe.zip "$ART"
( cd dist_win && unzip -oq YiJing-windows-exe.zip )

if [ ! -f dist_win/YiJing/YiJing.exe ]; then
  echo "[warn] 没有 onedir 结构,看实际:"
  find dist_win -maxdepth 2 -type f
  exit 1
fi
ONEDIR_COUNT=$(find dist_win/YiJing -type f | wc -l | tr -d ' ')
echo "    onedir 验证 OK: $ONEDIR_COUNT 个文件"

echo "==> 6/7  打 zip (含运行说明)"
ZIP=/tmp/YiJing_Windows_v2.0_oneder.zip
rm -f "$ZIP"
( cd dist_win && zip -rq "$ZIP" YiJing )
SIZE=$(stat -f%z "$ZIP" 2>/dev/null || stat -c%s "$ZIP")
echo "    zip: $ZIP ($SIZE bytes)"
echo "    使用方法:Windows 解压后,进入 YiJing 目录,双击 YiJing.exe 即可"

echo "==> 7/7  拷到 SMB"
SMB_DIR="/Volumes/gg 共享给我/qi"
if [ -d "$SMB_DIR" ]; then
  # 删旧 v1 (单文件 exe)
  rm -f "$SMB_DIR/YiJing.exe"
  rm -rf "$SMB_DIR/YiJing" 2>/dev/null || true
  cp "$ZIP" "$SMB_DIR/"
  cp -R dist_win/YiJing "$SMB_DIR/YiJing/"
  echo "    OK 已拷到 SMB:"
  ls -lah "$SMB_DIR/" | grep -iE "YiJing|oneder" || true
else
  echo "    SMB 没挂,zip 在 $ZIP 备用"
fi

echo
echo "============================================"
echo " 完成!onedir 包已就绪"
echo " SMB 路径:$SMB_DIR"
echo " 本地 zip:$ZIP"
echo "============================================"
