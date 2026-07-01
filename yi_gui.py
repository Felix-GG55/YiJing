#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄妙易经 v4.0  ─  单页界面 + 八卦元素 + 典籍引用 + AI 解卦
===================================================
  Item 1 美化:红黑金配色、太极图、八卦符
            河图洛书装饰、卦象 Canvas 重绘
  Item 2 优化:起卦→解读→问道士一体流,无 Tab 切换
  Item 3 集成:131 本周易/老子/参同契 典籍索引,
            附加引用框可直接贴入 AI prompt
  Item 4 AI 报错:v3.4 已修复(URL 匹配强制覆盖 model)
"""
import os
import sys
import json
import math
import datetime
import threading
import subprocess
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

try:
    import yi_core as core
except ImportError:
    core = None

import yi_expert

# ============================================================
# 配色
# ============================================================
THEME = {
    "bg":       "#F5E9D0",
    "panel":    "#FDF6E3",
    "ink":      "#1A1A1A",
    "accent":   "#B22222",
    "gold":     "#B8860B",
    "gold_lt":  "#D4AF37",
    "line_old": "#C8102E",
    "yang":     "#1A1A1A",
    "yin":      "#3D2817",
    "muted":    "#6B5B4F",
    "trigram_bg": "#FFF8E7",
}

# ============================================================
# 八卦符号
# ============================================================
TRIGRAM_SYM = {
    "乾": "☰", "兑": "☱", "离": "☲", "震": "☳",
    "巽": "☴", "坎": "☵", "艮": "☶", "坤": "☷",
}
TRIGRAM_WUXING = {
    "乾": "金", "兑": "金", "离": "火", "震": "木",
    "巽": "木", "坎": "水", "艮": "土", "坤": "土",
}
TRIGRAM_DEITY = {
    "乾": "天", "兑": "泽", "离": "火", "震": "雷",
    "巽": "风", "坎": "水", "艮": "山", "坤": "地",
}

# ============================================================
# 资源路径(支持 PyInstaller frozen)
# ============================================================
def _bundle_dir():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _user_dir():
    return Path.home() / "Documents" / "qi"


def load_books_manifest():
    """读取打包的典籍清单。"""
    p = _bundle_dir() / "yi_books_manifest.json"
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"categories": {}}


def open_path(path):
    """用系统默认程序打开文件/URL。"""
    if not path:
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        try:
            webbrowser.open(Path(path).as_uri() if Path(path).exists() else path)
            return True
        except Exception:
            return False


# ============================================================
# 卦象绘制
# ============================================================
def draw_hex_canvas(canvas, binary, lines=None, moving_idx=None):
    """在 canvas 上画 6 根爻(从下到上)。binary='111111' 表全阳。"""
    canvas.delete("all")
    w = int(canvas["width"])
    h = int(canvas["height"])
    pad_x = 18
    pad_y = 8
    line_w = w - 2 * pad_x
    line_thick = 6
    gap = (h - 2 * pad_y) // 6
    moving_idx = set(moving_idx or [])
    lines = lines or [None] * 6
    # binary 字符串按从下到上:binary[0]=初爻, binary[5]=上爻
    for i in range(6):
        y_center = h - pad_y - i * gap - gap // 2
        kind = binary[i] if i < len(binary) else "1"
        is_old = (i + 1) in moving_idx  # i+1 = 爻位 1..6
        # 阳爻 solid,阴爻 broken
        if kind == "1":
            # 阳爻
            x0 = pad_x
            x1 = pad_x + line_w
            canvas.create_rectangle(
                x0, y_center - line_thick // 2,
                x1, y_center + line_thick // 2,
                fill=THEME["line_old"] if is_old else THEME["yang"],
                outline="",
            )
        else:
            # 阴爻 broken: 两段
            seg = line_w // 2 - 4
            y0 = y_center - line_thick // 2
            y1 = y_center + line_thick // 2
            color = THEME["line_old"] if is_old else THEME["yin"]
            canvas.create_rectangle(pad_x, y0, pad_x + seg, y1, fill=color, outline="")
            canvas.create_rectangle(pad_x + seg + 8, y0, pad_x + 2 * seg + 8, y1, fill=color, outline="")
        # 老爻上盖 O/X
        if is_old:
            color = THEME["line_old"]
            if kind == "1":
                # 老阳 ─O─
                r = 7
                canvas.create_oval(
                    pad_x + line_w // 2 - r, y_center - r,
                    pad_x + line_w // 2 + r, y_center + r,
                    fill=THEME["bg"], outline=color, width=2,
                )
                canvas.create_text(
                    pad_x + line_w // 2, y_center,
                    text="O", fill=color, font=("Noto Sans CJK SC", 8, "bold"),
                )
            else:
                # 老阴 ─X─
                canvas.create_line(
                    pad_x + line_w // 2 - 5, y_center - 5,
                    pad_x + line_w // 2 + 5, y_center + 5,
                    fill=color, width=2,
                )
                canvas.create_line(
                    pad_x + line_w // 2 - 5, y_center + 5,
                    pad_x + line_w // 2 + 5, y_center - 5,
                    fill=color, width=2,
                )
# ============================================================
# 主类
# ============================================================

class YiApp:
    """玄妙易经 v4.0 单页应用。"""

    LOG_DIR = Path.home() / "Documents" / "qi" / "logs"

    def __init__(self, root):
        self.root = root
        self._setup_root()
        self._setup_styles()

        # 数据
        self.books = load_books_manifest()
        self.current_cast = None
        self.last_question = ""

        # UI 控件缓存(供后续刷新)
        self.hex_canvases = {}   # {"main": canvas, ...}
        self.hex_titles   = {}   # 卦名
        self.hex_meta     = {}   # 上下卦符
        self.txt_guaci    = None
        self.txt_lines    = None
        self.txt_extra    = None
        self.txt_expert   = None
        self.status_var   = tk.StringVar(value="就绪")
        self.expert_status_var = tk.StringVar(value="")
        self.summary_var  = tk.StringVar(value="尚未起卦")

        self._build_header()
        self._build_cast_row()
        self._build_hex_panels()
        self._build_interpretation()
        self._build_expert_panel()
        self._build_books_panel()
        self._build_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_books_tree()

    # ----------------------------------------------------------------
    # 基础设置
    # ----------------------------------------------------------------
    def _setup_root(self):
        self.root.title("玄妙易经  v4.0")
        self.root.geometry("1280x780")
        self.root.minsize(1100, 700)
        self.root.configure(bg=THEME["bg"])

    def _setup_styles(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass

        # 全局配色
        s.configure(".",            background=THEME["bg"], foreground=THEME["ink"])
        s.configure("TFrame",       background=THEME["bg"])
        s.configure("Panel.TFrame", background=THEME["panel"], relief="flat")
        s.configure("Card.TFrame",  background=THEME["panel"], relief="solid", borderwidth=1)
        s.configure("TLabel",       background=THEME["bg"],    foreground=THEME["ink"],   font=("Noto Serif CJK SC", 11))
        s.configure("Panel.TLabel", background=THEME["panel"], foreground=THEME["ink"],   font=("Noto Serif CJK SC", 11))
        s.configure("Muted.TLabel", background=THEME["panel"], foreground=THEME["muted"], font=("Noto Serif CJK SC", 10))
        s.configure("Title.TLabel", background=THEME["bg"],    foreground=THEME["accent"], font=("Noto Serif CJK SC", 22, "bold"))
        s.configure("Sub.TLabel",   background=THEME["bg"],    foreground=THEME["muted"], font=("Noto Serif CJK SC", 11))
        s.configure("HexName.TLabel", background=THEME["panel"], foreground=THEME["accent"], font=("Noto Serif CJK SC", 14, "bold"))
        s.configure("HexMeta.TLabel", background=THEME["panel"], foreground=THEME["ink"], font=("Noto Sans CJK SC", 10))
        s.configure("HexRole.TLabel", background=THEME["panel"], foreground=THEME["gold"], font=("Noto Serif CJK SC", 11, "bold"))
        s.configure("Status.TLabel", background=THEME["gold"],  foreground=THEME["ink"], font=("Noto Serif CJK SC", 10))
        s.configure("TButton",      background=THEME["panel"], foreground=THEME["ink"], font=("Noto Serif CJK SC", 10), padding=(8, 4))
        s.map("TButton",  background=[("active", THEME["gold_lt"])])
        s.configure("Accent.TButton", background=THEME["accent"], foreground="#FFFFFF", font=("Noto Serif CJK SC", 11, "bold"), padding=(10, 5))
        s.map("Accent.TButton", background=[("active", "#8B1A1A")])
        s.configure("Gold.TButton",   background=THEME["gold"],   foreground=THEME["ink"],   font=("Noto Serif CJK SC", 10, "bold"), padding=(10, 4))
        s.map("Gold.TButton", background=[("active", THEME["gold_lt"])])
        s.configure("TEntry",      fieldbackground="#FFFFFF", foreground=THEME["ink"], font=("Noto Serif CJK SC", 11))
        s.configure("TNotebook",   background=THEME["bg"],    borderwidth=0)
        s.configure("TNotebook.Tab", background=THEME["panel"], foreground=THEME["ink"], padding=(10, 4), font=("Noto Serif CJK SC", 10))
        s.map("TNotebook.Tab", background=[("selected", THEME["accent"])], foreground=[("selected", "#FFFFFF")])
        s.configure("Treeview",    background="#FFFFFF", fieldbackground="#FFFFFF", foreground=THEME["ink"], font=("Noto Sans CJK SC", 10), rowheight=22)
        s.configure("Treeview.Heading", background=THEME["panel"], foreground=THEME["ink"], font=("Noto Serif CJK SC", 10, "bold"))

    # ----------------------------------------------------------------
    # Header — 标题 + 太极图 + 副标
    # ----------------------------------------------------------------
    def _build_header(self):
        head = ttk.Frame(self.root, style="TFrame", padding=(16, 8, 16, 4))
        head.pack(side="top", fill="x")

        # 左:太极图(canvas 绘)
        tjc = tk.Canvas(head, width=46, height=46, bg=THEME["bg"], highlightthickness=0)
        tjc.pack(side="left", padx=(0, 10))
        self._draw_taiji(tjc, 23, 23, 20)

        # 中:标题 + 副标
        mid = ttk.Frame(head)
        mid.pack(side="left", fill="x", expand=True)
        ttk.Label(mid, text="玄妙易经", style="Title.TLabel").pack(anchor="w")
        ttk.Label(mid, text="道生一,一生二,二生三,三生万物。万物负阴而抱阳,冲气以为和。",
                  style="Sub.TLabel").pack(anchor="w")

        # 右:版本 + API 设置
        right = ttk.Frame(head)
        right.pack(side="right")
        ttk.Button(right, text="设置 API", style="Gold.TButton",
                   command=self._show_expert_config).pack(side="right", padx=4)
        ttk.Label(right, text="v4.0", style="Sub.TLabel").pack(side="right", padx=6)

        # 分隔金线
        sep = tk.Frame(self.root, height=2, bg=THEME["gold"])
        sep.pack(side="top", fill="x", padx=16)

    def _draw_taiji(self, canvas, cx, cy, r):
        """画一个太极图。"""
        # 外圈
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           outline=THEME["ink"], width=2, fill=THEME["bg"])
        # 左半阴(黑)
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=90, extent=180, fill=THEME["ink"], outline="")
        # 右半阳(留白)
        # 上下两个小圆,头尾是对方颜色
        sr = r // 2
        canvas.create_oval(cx - sr, cy - r, cx + sr, cy,
                           fill=THEME["ink"], outline="")
        canvas.create_oval(cx - sr, cy, cx + sr, cy + r,
                           fill=THEME["bg"], outline=THEME["ink"], width=1)
        # 阴阳鱼眼
        er = r // 8
        canvas.create_oval(cx - er, cy - sr // 2 - er, cx + er, cy - sr // 2 + er,
                           fill=THEME["bg"], outline=THEME["ink"], width=1)
        canvas.create_oval(cx - er, cy + sr // 2 - er, cx + er, cy + sr // 2 + er,
                           fill=THEME["ink"], outline="")

    # ----------------------------------------------------------------
    # 起卦行
    # ----------------------------------------------------------------
    def _build_cast_row(self):
        row = ttk.Frame(self.root, style="TFrame", padding=(16, 8))
        row.pack(side="top", fill="x")
        ttk.Label(row, text="问事:", style="TLabel").pack(side="left")
        self.question_var = tk.StringVar()
        ent = ttk.Entry(row, textvariable=self.question_var, font=("Noto Serif CJK SC", 12))
        ent.pack(side="left", fill="x", expand=True, padx=8)
        ent.bind("<Return>", lambda _e: self._do_cast())
        ttk.Button(row, text="起 卦", style="Accent.TButton",
                   command=self._do_cast).pack(side="left", padx=2)
        ttk.Button(row, text="清 空", command=self._clear_cast).pack(side="left", padx=2)
    # ----------------------------------------------------------------
    # 三卦面板:本卦 / 互卦 / 变卦
    # ----------------------------------------------------------------
    def _build_hex_panels(self):
        wrap = ttk.Frame(self.root, style="TFrame", padding=(16, 4))
        wrap.pack(side="top", fill="x")
        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=1)
        wrap.columnconfigure(2, weight=1)

        for col, role in enumerate(["本卦(当前)", "互卦(内在)", "变卦(趋向)"]):
            card = ttk.Frame(wrap, style="Card.TFrame", padding=8)
            card.grid(row=0, column=col, sticky="nsew", padx=4)
            # role 标题
            role_key = {"本卦(当前)": "main", "互卦(内在)": "nuclear", "变卦(趋向)": "changed"}[role]
            ttk.Label(card, text=role, style="HexRole.TLabel").pack(anchor="w")
            # canvas
            cv = tk.Canvas(card, width=180, height=180, bg=THEME["trigram_bg"],
                           highlightthickness=1, highlightbackground=THEME["gold"])
            cv.pack(pady=6)
            self.hex_canvases[role_key] = cv
            # 卦名 + 序号
            self.hex_titles[role_key] = ttk.Label(card, text="—", style="HexName.TLabel")
            self.hex_titles[role_key].pack()
            # 上下卦符
            self.hex_meta[role_key] = ttk.Label(card, text="", style="HexMeta.TLabel")
            self.hex_meta[role_key].pack()

    def _render_hex(self, key, hex_obj, moving=None):
        """刷新某个卦的 canvas + 标签。"""
        cv = self.hex_canvases[key]
        if not hex_obj:
            cv.delete("all")
            self.hex_titles[key].config(text="—")
            self.hex_meta[key].config(text="")
            return
        draw_hex_canvas(cv, hex_obj["binary"], moving_idx=moving or [])
        n = hex_obj["num"]
        name = hex_obj["name"]
        sym_u = TRIGRAM_SYM.get(hex_obj["upper"], "?")
        sym_l = TRIGRAM_SYM.get(hex_obj["lower"], "?")
        wu_u = TRIGRAM_WUXING.get(hex_obj["upper"], "")
        wu_l = TRIGRAM_WUXING.get(hex_obj["lower"], "")
        self.hex_titles[key].config(text=f"第{n}卦 {name}")
        self.hex_meta[key].config(
            text=f"{sym_u}{wu_u}上 · {sym_l}{wu_l}下"
        )

    # ----------------------------------------------------------------
    # 解读区:卦辞 / 象传 / 动爻 + 爻辞
    # ----------------------------------------------------------------
    def _build_interpretation(self):
        wrap = ttk.LabelFrame(self.root, text="卦辞 · 象传 · 爻辞", padding=10)
        wrap.pack(side="top", fill="x", padx=16, pady=6)
        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=1)

        # 左:卦辞 + 象传
        left = ttk.Frame(wrap)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(left, text="卦辞 · 象传", style="HexRole.TLabel").pack(anchor="w")
        self.txt_guaci = scrolledtext.ScrolledText(left, height=4, font=("Noto Serif CJK SC", 11),
                                                    wrap="word", bg="#FFFFFF", relief="solid", borderwidth=1)
        self.txt_guaci.pack(fill="x", pady=2)
        self.txt_guaci.insert("end", "(尚未起卦)")
        self.txt_guaci.configure(state="disabled")

        # 右:动爻 + 爻辞
        right = ttk.Frame(wrap)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="动爻 · 爻辞", style="HexRole.TLabel").pack(anchor="w")
        self.txt_lines = scrolledtext.ScrolledText(right, height=4, font=("Noto Serif CJK SC", 11),
                                                    wrap="word", bg="#FFFFFF", relief="solid", borderwidth=1)
        self.txt_lines.pack(fill="x", pady=2)
        self.txt_lines.insert("end", "(尚未起卦)")
        self.txt_lines.configure(state="disabled")

    # ----------------------------------------------------------------
    # AI 道士区:附加引用 + 流式输出
    # ----------------------------------------------------------------
    def _build_expert_panel(self):
        wrap = ttk.LabelFrame(self.root, text="问  道  士  ─  AI 解卦", padding=10)
        wrap.pack(side="top", fill="both", expand=True, padx=16, pady=6)

        # 附加引用行
        ref_row = ttk.Frame(wrap)
        ref_row.pack(side="top", fill="x")
        ttk.Label(ref_row, text="附加引用(从右侧典籍复制粘贴经文,会作为权威依据注入 AI prompt):",
                  style="Muted.TLabel").pack(anchor="w")
        self.txt_extra = tk.Text(ref_row, height=3, font=("Noto Serif CJK SC", 11),
                                  wrap="word", bg="#FFF8E7", relief="solid", borderwidth=1,
                                  foreground=THEME["ink"])
        self.txt_extra.pack(fill="x", pady=2)

        # 按钮行
        btn_row = ttk.Frame(wrap)
        btn_row.pack(side="top", fill="x", pady=6)
        self.btn_ask = ttk.Button(btn_row, text="请道士解卦", style="Accent.TButton",
                                   command=self._ask_expert)
        self.btn_ask.pack(side="left")
        self.btn_stop = ttk.Button(btn_row, text="停止", command=self._stop_expert,
                                   state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        ttk.Button(btn_row, text="保存到日志", command=self._save_log,
                   style="Gold.TButton").pack(side="left", padx=4)
        ttk.Label(btn_row, textvariable=self.expert_status_var,
                  style="Muted.TLabel").pack(side="left", padx=10)

        # 输出区
        out_frame = ttk.Frame(wrap)
        out_frame.pack(side="top", fill="both", expand=True)
        self.txt_expert = scrolledtext.ScrolledText(out_frame, height=10, font=("Noto Serif CJK SC", 11),
                                                     wrap="word", bg="#FFFFFF", relief="solid", borderwidth=1,
                                                     foreground=THEME["ink"])
        self.txt_expert.pack(fill="both", expand=True)
        self.txt_expert.configure(state="disabled")
        # 流式 token 累积
        self._stream_buf = []

    # ----------------------------------------------------------------
    # 典籍侧栏
    # ----------------------------------------------------------------
    def _build_books_panel(self):
        wrap = ttk.LabelFrame(self.root, text="典  籍  ─  131 本", padding=6)
        wrap.pack(side="right", fill="y", padx=(0, 16), pady=(0, 16), ipadx=4)
        wrap.configure(width=280)
        # 分类 notebook
        nb = ttk.Notebook(wrap)
        nb.pack(fill="both", expand=True)
        self.books_nb = nb
        self.books_trees = {}

    def _update_books_tree(self):
        """用 self.books 数据填充典籍侧栏。"""
        cats = self.books.get("categories", {})
        for cat, books in cats.items():
            if cat in self.books_trees:
                continue
            f = ttk.Frame(self.books_nb)
            self.books_nb.add(f, text=f"{cat}({len(books)})")
            tree = ttk.Treeview(f, columns=("size",), show="tree headings", height=22)
            tree.heading("#0", text="书名")
            tree.heading("size", text="大小")
            tree.column("#0", width=180, anchor="w")
            tree.column("size", width=70, anchor="e")
            for b in books:
                size_kb = b["size"] // 1024
                if size_kb > 1024:
                    size_txt = f"{size_kb/1024:.1f}MB"
                else:
                    size_txt = f"{size_kb}KB"
                tree.insert("", "end", iid=f"{cat}::{b['name']}", text=b["name"][:40], values=(size_txt,))
            tree.pack(fill="both", expand=True)
            tree.bind("<Double-1>", self._on_book_double_click)
            self.books_trees[cat] = tree
        # 空时给个提示
        if not cats:
            ttk.Label(wrap, text="(未发现典籍清单)", style="Muted.TLabel").pack()

    def _on_book_double_click(self, _evt=None):
        tree = self.books_nb.focus_get()
        if not isinstance(tree, ttk.Treeview):
            return
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        if "::" not in iid:
            return
        cat, name = iid.split("::", 1)
        # 在 manifest 里找 path
        for b in self.books.get("categories", {}).get(cat, []):
            if b["name"] == name:
                ok = open_path(b["path"])
                self.status_var.set(f"打开 {name}... {'OK' if ok else '失败'}")
                return

    # ----------------------------------------------------------------
    # 状态栏
    # ----------------------------------------------------------------
    def _build_status_bar(self):
        bar = tk.Frame(self.root, height=22, bg=THEME["gold"])
        bar.pack(side="bottom", fill="x")
        ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel").pack(side="left", padx=8)
        ttk.Label(bar, textvariable=self.summary_var, style="Status.TLabel").pack(side="right", padx=8)
    # ----------------------------------------------------------------
    # 起卦 / 解读 / AI 解卦
    # ----------------------------------------------------------------
    def _do_cast(self):
        if core is None:
            messagebox.showerror("错误", "yi_core 未加载")
            return
        question = self.question_var.get().strip()
        self.last_question = question
        # 调 core.cast(自动三钱法 + 计算本/互/变)
        try:
            import time as _t
            cast = core.cast(question, seed=int(_t.time()))
        except TypeError:
            cast = core.cast(question)
        self.current_cast = cast
        lines = cast["lines"]

        # HEX tuple -> dict 包装(供 _render_hex 用)
        def _to_dict(h):
            if not h: return None
            return {"num": h[0], "name": h[1], "upper": h[2], "lower": h[3],
                    "binary": h[4], "guaci": h[5], "xiangzhuan": h[6], "lines": h[7]}
        main    = _to_dict(core.HEX_BY_NUM.get(cast["main_num"]))
        nuclear = _to_dict(core.HEX_BY_NUM.get(cast["nuclear_num"]))
        changed = _to_dict(core.HEX_BY_NUM.get(cast["changed_num"])) if cast.get("changed_num") else None

        moving = [i for i, l in enumerate(lines, 1) if l[2] in ("老阴", "老阳")]

        self._render_hex("main",    main,    moving if main else [])
        self._render_hex("nuclear", nuclear, [])
        self._render_hex("changed", changed, [])

        # 卦辞 / 象传
        guaci_lines = []
        if main:
            guaci_lines.append(f"【卦辞】{main['guaci']}")
            guaci_lines.append(f"【象传】{main['xiangzhuan']}")
        self._set_text(self.txt_guaci, "\n".join(guaci_lines) or "(无)")

        # 爻辞(主卦)
        line_lines = []
        if main:
            for idx, ltxt in enumerate(main["lines"], 1):
                marker = "★" if idx in moving else "·"
                line_lines.append(f" {marker} {ltxt}")
        if not moving:
            line_lines.append("【注】本卦无动爻,以主卦为终。")
        self._set_text(self.txt_lines, "\n".join(line_lines) or "(无)")

        # 状态摘要
        sig = []
        if main:
            sym_u = TRIGRAM_SYM.get(main["upper"], "?")
            sym_l = TRIGRAM_SYM.get(main["lower"], "?")
            sig.append(f"{main['name']} ({sym_u}{main['upper']}上 {sym_l}{main['lower']}下)")
        self.summary_var.set("  ".join(sig))
        self.status_var.set(f"起卦完成 · {datetime.datetime.now().strftime('%H:%M:%S')} · 动爻 {len(moving)} 个")

        self._save_log()

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def _clear_cast(self):
        self.question_var.set("")
        self.current_cast = None
        self.summary_var.set("尚未起卦")
        self.status_var.set("已清空")
        for k in ("main", "nuclear", "changed"):
            self._render_hex(k, None)
        self._set_text(self.txt_guaci, "(尚未起卦)")
        self._set_text(self.txt_lines, "(尚未起卦)")
        self._set_text(self.txt_expert, "(空)")
        self.txt_extra.delete("1.0", "end")

    # ----------------------------------------------------------------
    # AI 解卦(流式)
    # ----------------------------------------------------------------
    def _ask_expert(self):
        if not self.current_cast:
            messagebox.showinfo("提示", "请先起卦")
            return
        cfg = yi_expert.load_config()
        if not cfg.get("api_key"):
            messagebox.showinfo("提示", "尚未配置 API Key,请先点右上角 '设置 API'")
            return
        # reset UI
        self._set_text(self.txt_expert, "道士正在解卦,请稍候...\n\n")
        self._stream_buf = []
        self.btn_ask.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.expert_status_var.set("生成中…")
        self._stop_event = threading.Event()

        extra = self.txt_extra.get("1.0", "end").strip()
        threading.Thread(
            target=self._expert_worker,
            args=(extra,),
            daemon=True,
        ).start()

    def _stop_expert(self):
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        self.expert_status_var.set("已停止")
        self.btn_ask.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    def _expert_worker(self, extra):
        def on_token(tok):
            self._stream_buf.append(tok)
            # 用 after 切回主线程
            self.root.after(0, self._append_expert_text, tok)
        def on_done(_full):
            self.root.after(0, self._on_expert_done)
        def on_error(msg):
            self.root.after(0, self._on_expert_error, msg)

        cast = self.current_cast
        # 在 worker 里把 extra 注入 — 通过闭包变量传
        yi_expert.ask_stream_v4(
            self.last_question, cast, extra,
            on_token=on_token, on_done=on_done, on_error=on_error,
            stop_event=self._stop_event,
        )

    def _append_expert_text(self, tok):
        self.txt_expert.configure(state="normal")
        self.txt_expert.insert("end", tok)
        self.txt_expert.see("end")
        self.txt_expert.configure(state="disabled")

    def _on_expert_done(self):
        self.btn_ask.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.expert_status_var.set("✓ 解卦完成")
        self._save_log()

    def _on_expert_error(self, msg):
        self.btn_ask.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.expert_status_var.set("✗ 失败")
        self._set_text(self.txt_expert, f"[出错] {msg}\n\n(可点 '设置 API' 切换厂商或修正 model)")

    # ----------------------------------------------------------------
    # 日志
    # ----------------------------------------------------------------
    def _save_log(self):
        if not self.current_cast:
            return
        try:
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.LOG_DIR / f"cast_{ts}.txt"
            cast = self.current_cast
            main = core.HEX_BY_NUM.get(cast["main_num"])
            extra_txt = self.txt_extra.get("1.0", "end").strip()
            expert_txt = "".join(self._stream_buf) if self._stream_buf else self.txt_expert.get("1.0", "end").strip()
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# 时间: {datetime.datetime.now().isoformat()}\n")
                f.write(f"# 问事: {self.last_question}\n")
                if main:
                    f.write(f"# 主卦: 第{main[0]}卦 {main[1]}\n")
                    f.write(f"# 卦辞: {main[5]}\n")
                    f.write(f"# 象传: {main[6]}\n")
                f.write(f"# 动爻: {cast.get('moving', [])}\n\n")
                f.write("## 附加引用\n" + extra_txt + "\n\n")
                f.write("## AI 解卦\n" + expert_txt + "\n")
            self.status_var.set(f"已保存日志: {path.name}")
        except Exception as e:
            self.status_var.set(f"日志保存失败: {e}")

    # ----------------------------------------------------------------
    # 关闭
    # ----------------------------------------------------------------
    def _on_close(self):
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        self.root.destroy()
    # ----------------------------------------------------------------
    # 设置 API(v3.4:URL 匹配强制覆盖 model)
    # ----------------------------------------------------------------
    PRESETS = {
        "DeepSeek(默认,中文好,便宜)":  ("https://api.deepseek.com/v1",               "deepseek-chat"),
        "OpenAI":                          ("https://api.openai.com/v1",                 "gpt-4o-mini"),
        "通义千问 Qwen":                   ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-turbo"),
        "智谱 GLM":                        ("https://open.bigmodel.cn/api/paas/v4",      "glm-4-flash"),
        "月之暗面 Moonshot":               ("https://api.moonshot.cn/v1",                "moonshot-v1-8k"),
        "MiniMax / MiniMax":               ("https://api.MiniMax.chat/v1",          "MiniMax-Text-01"),
        "自定义(手动填 URL/Model)":        ("",                                          ""),
    }

    def _show_expert_config(self):
        win = tk.Toplevel(self.root)
        win.title("设置 AI 解卦 API")
        win.geometry("580x460")
        win.transient(self.root)
        win.configure(bg=THEME["bg"])
        win.grab_set()

        names = list(self.PRESETS.keys())

        cfg = yi_expert.load_config()
        cur_url   = (cfg.get("base_url", "") or "").strip() or "https://api.deepseek.com/v1"
        cur_model = (cfg.get("model",    "") or "").strip() or "deepseek-chat"

        # v4.0.1: URL 命中即选中 preset,model 字段强制覆盖为 preset 默认值 (防 minimax-chat 之类错字段)
        #          URL 比较 case-insensitive + 忽略尾部斜杠
        matched = "自定义(手动填 URL/Model)"
        cur_url_norm = cur_url.rstrip("/").lower()
        for n, (u, m) in self.PRESETS.items():
            if u and u.rstrip("/").lower() == cur_url_norm:
                matched = n
                if cur_model != m:
                    cur_model = m
                break

        ttk.Label(win, text="厂商预设(选完自动填 URL/Model)", padding=(10, 8, 0, 0),
                  font=("Noto Serif CJK SC", 11, "bold"),
                  foreground=THEME["accent"], background=THEME["bg"]).pack(anchor="w")
        preset_var = tk.StringVar(value=matched)
        combo = ttk.Combobox(win, textvariable=preset_var, values=names, state="readonly", width=56,
                             font=("Noto Serif CJK SC", 11))
        combo.pack(padx=10, pady=4, fill="x")

        ttk.Label(win, text="API Key:", background=THEME["bg"]).pack(anchor="w", padx=10)
        key_var = tk.StringVar(value=cfg.get("api_key", ""))
        ent = ttk.Entry(win, textvariable=key_var, width=70, show="*", font=("Noto Serif CJK SC", 11))
        ent.pack(padx=10, pady=4, fill="x")

        ttk.Label(win, text="Base URL(OpenAI 兼容):", background=THEME["bg"]).pack(anchor="w", padx=10)
        url_var = tk.StringVar(value=cur_url)
        ttk.Entry(win, textvariable=url_var, width=70, font=("Noto Serif CJK SC", 11)).pack(padx=10, pady=4, fill="x")

        ttk.Label(win, text="Model:", background=THEME["bg"]).pack(anchor="w", padx=10)
        model_var = tk.StringVar(value=cur_model)
        ttk.Entry(win, textvariable=model_var, width=70, font=("Noto Serif CJK SC", 11)).pack(padx=10, pady=4, fill="x")

        def on_preset(_evt=None):
            n = preset_var.get()
            if n == "自定义(手动填 URL/Model)":
                return
            u, m = self.PRESETS[n]
            url_var.set(u); model_var.set(m)
            save(silent=True)

        combo.bind("<<ComboboxSelected>>", on_preset)

        ttk.Label(win, text="注:DeepSeek/通义/GLM/Moonshot/MiniMax 都走 OpenAI 兼容接口,只要 Key + URL + Model 对得上。\n"
                            "若报 'unknown model',去厂商后台查实际可用模型名填入。",
                  background=THEME["bg"], foreground=THEME["muted"],
                  font=("Noto Serif CJK SC", 9), wraplength=540).pack(anchor="w", padx=10, pady=4)

        def save(silent=False):
            yi_expert.save_config({
                "provider": preset_var.get(),
                "api_key":  key_var.get().strip(),
                "base_url": url_var.get().strip() or "https://api.deepseek.com/v1",
                "model":    model_var.get().strip() or "deepseek-chat",
            })
            if not silent:
                messagebox.showinfo("已保存", f"配置已保存到:\n{yi_expert.CONFIG_FILE}", parent=win)
                win.destroy()

        bf = ttk.Frame(win, style="TFrame")
        bf.pack(pady=10)
        def show_key():
            ent.config(show="" if ent.cget("show") == "*" else "*")
        ttk.Button(bf, text="显示/隐藏 Key", command=show_key).pack(side="left", padx=4)
        ttk.Button(bf, text="保存", style="Accent.TButton", command=save).pack(side="left", padx=4)
        ttk.Button(bf, text="取消", command=win.destroy).pack(side="left", padx=4)

        ent.focus_set()


# ============================================================
# 自测 / 入口
# ============================================================
def self_test() -> bool:
    """不弹窗,验证 core + tk + YiApp 可实例化。"""
    print(f"  yi_core HEX: {len(core.HEX)} (expect 64)")
    assert len(core.HEX) == 64
    # 验一卦
    h = core.HEX[0]
    assert h[0] == 1 and h[1] == "乾"
    cast = core.cast("自测", seed=42)
    print(f"  sample cast: main={cast['main_num']} nuclear={cast['nuclear_num']} changed={cast.get('changed_num')}")
    # 模拟一次 ask,但不联网
    prompt = yi_expert.build_user_prompt("近期事业", cast)
    assert "主卦" in prompt
    # 弹窗 smoke test
    root = tk.Tk(); root.withdraw()
    app = YiApp(root)
    app._do_cast()
    app._clear_cast()
    root.destroy()
    print("  YiApp instance + _do_cast + _clear_cast OK")
    return True


def main():
    root = tk.Tk()
    app = YiApp(root)
    root.mainloop()


if __name__ == "__main__":
    import sys as _s
    if "--self-test" in _s.argv:
        print("[self-test]")
        ok = self_test()
        print("OK" if ok else "FAIL")
        _s.exit(0 if ok else 1)
    main()
