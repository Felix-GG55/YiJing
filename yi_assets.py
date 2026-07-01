#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v4.1 资源与效果模块:
  - ICON_PNG_PATH / MANTRA_WAV_PATH  资源路径
  - play_mantra() / stop_mantra()    跨平台循环播放 mantra.wav
  - BaguaLoader                       八卦盘加载动画(8 卦符循环高亮)
  - show_splash_incense()             启动三根香 + 烟封面

颜色与 yi_gui.THEME 一致,独立模块避免循环 import。
"""
import math
import random
import subprocess
import sys
import tkinter as tk
from pathlib import Path

# 资源路径(支持 PyInstaller frozen)
def _bundle_dir():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

ICON_PNG_PATH   = _bundle_dir() / "assets" / "icon.png"
MANTRA_WAV_PATH = _bundle_dir() / "assets" / "sounds" / "mantra.wav"

# 颜色(与 yi_gui.THEME 同步)
BG     = "#F5E9D0"   # 米黄
INK    = "#1A1A1A"   # 玄墨
ACCENT = "#B22222"   # 朱红
GOLD   = "#B8860B"   # 古金
MUTED  = "#888888"   # 灰
RICE   = "#FFF8E7"   # 附加引用底色
WOOD   = "#8B4513"   # 香木色
DARK_WOOD = "#5C3317"


# ============================================================
# 跨平台 mantra 循环播放
# ============================================================
def play_mantra():
    """循环播放 mantra.wav(尽力而为)。"""
    if not MANTRA_WAV_PATH.exists():
        return
    wav = str(MANTRA_WAV_PATH)
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound(
                wav,
                winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC,
            )
        elif sys.platform == "darwin":
            subprocess.Popen(
                ["afplay", wav],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            for cmd in (["paplay", "--loop"], ["mpg123", "--loop", "--quiet"], ["aplay", "--loop"]):
                try:
                    subprocess.Popen(cmd + [wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except FileNotFoundError:
                    continue
    except Exception:
        pass


def stop_mantra():
    """停止循环播放。"""
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound(None, 0)
    except Exception:
        pass


# ============================================================
# 八卦盘加载动画
# ============================================================
class BaguaLoader(tk.Frame):
    """在父容器里画一个循环高亮的八卦盘。"""

    GLYPHS = ["\u2630", "\u2631", "\u2632", "\u2633", "\u2634", "\u2635", "\u2636", "\u2637"]
    NAMES  = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]

    def __init__(self, master, size: int = 220, on_done=None, **kwargs):
        super().__init__(master, bg=BG, **kwargs)
        self._on_done = on_done
        self._active = True
        self._highlight = 0

        self.canvas = tk.Canvas(
            self, width=size, height=size, bg=BG, highlightthickness=0,
        )
        self.canvas.pack(pady=(6, 2))
        self.size = size
        self._glyph_ids = []
        self._draw_static()

        self.lbl_name = tk.Label(
            self, text="\u00b7  起  卦  \u00b7",
            font=("Noto Serif CJK SC", 14, "bold"),
            bg=BG, fg=ACCENT,
        )
        self.lbl_name.pack()
        self.lbl_hint = tk.Label(
            self, text="道生一,一生二,二生三,三生万物",
            font=("Noto Serif CJK SC", 10),
            bg=BG, fg=MUTED,
        )
        self.lbl_hint.pack()

        self._animate()

    def _draw_static(self):
        s = self.size
        cx, cy = s / 2, s / 2
        r_outer = s / 2 - 8
        r_inner = r_outer * 0.32
        self.canvas.create_oval(
            cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
            fill=ACCENT, outline=GOLD, width=2,
        )
        self.canvas.create_oval(
            cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
            fill=INK, outline="",
        )
        r_ring = r_outer * 0.70
        for i, g in enumerate(self.GLYPHS):
            ang = math.radians(-90 + i * 45)
            x = cx + r_ring * math.cos(ang)
            y = cy + r_ring * math.sin(ang)
            tid = self.canvas.create_text(
                x, y, text=g,
                font=("Noto Serif CJK SC", 16),
                fill=MUTED,
            )
            self._glyph_ids.append(tid)

    def _animate(self):
        if not self._active:
            return
        for i, tid in enumerate(self._glyph_ids):
            if i == self._highlight:
                self.canvas.itemconfig(tid, fill="#FFFFFF", font=("Noto Serif CJK SC", 22, "bold"))
            else:
                self.canvas.itemconfig(tid, fill=MUTED, font=("Noto Serif CJK SC", 16))
        self.lbl_name.configure(text=f"\u00b7  {self.NAMES[self._highlight]} 卦  \u00b7")
        self._highlight = (self._highlight + 1) % 8
        self.after(140, self._animate)

    def stop(self):
        self._active = False
        if self._on_done is not None:
            try:
                self._on_done()
            except Exception:
                pass


# ============================================================
# 启动封面:三根香 + 烟
# ============================================================
def show_splash_incense(root, on_close, duration_ms: int = 3000):
    """在 root 上叠无边框封面,三柱清香 + 升烟动画,持续 duration_ms 后回调。"""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg=INK)
    splash.attributes("-topmost", True)

    w, h = 520, 380
    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    canvas = tk.Canvas(splash, width=w, height=h, bg=INK, highlightthickness=0)
    canvas.pack()

    canvas.create_text(
        w // 2, 56, text="\u7384  \u5999  \u6613  \u7ecf",
        font=("Noto Serif CJK SC", 30, "bold"),
        fill=GOLD,
    )
    canvas.create_text(
        w // 2, 96, text="\u4e09\u67f1\u6e05\u9999 \u00b7 \u656c\u7956\u5e08",
        font=("Noto Serif CJK SC", 14),
        fill=BG,
    )

    stick_x = [w // 2 - 90, w // 2, w // 2 + 90]
    stick_top = h - 80
    stick_height = 130
    for x in stick_x:
        canvas.create_rectangle(
            x - 4, stick_top, x + 4, stick_top + stick_height,
            fill=WOOD, outline=DARK_WOOD,
        )
        canvas.create_oval(
            x - 9, stick_top - 9, x + 9, stick_top + 5,
            fill="#FF8C42", outline="#FFD27A", width=2,
        )
        canvas.create_oval(
            x - 4, stick_top - 4, x + 4, stick_top + 1,
            fill="#FFEB3B", outline="",
        )

    smoke = []
    rng = random.Random(7)

    def update():
        for x in stick_x:
            if rng.random() < 0.35:
                sway = rng.uniform(0, math.tau)
                pid = canvas.create_oval(
                    x - 2, stick_top - 4, x + 2, stick_top - 1,
                    fill="#888888", outline="",
                )
                smoke.append([pid, x, 0, sway])
        alive = []
        for s in smoke:
            s[2] += 1
            age = s[2]
            dx = math.sin(age * 0.12 + s[3]) * 0.7
            canvas.move(s[0], dx, -1.6)
            if age < 25:
                canvas.itemconfig(s[0], fill="#999999")
            elif age < 50:
                canvas.itemconfig(s[0], fill="#666666")
            elif age < 75:
                canvas.itemconfig(s[0], fill="#444444")
            else:
                canvas.itemconfig(s[0], fill="#333333")
            if age < 110:
                alive.append(s)
            else:
                canvas.delete(s[0])
        smoke[:] = alive
        canvas.after(50, update)

    canvas.create_text(
        w // 2, h - 32,
        text="\u9053\u6559\u7ecf\u5178 \u00b7 \u5468\u6613\u6b63\u4e49 \u00b7 \u9053\u5fb7\u771f\u7ecf",
        font=("Noto Serif CJK SC", 10),
        fill="#888888",
    )
    canvas.create_text(
        w // 2, h - 14,
        text="\u2014  \u9053 \u6cd5 \u81ea \u7136  \u2014",
        font=("Noto Serif CJK SC", 11, "italic"),
        fill=GOLD,
    )

    update()

    def _close():
        try:
            splash.destroy()
        except Exception:
            pass
        on_close()

    splash.after(duration_ms, _close)
    return splash
