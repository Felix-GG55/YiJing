#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易经 AI 解卦 - 道士人设 + OpenAI 兼容 API
默认 DeepSeek(中文好/便宜),可换 OpenAI/Qwen/GLM 等
"""
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path

try:
    import yi_core as core
except ImportError:
    core = None

CONFIG_FILE = Path.home() / "Documents" / "qi" / "notes" / "yi_expert.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
}

# v4.0.1: 已知错误的 model 占位名 → 真实可用的 model 名
# 用户在 v3.x 时手填的占位符(如 minimax-chat),会被自动纠正并回写磁盘
MODEL_NAME_MIGRATION = {
    "minimax-chat":      "MiniMax-Text-01",
    "minimax":           "MiniMax-Text-01",
    "MiniMax-chat":      "MiniMax-Text-01",
    "MiniMax":           "MiniMax-Text-01",
    "abab5.5-chat":      "MiniMax-Text-01",
    "abab6.5s-chat":     "MiniMax-Text-01",
}

SYSTEM_PROMPT = """你是一位道行深厚的道士,精研《周易》数十年,通晓王弼注与朱熹《周易本义》,
能以现代白话为求测者解卦。

【解卦规矩】
- 主卦(本卦)代表当前局势/起因
- 互卦代表事情内在的过程、隐藏因素
- 变卦代表事情发展趋向、最终结果
- 动爻(老阳/老阴)是关键转折,务必着墨
- 引用 卦辞/象传/爻辞 时必须忠于原文,不要杜撰
- 若无动爻,主卦为主、互卦为辅

【表达要求】
- 语气沉稳温和,有长者风,不夸张不恐吓
- 用现代白话,少用玄学术语,必要时用括号解释
- 给出可操作的建议,不是空泛安慰
- 长度 400-800 字,结构清晰
- 不要重复用户已经知道的事实(卦象本身)

【格式】
请按以下结构分段落(每段以粗体小标题起头,小标题单独一行,不要 Markdown #):
**整体局势** - 主卦含义
**关键转折** - 动爻分析(无动爻则说"目前无显著变爻,以本卦论")
**内在脉络** - 互卦
**发展趋向** - 变卦或以主卦为终
**行动指引** - 2-3 条具体建议
"""


def load_config():
    merged = _load_config_raw()
    # 纠正已知错误的 model 占位符
    model = (merged.get("model") or "").strip()
    new_model = MODEL_NAME_MIGRATION.get(model)
    if new_model and new_model != model:
        merged["model"] = new_model
        # 回写磁盘,避免每次启动都纠正
        try:
            save_config(merged)
        except Exception:
            pass
    return merged


def _load_config_raw():
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            if isinstance(cfg, dict):
                merged.update(cfg)
            return merged
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _hex_info(num):
    if core is None or num is None:
        return None
    h = core.HEX_BY_NUM.get(num)
    if not h:
        return None
    return {
        "num": h[0],
        "name": h[1],
        "upper": h[2],
        "lower": h[3],
        "binary": h[4],
        "guaci": h[5],
        "xiangzhuan": h[6],
        "lines": h[7],
    }


def build_user_prompt(question, cast_result, extra=""):
    """构造给 LLM 的 user prompt。extra 为可选附加引用。"""
    main = _hex_info(cast_result.get("main_num"))
    nuclear = _hex_info(cast_result.get("nuclear_num"))
    changed_num = cast_result.get("changed_num")
    changed = _hex_info(changed_num) if changed_num else None

    moving = []
    for i, l in enumerate(cast_result.get("lines", []), 1):
        if l[2] in ("老阴", "老阳"):
            moving.append(i)

    parts = []
    parts.append(f"求测者所问:{question or '(无特定问题,以整体运势问之)'}")
    parts.append("")

    if main:
        parts.append(f"主卦(本卦):第{main['num']}卦 {main['name']}({main['upper']}上 {main['lower']}下)")
        parts.append(f"  卦辞:{main['guaci']}")
        parts.append(f"  象传:{main['xiangzhuan']}")
        parts.append(f"  爻辞:")
        for ln in main['lines']:
            parts.append(f"    {ln}")
        parts.append("")

    if nuclear and nuclear['num'] != main['num']:
        parts.append(f"互卦:第{nuclear['num']}卦 {nuclear['name']}({nuclear['upper']}上 {nuclear['lower']}下)")
        parts.append(f"  卦辞:{nuclear['guaci']}")
        parts.append(f"  象传:{nuclear['xiangzhuan']}")
        parts.append("")

    if changed:
        parts.append(f"变卦:第{changed['num']}卦 {changed['name']}({changed['upper']}上 {changed['lower']}下)")
        parts.append(f"  卦辞:{changed['guaci']}")
        parts.append(f"  象传:{changed['xiangzhuan']}")
        parts.append("")
    else:
        parts.append("变卦:无(本卦无动爻,主卦为终)")
        parts.append("")

    if moving:
        parts.append(f"动爻位置:第 {','.join(map(str, moving))} 爻(共 {len(moving)} 个)")
    else:
        parts.append("动爻:无")
    parts.append("")
    parts.append("请据此解卦,以白话答之。")
    if extra:
        parts.append("")
        parts.append("=" * 50)
        parts.append("【附加引用】用户从典籍复制粘贴的权威经文/注疏,你必须以其为依据:")
        parts.append(extra.strip())
        parts.append("=" * 50)
    return "\n".join(parts)


def ask_stream(question, cast_result, on_token, on_done, on_error):
    """向后兼容的 wrapper。"""
    ask_stream_v4(question, cast_result, "", on_token, on_done, on_error, None)


def ask_stream_v4(question, cast_result, extra, on_token, on_done, on_error, stop_event=None):
    """v4:支持 extra 引用 + stop_event 中止。回调在工作线程。"""
    cfg = load_config()
    if not cfg.get("api_key"):
        on_error("未配置 API Key。请点 '设置 API'。")
        return

    user_prompt = build_user_prompt(question, cast_result, extra)
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
        "temperature": 0.7,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + cfg["api_key"],
    }
    url = cfg["base_url"].rstrip("/") + "/chat/completions"

    def worker():
        full = []
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            for k, v in headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=180) as resp:
                for raw_line in resp:
                    if stop_event is not None and stop_event.is_set():
                        on_error("用户停止")
                        return
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        obj = json.loads(data_str)
                    except Exception:
                        continue
                    choices = obj.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        full.append(token)
                        on_token(token)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                err_body = str(e)
            on_error("HTTP " + str(e.code) + ": " + err_body)
            return
        except Exception as e:
            on_error(type(e).__name__ + ": " + str(e))
            return
        on_done("".join(full))

    threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    sample = {
        "question": "近期事业",
        "lines": [(7, 1, "少阳"), (6, 0, "老阴"), (7, 1, "少阳"),
                  (6, 0, "老阴"), (6, 0, "老阴"), (7, 1, "少阳")],
        "main_num": 1,
        "nuclear_num": 1,
        "changed_num": 1,
    }
    print(build_user_prompt("近期事业", sample))
    print("\n--- config ---")
    print(load_config())
