#!/usr/bin/env python3
"""
从 yi_core.py 重新生成 web/index.html 所需的内嵌数据。

用法:
    python3 tools/export_web_data.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yi_core

hex_data = []
for h in yi_core.HEX:
    num, name, up, lo, binary, judgment, image, lines = h
    hex_data.append({
        "num": num, "name": name, "upper": up, "lower": lo,
        "binary": binary, "guaci": judgment, "xiangzhuan": image,
        "lines": list(lines),
    })

trigrams = {}
for k, v in yi_core.TRIGRAMS.items():
    trigrams["".join(map(str, k))] = {"name": v[0], "nature": v[1], "trait": v[2]}

payload = {"hex": hex_data, "trigrams": trigrams}
js_header = (
    "// Auto-generated from yi_core.py\n"
    "// 64-hex data + 8 trigrams, 用于网页易经\n"
    "\n"
)
js = js_header + "const YI_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"

# 注入到 index.html
html_path = ROOT / "web" / "index.html"
if not html_path.exists():
    print(f"[fail] {html_path} 不存在,请先 web/index.html 存在再跑")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")
import re

# 找到已有的内联数据块 <script>const YI_DATA = ...</script>
m = re.search(r"<script>\s*const YI_DATA = \{.*?\};\s*</script>", html, re.DOTALL)
# 内联数据块可能夹了 header 注释 //, 使用平衡 {} 查找
idx = html.find("const YI_DATA = {")
if idx < 0:
    print("[fail] 没找到 const YI_DATA = {")
    sys.exit(1)
depth = 0
end = -1
for i, c in enumerate(html[idx:]):
    if c == '{': depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            end = idx + i + 1  # exclusive end (after '}')
            break
if end < 0:
    print("[fail] 数据块未闭合")
    sys.exit(1)
# 找这个数据块所属的 <script> 开始位置
script_start = html.rfind("<script>", 0, idx)
# 找这个 </script> 结束位置
script_end = html.find("</script>", end) + len("</script>")
if script_start < 0 or script_end < 0:
    print("[fail] 没找到包裹的 <script> 标签")
    sys.exit(1)
m_start, m_end = script_start, script_end
if True:
    new_html = html[:m_start] + "<script>\n" + js + "</script>" + html[m_end:]
    html_path.write_text(new_html, encoding="utf-8")
    print(f"[ok] 内联数据已更新: {len(hex_data)} 卦, {len(trigrams)} 卦符")
    print(f"     {html_path} ({len(new_html)} chars)")
else:
    print("[fail] 没找到内联数据块,请检查 index.html 格式")
    sys.exit(1)
