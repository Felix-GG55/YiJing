#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易经三钱法 - Tkinter GUI(Windows / macOS / Linux 通用)
依赖:Python 3.7+ 标准库(tkinter)。
启动:python yi_gui.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yi_core as core
import yi_expert

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class YiApp:
    def __init__(self, root):
        self.root = root
        root.title("易经三钱法")
        root.geometry("980x720")
        try:
            root.tk.call("tk", "scaling", 1.2)
        except Exception:
            pass

        self._build_menu()
        self._build_tabs()

        self.last_cast = None
        self.expert_full = ''
        self.expert_busy = False

    # ---------- 菜单 ----------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="起卦  Ctrl+N", command=lambda: self.notebook.select(0))
        filem.add_command(label="查看 64 卦  Ctrl+B", command=lambda: self.notebook.select(1))
        filem.add_command(label="查看日志  Ctrl+L", command=lambda: self.notebook.select(2))
        filem.add_command(label="AI 解卦  Ctrl+E", command=lambda: self.notebook.select(3))
        filem.add_separator()
        filem.add_command(label="退出  Ctrl+Q", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=filem)

        helpm = tk.Menu(menubar, tearoff=0)
        helpm.add_command(label="三钱法说明", command=self._show_help)
        helpm.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=helpm)
        self.root.config(menu=menubar)

        self.root.bind("<Control-n>", lambda e: self.notebook.select(0))
        self.root.bind("<Control-b>", lambda e: self.notebook.select(1))
        self.root.bind("<Control-l>", lambda e: self.notebook.select(2))
        self.root.bind("<Control-e>", lambda e: self.notebook.select(3))
        self.root.bind("<Control-q>", lambda e: self.root.quit())

    # ---------- 标签页 ----------
    def _build_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)

        self.tab_cast = ttk.Frame(self.notebook)
        self.tab_browse = ttk.Frame(self.notebook)
        self.tab_log = ttk.Frame(self.notebook)
        self.tab_expert = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cast, text="  起 卦  ")
        self.notebook.add(self.tab_browse, text="  64 卦  ")
        self.notebook.add(self.tab_log, text="  日 志  ")
        self.notebook.add(self.tab_expert, text="  AI解卦  ")

        self._build_cast_tab()
        self._build_browse_tab()
        self._build_log_tab()
        self._build_expert_tab()

    # ---------- 起卦 ----------
    def _build_cast_tab(self):
        top = ttk.Frame(self.tab_cast)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="问事:").pack(side="left")
        self.q_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.q_var, width=50)
        ent.pack(side="left", padx=6)
        ent.bind("<Return>", lambda e: self._do_cast())
        ttk.Button(top, text="起 卦", command=self._do_cast).pack(side="left", padx=4)
        ttk.Button(top, text="清 空", command=self._clear_cast).pack(side="left", padx=4)

        body = ttk.Frame(self.tab_cast)
        body.pack(fill="both", expand=True, padx=8, pady=4)

        # 左侧:画三个卦象
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 8))

        self.canvas_main = self._make_hex_canvas(left, "主卦")
        self.canvas_nuclear = self._make_hex_canvas(left, "互卦")
        self.canvas_changed = self._make_hex_canvas(left, "变卦")

        # 右侧:文本信息
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.cast_text = scrolledtext.ScrolledText(right, wrap="char", width=50, font=("Menlo", 11))
        self.cast_text.pack(fill="both", expand=True)

    def _make_hex_canvas(self, parent, title):
        f = ttk.LabelFrame(parent, text=title, padding=4)
        f.pack(fill="x", pady=4)
        c = tk.Canvas(f, width=160, height=140, bg="white", highlightthickness=1, highlightbackground="#888")
        c.pack()
        return c

    def _draw_hex(self, canvas, lines, title):
        canvas.delete("all")
        if not lines:
            canvas.create_text(80, 70, text="(无)", fill="#888", font=("Menlo", 11))
            return
        w = int(canvas["width"])
        h = int(canvas["height"])
        margin_x = 20
        line_w = w - 2 * margin_x
        line_h = 4
        gap = (h - 12) / 6
        for idx, ln in enumerate(lines):
            _, v, lbl = ln
            y = 8 + idx * gap
            x0, x1 = margin_x, margin_x + line_w
            if v == 1:
                # yang 阳
                canvas.create_rectangle(x0, y, x1, y + line_h, fill="black", outline="black")
            else:
                # yin 阴(中间断)
                seg = (line_w - 12) // 2
                canvas.create_rectangle(x0, y, x0 + seg, y + line_h, fill="black", outline="black")
                canvas.create_rectangle(x1 - seg, y, x1, y + line_h, fill="black", outline="black")
            if lbl in ("老阳", "老阴"):
                canvas.create_oval(w - 14, y - 6, w - 4, y + 10, outline="red", width=2)
                canvas.create_text(w - 9, y + 2, text="动", fill="red", font=("Menlo", 8))

    def _do_cast(self):
        q = self.q_var.get().strip()
        lines = core.cast_six_lines()
        main_bin = core.lines_to_binary(lines)
        main = core.binary_to_hex(main_bin)
        nuclear_bin = core.nuclear_hex(lines)
        nuclear = core.binary_to_hex(nuclear_bin)
        changed_bin = core.changed_binary(lines)
        changed = core.binary_to_hex(changed_bin)
        any_change = any(l[2] in ("老阴", "老阳") for l in lines)

        # 主卦画法:用真实爻
        self._draw_hex(self.canvas_main, lines, "主卦")

        # 互卦:从 lines 抽出 2,3,4 / 3,4,5 爻
        nuc_vals = [core.line_to_yinyang(l) for l in lines]
        nuc_lines = [(0, nuc_vals[5 - i], "互卦") for i in range(6)]
        # 互卦的 binary 顺序是 自下而上 = vals[2],vals[3],vals[4] (下卦 3,4,5) + vals[1],vals[2],vals[3] (上卦 2,3,4)
        # 索引 i=0 对应最下爻 = nuc_vals[2], i=5 对应最上爻 = nuc_vals[1]
        nuc_lines = [(0, nuc_vals[5 - i], "互卦") for i in range(6)]
        # 重新排列:nuc_lines[0] 是下卦最下爻 = nuc_vals[2] (即原卦第 3 爻)
        nuc_lines = [(0, nuc_vals[5 - i], "互卦") for i in range(6)]
        # 直接用 nuc_vals 重排:互卦六爻自下而上 = [nuc_vals[2], nuc_vals[3], nuc_vals[4], nuc_vals[1], nuc_vals[2], nuc_vals[3]]
        nuc_yy = [nuc_vals[2], nuc_vals[3], nuc_vals[4], nuc_vals[1], nuc_vals[2], nuc_vals[3]]
        nuc_lines = [(0, nuc_yy[5 - i], "互卦") for i in range(6)]
        self._draw_hex(self.canvas_nuclear, nuc_lines, "互卦")

        # 变卦
        chg_yy = [core.line_to_yinyang(l) for l in lines]
        chg_lines = []
        for i in range(6):
            lbl = "变爻" if lines[i][2] in ("老阴", "老阳") else "变卦"
            chg_lines.append((0, chg_yy[5 - i], lbl))
        self._draw_hex(self.canvas_changed, chg_lines if any_change else [], "变卦")

        # 文本信息
        from datetime import datetime
        text = []
        text.append(f"起卦:{datetime.now():%Y-%m-%d %H:%M:%S}")
        text.append(f"所问:{q or '(无)'}")
        text.append("")
        text.append(f"主卦 #{main[0]} {main[1]} {main[4]}  ({main[2]}上 {main[3]}下)")
        text.append(f"  卦辞:{main[5]}")
        text.append(f"  象传:{main[6]}")
        text.append("  爻辞:")
        for ln in main[7]:
            text.append(f"    {ln}")
        text.append("")
        text.append(f"互卦 #{nuclear[0]} {nuclear[1]} {nuclear_bin}")
        text.append(f"  卦辞:{nuclear[5]}")
        text.append(f"  象传:{nuclear[6]}")
        if any_change:
            text.append("")
            text.append(f"变卦 #{changed[0]} {changed[1]} {changed_bin}")
            text.append(f"  卦辞:{changed[5]}")
            text.append(f"  象传:{changed[6]}")
        else:
            text.append("")
            text.append("(无动爻)")

        self.cast_text.delete("1.0", "end")
        self.cast_text.insert("1.0", "\n".join(text))

        result = {
            "question": q,
            "lines": [(l[0], l[1], l[2]) for l in lines],
            "main_num": main[0],
            "nuclear_num": nuclear[0],
            "changed_num": changed[0] if any_change else None,
        }
        self.last_cast = result
        core.append_log(result)
        self._refresh_expert_context()

    def _clear_cast(self):
        self.q_var.set("")
        for c in (self.canvas_main, self.canvas_nuclear, self.canvas_changed):
            c.delete("all")
        self.cast_text.delete("1.0", "end")

    # ---------- 64 卦浏览 ----------
    def _build_browse_tab(self):
        top = ttk.Frame(self.tab_browse)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="卦序:").pack(side="left")
        self.hex_num = tk.StringVar(value="1")
        spin = ttk.Spinbox(top, from_=1, to=64, textvariable=self.hex_num, width=6)
        spin.pack(side="left", padx=4)
        ttk.Button(top, text="查看", command=self._show_hex).pack(side="left", padx=4)
        ttk.Label(top, text="  搜索:").pack(side="left")
        self.search_var = tk.StringVar()
        se = ttk.Entry(top, textvariable=self.search_var, width=30)
        se.pack(side="left", padx=4)
        se.bind("<Return>", lambda e: self._do_search())
        ttk.Button(top, text="搜索", command=self._do_search).pack(side="left")

        body = ttk.Frame(self.tab_browse)
        body.pack(fill="both", expand=True, padx=8, pady=4)

        self.listbox = tk.Listbox(body, width=20, font=("Menlo", 10))
        self.listbox.pack(side="left", fill="y", padx=(0, 6))
        self.listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        for h in core.HEX:
            self.listbox.insert("end", f"#{h[0]:>2} {h[1]} ({h[2]}{h[3]})")

        self.browse_text = scrolledtext.ScrolledText(body, wrap="char", font=("Menlo", 11))
        self.browse_text.pack(side="left", fill="both", expand=True)

        self._show_hex()

    def _on_listbox_select(self, _evt=None):
        sel = self.listbox.curselection()
        if sel:
            self.hex_num.set(str(sel[0] + 1))
            self._show_hex()

    def _show_hex(self):
        try:
            n = int(self.hex_num.get())
        except ValueError:
            return
        if n < 1 or n > 64:
            return
        h = core.get_hex(n)
        text = [f"#{h[0]} {h[1]}  上卦 {h[2]}  下卦 {h[3]}",
                f"卦象(自下而上):{h[4]}",
                "",
                f"卦辞:{h[5]}",
                f"象传:{h[6]}",
                "",
                "六爻辞:"]
        for ln in h[7]:
            text.append(f"  {ln}")
        self.browse_text.delete("1.0", "end")
        self.browse_text.insert("1.0", "\n".join(text))

    def _do_search(self):
        kw = self.search_var.get().strip()
        if not kw:
            return
        results = core.search_hex(kw)
        if not results:
            messagebox.showinfo("搜索", f"未找到包含 {kw} 的卦象")
            return
        self.browse_text.delete("1.0", "end")
        out = [f"搜索 {kw} 共 {len(results)} 个结果:", ""]
        for h in results:
            out.append(f"#{h[0]} {h[1]} (上{h[2]} 下{h[3]}) - {h[5]}")
            out.append("")
        self.browse_text.insert("1.0", "\n".join(out))

    # ---------- 日志 ----------
    def _build_log_tab(self):
        top = ttk.Frame(self.tab_log)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="刷新", command=self._load_log).pack(side="left", padx=4)
        ttk.Button(top, text="打开日志目录", command=self._open_log_dir).pack(side="left", padx=4)
        ttk.Button(top, text="清空日志", command=self._clear_log).pack(side="left", padx=4)

        self.log_text = scrolledtext.ScrolledText(self.tab_log, wrap="char", font=("Menlo", 10))
        self.log_text.pack(fill="both", expand=True, padx=8, pady=4)
        self._load_log()

    def _load_log(self):
        if core.LOG_FILE.exists():
            self.log_text.delete("1.0", "end")
            self.log_text.insert("1.0", core.LOG_FILE.read_text(encoding="utf-8"))
        else:
            self.log_text.delete("1.0", "end")
            self.log_text.insert("1.0", "(尚无日志)")

    def _open_log_dir(self):
        import subprocess, platform
        p = core.LOG_FILE.parent
        p.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(p)])
        elif platform.system() == "Windows":
            subprocess.Popen(["explorer", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])

    def _clear_log(self):
        if messagebox.askyesno("确认", "清空全部日志?"):
            core.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            core.LOG_FILE.write_text("# 易卦日志\n\n", encoding="utf-8")
            self._load_log()

    # ---------- 帮助 ----------
    def _show_help(self):
        msg = ("三钱法起卦\n\n"
               "1. 心中默念所问之事\n"
               "2. 取三枚铜钱(无字背则约定正面=3 反面=2)\n"
               "3. 掷六次,每次记下:\n"
               "   三个背(3+3+3=9)= 老阳(阳动变阴)\n"
               "   两背一字(3+3+2=8)= 少阴\n"
               "   一背二字(3+2+2=7)= 少阳\n"
               "   三个字(2+2+2=6)= 老阴(阴动变阳)\n"
               "4. 自下而上六爻成卦\n"
               "5. 程序自动生成:主卦 / 互卦 / 变卦\n\n"
               "互卦:取 2,3,4 爻为上,3,4,5 爻为下\n"
               "变卦:动爻阴阳互换\n"
               "无动爻则不变")
        messagebox.showinfo("三钱法说明", msg)

    def _show_about(self):
        messagebox.showinfo("关于",
            "易经三钱法 v1.0\n\n"
            "依据:王弼注 / 朱熹 周易本义(宋,公版)\n"
            "跨平台:Python 3.7+ / Tkinter\n"
            f"日志:{core.LOG_FILE}")


    # ---------- AI解卦 ----------
    def _build_expert_tab(self):
        top = ttk.Frame(self.tab_expert)
        top.pack(fill="x", padx=8, pady=8)
        self.expert_summary_var = tk.StringVar(value="(尚未起卦)")
        ttk.Label(top, text="本卦:", font=("", 10, "bold")).pack(side="left")
        ttk.Label(top, textvariable=self.expert_summary_var, foreground="#444").pack(side="left", padx=(4, 12))
        ttk.Label(top, text="额外说明(可选):").pack(side="left")
        self.expert_q_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.expert_q_var, width=30).pack(side="left", padx=4)

        btns = ttk.Frame(self.tab_expert)
        btns.pack(fill="x", padx=8, pady=(0, 6))
        self.btn_ask = ttk.Button(btns, text="请道士解卦", command=self._ask_expert)
        self.btn_ask.pack(side="left", padx=2)
        ttk.Button(btns, text="设置 API", command=self._show_expert_config).pack(side="left", padx=2)
        ttk.Button(btns, text="复制结果", command=self._copy_expert).pack(side="left", padx=2)
        ttk.Button(btns, text="保存到日志", command=self._save_expert_to_log).pack(side="left", padx=2)
        ttk.Button(btns, text="清空", command=self._clear_expert).pack(side="left", padx=2)

        body = ttk.Frame(self.tab_expert)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.expert_text = tk.Text(body, wrap="word", padx=8, pady=8)
        self.expert_text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.expert_text.yview)
        sb.pack(side="right", fill="y")
        self.expert_text.config(yscrollcommand=sb.set, state="disabled")
        self.expert_text.tag_configure("header", font=("Helvetica", 12, "bold"), foreground="#8B4513", spacing1=6, spacing3=2)
        self.expert_text.tag_configure("meta", foreground="#666")
        self.expert_text.tag_configure("err", foreground="#c00")

    def _refresh_expert_context(self):
        if not self.last_cast:
            self.expert_summary_var.set("(尚未起卦)")
            return
        r = self.last_cast
        main = core.HEX_BY_NUM.get(r["main_num"])
        moving = [i for i, l in enumerate(r["lines"], 1) if l[2] in ("老阴", "老阳")]
        s = f"#{main[0]} {main[1]}"
        if moving:
            s += f"  动爻:{','.join(map(str, moving))}爻"
        else:
            s += "  无动爻"
        s += f"   问:{r['question'] or '(无)'}"
        self.expert_summary_var.set(s)

    def _append_expert(self, text, tag=None):
        self.expert_text.config(state="normal")
        if tag:
            self.expert_text.insert("end", text, tag)
        else:
            self.expert_text.insert("end", text)
        self.expert_text.see("end")
        self.expert_text.config(state="disabled")

    def _clear_expert(self):
        self.expert_text.config(state="normal")
        self.expert_text.delete("1.0", "end")
        self.expert_text.config(state="disabled")
        self.expert_full = ""

    def _ask_expert(self):
        if self.expert_busy:
            messagebox.showinfo("提示", "道士还在解卦,请稍候...")
            return
        if not self.last_cast:
            messagebox.showwarning("提示", "请先在 '起卦' 标签起一卦。")
            self.notebook.select(0)
            return
        cfg = yi_expert.load_config()
        if not cfg.get("api_key"):
            self._show_expert_config()
            cfg = yi_expert.load_config()
            if not cfg.get("api_key"):
                return
        self._clear_expert()
        self._append_expert("道士正在解卦,请稍候...\n\n", "meta")
        self.expert_busy = True
        self.btn_ask.config(state="disabled", text="解卦中...")
        extra = self.expert_q_var.get().strip()
        q = self.last_cast["question"] or ""
        if extra:
            q = (q + " | " + extra) if q else extra
        cast_result = self.last_cast
        root = self.root

        def on_token(tok):
            root.after(0, lambda: self._append_expert(tok))

        def on_done(full):
            def _():
                self.expert_full = full
                self.expert_busy = False
                self.btn_ask.config(state="normal", text="请道士解卦")
                self._highlight_headers()
            root.after(0, _)

        def on_error(err):
            def _():
                self._append_expert("\n\n[出错] " + err + "\n", "err")
                self.expert_busy = False
                self.btn_ask.config(state="normal", text="请道士解卦")
            root.after(0, _)

        yi_expert.ask_stream(q, cast_result, on_token, on_done, on_error)

    def _highlight_headers(self):
        text = self.expert_text.get("1.0", "end")
        if "**" not in text:
            return
        self.expert_text.config(state="normal")
        self.expert_text.delete("1.0", "end")
        import re
        parts = re.split(r"(\*\*[^*]+\*\*)", text)
        for p in parts:
            if p.startswith("**") and p.endswith("**") and len(p) > 4:
                self.expert_text.insert("end", p[2:-2] + "\n", "header")
            else:
                self.expert_text.insert("end", p)
        self.expert_text.config(state="disabled")

    def _copy_expert(self):
        if not self.expert_full:
            messagebox.showinfo("提示", "尚无解卦结果。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.expert_full)
        messagebox.showinfo("已复制", "解卦文本已复制到剪贴板。")

    def _save_expert_to_log(self):
        if not self.expert_full or not self.last_cast:
            messagebox.showinfo("提示", "尚无解卦结果。")
            return
        try:
            from datetime import datetime
            with open(core.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n\n## AI解卦 {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
                f.write(self.expert_full + "\n")
            messagebox.showinfo("已保存", f"解卦文本已追加到日志:\n{core.LOG_FILE}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _show_expert_config(self):
        win = tk.Toplevel(self.root)
        win.title("设置 AI 解卦 API")
        win.geometry("560x420")
        win.transient(self.root)
        win.grab_set()

        # 预设表
        PRESETS = {
            "DeepSeek(默认,中文好,便宜)":  ("https://api.deepseek.com/v1",        "deepseek-chat"),
            "OpenAI":                         ("https://api.openai.com/v1",          "gpt-4o-mini"),
            "通义千问 Qwen":                  ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-turbo"),
            "智谱 GLM":                       ("https://open.bigmodel.cn/api/paas/v4","glm-4-flash"),
            "月之暗面 Moonshot":              ("https://api.moonshot.cn/v1",         "moonshot-v1-8k"),
            "MiniMax / MiniMax":              ("https://api.MiniMax.chat/v1",        "MiniMax-Text-01"),
            "自定义(手动填 URL/Model)":      ("",                                  ""),
        }
        names = list(PRESETS.keys())

        cfg = yi_expert.load_config()
        url_var = tk.StringVar(value=cfg.get("base_url", "https://api.deepseek.com/v1"))
        model_var = tk.StringVar(value=cfg.get("model", "deepseek-chat"))

        ttk.Label(win, text="提供商预设(选完自动填 URL/Model,可再改):", padding=(8, 8, 0, 0)).pack(anchor="w")
        preset_var = tk.StringVar(value=names[0])
        # 反查当前 cfg 匹配哪个预设
        for n, (u, m) in PRESETS.items():
            if u == url_var.get() and m == model_var.get():
                preset_var.set(n)
                break
        preset_combo = ttk.Combobox(win, textvariable=preset_var, values=names, state="readonly", width=50)
        preset_combo.pack(padx=8, pady=4, fill="x")

        ttk.Label(win, text="API Key:", padding=(8, 8, 0, 0)).pack(anchor="w")
        key_var = tk.StringVar(value=cfg.get("api_key", ""))
        ent = ttk.Entry(win, textvariable=key_var, width=70, show="*")
        ent.pack(padx=8, pady=4, fill="x")

        ttk.Label(win, text="Base URL(OpenAI 兼容):", padding=(8, 8, 0, 0)).pack(anchor="w")
        url_entry = ttk.Entry(win, textvariable=url_var, width=70)
        url_entry.pack(padx=8, pady=4, fill="x")

        ttk.Label(win, text="Model:", padding=(8, 8, 0, 0)).pack(anchor="w")
        model_entry = ttk.Entry(win, textvariable=model_var, width=70)
        model_entry.pack(padx=8, pady=4, fill="x")

        def on_preset(_evt=None):
            n = preset_var.get()
            if n == "自定义(手动填 URL/Model)":
                return
            u, m = PRESETS[n]
            url_var.set(u)
            model_var.set(m)
        preset_combo.bind("<<ComboboxSelected>>", on_preset)

        ttk.Label(win, text="注:DeepSeek/通义/GLM/Moonshot/MiniMax 都走 OpenAI 兼容接口,只要 Key + URL + Model 对得上。",
                  foreground="#666", padding=(8, 8, 0, 4), wraplength=520).pack(anchor="w")

        def save():
            yi_expert.save_config({
                "provider": preset_var.get(),
                "api_key": key_var.get().strip(),
                "base_url": url_var.get().strip() or "https://api.deepseek.com/v1",
                "model": model_var.get().strip() or "deepseek-chat",
            })
            messagebox.showinfo("已保存", "配置已保存到:\n" + str(yi_expert.CONFIG_FILE), parent=win)
            win.destroy()

        def show_key():
            ent.config(show="" if ent.cget("show") == "*" else "*")

        bf = ttk.Frame(win)
        bf.pack(pady=12)
        ttk.Button(bf, text="显示/隐藏 Key", command=show_key).pack(side="left", padx=4)
        ttk.Button(bf, text="保存", command=save).pack(side="left", padx=4)
        ttk.Button(bf, text="取消", command=win.destroy).pack(side="left", padx=4)

        ent.focus_set()


def self_test() -> bool:
    """自测:验证 yi_core 数据 + YiApp 可实例化,不弹窗。"""
    print(f"  yi_core HEX: {len(core.HEX)} (expect 64)")
    assert len(core.HEX) == 64

    r = core.cast("自测", seed=42)
    print(f"  cast: main=#{r['main_num']} nuclear=#{r['nuclear_num']} changed=#{r['changed_num']}")

    for kw in ["龙", "水", "贞"]:
        hits = core.search_hex(kw)
        print(f"  search {kw}: {len(hits)} hits")

    print(f"  YiApp class defined OK")

    try:
        root = tk.Tk()
        root.withdraw()
        app = YiApp(root)
        print(f"  YiApp instantiated OK (3 tabs, 64 hexagrams loaded)")
        root.destroy()
    except Exception as e:
        print(f"  YiApp instantiation failed: {e}")
        return False
    return True


def main():
    root = tk.Tk()
    YiApp(root)
    root.mainloop()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(0 if self_test() else 1)
    main()
