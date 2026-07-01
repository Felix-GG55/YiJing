#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键生成 v4.1 资源:
  assets/icon.png      256x256 八卦 PNG(用于窗口 iconphoto)
  assets/icon.ico      多尺寸 ICO(用于 Windows EXE 图标)
  assets/sounds/mantra.wav  120s 八大神咒背景音(drone + 木鱼/磬)

运行: python3 gen_assets.py
"""
import math
import os
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SOUNDS = ASSETS / "sounds"
ASSETS.mkdir(exist_ok=True)
SOUNDS.mkdir(exist_ok=True)


# ============================================================
# 八大神咒 → 频率 / 命名
# ============================================================
# 频率选自五声音阶 + 八度,适合东方冥想氛围
MANTRA_FREQS = [
    ("01_净心神咒",  220.00, "宫"),  # A3
    ("02_净口神咒",  246.94, "商"),  # B3
    ("03_净身神咒",  293.66, "角"),  # D4
    ("04_安土地神咒", 329.63, "徵"),  # E4
    ("05_净天地神咒", 369.99, "羽"),  # F#4
    ("06_金光神咒",   440.00, "宫"),  # A4
    ("07_坐忘咒",     493.88, "商"),  # B4
    ("08_祝香神咒",   587.33, "角"),  # D5
]


# ============================================================
# 八大神咒 WAV(120s,8 段各 15s)
# ============================================================
def gen_mantra_wav(path: Path, total_seconds: int = 120, sr: int = 11025):
    """8 段 drone + bell accents,每段 15s,频率随 MANTRA_FREQS 渐变。"""
    section_seconds = total_seconds / len(MANTRA_FREQS)
    samples_total = int(sr * total_seconds)
    samples = [0] * samples_total

    for sec_idx, (name, base_f, scale) in enumerate(MANTRA_FREQS):
        t0 = int(sec_idx * section_seconds * sr)
        t1 = int((sec_idx + 1) * section_seconds * sr)
        bell_f = base_f * 4
        for i in range(t0, t1):
            t = (i - t0) / sr
            env = math.exp(-t / (section_seconds * 0.6))
            drone = (
                math.sin(2 * math.pi * base_f * t) * 0.30
                + math.sin(2 * math.pi * base_f * 2 * t) * 0.12
                + math.sin(2 * math.pi * base_f * 3 * t) * 0.06
            ) * env
            bell_period = 3.75
            bell_phase = (t % bell_period) / bell_period
            bell = math.sin(2 * math.pi * bell_f * t) * 0.55 * math.exp(-bell_phase * 9)
            fade = min(1.0, t / 0.8, (section_seconds - t) / 0.8)
            samples[i] = int(max(-32767, min(32767, (drone + bell) * 13000 * fade)))

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        chunk = b"".join(struct.pack("<h", s) for s in samples)
        w.writeframes(chunk)
    return path


# ============================================================
# 八卦图标 PNG(256×256)
# ============================================================
def _pick_font(size: int):
    from PIL import ImageFont
    cands = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Songti.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/YuMincho.ttc",
    ]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def gen_icon_png(path: Path, size: int = 256):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    r_outer = size / 2 - 4
    r_inner = r_outer * 0.62

    d.ellipse(
        [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
        fill=(178, 34, 34, 255),
        outline=(184, 134, 11, 255),
        width=3,
    )
    d.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        fill=(26, 26, 26, 255),
    )
    r_yang = r_inner * 0.95
    d.pieslice(
        [cx - r_yang, cy - r_yang, cx + r_yang, cy + r_yang],
        -90, 90,
        fill=(245, 233, 208, 255),
    )
    dot_r = r_inner * 0.18
    d.ellipse(
        [cx - dot_r, cy - r_inner * 0.5 - dot_r, cx + dot_r, cy - r_inner * 0.5 + dot_r],
        fill=(26, 26, 26, 255),
    )
    d.ellipse(
        [cx - dot_r, cy + r_inner * 0.5 - dot_r, cx + dot_r, cy + r_inner * 0.5 + dot_r],
        fill=(245, 233, 208, 255),
    )

    glyphs = ["☰", "☷", "☱", "☴", "☵", "☶", "☲", "☳"]
    font = _pick_font(int(size / 6))
    r_ring = r_outer * 0.78
    for i, g in enumerate(glyphs):
        ang = math.radians(-90 + i * 45)
        x = cx + r_ring * math.cos(ang)
        y = cy + r_ring * math.sin(ang)
        bbox = d.textbbox((0, 0), g, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text((x - tw / 2 - bbox[0], y - th / 2 - bbox[1]),
               g, font=font, fill=(245, 233, 208, 255))

    img.save(str(path), "PNG")
    return img


def gen_icon_ico(png_path: Path, ico_path: Path):
    from PIL import Image
    src = Image.open(str(png_path)).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    src.save(str(ico_path), format="ICO", sizes=sizes)


if __name__ == "__main__":
    print(f"=== 生成资源到 {ASSETS} ===")
    print("[1/3] icon.png (256x256)")
    img = gen_icon_png(ASSETS / "icon.png", 256)
    print(f"      saved: {ASSETS / 'icon.png'}  ({img.size})")

    print("[2/3] icon.ico (multi-size)")
    gen_icon_ico(ASSETS / "icon.png", ASSETS / "icon.ico")
    print(f"      saved: {ASSETS / 'icon.ico'}")

    print(f"[3/3] mantra.wav (120s, 8 mantras)")
    p = gen_mantra_wav(SOUNDS / "mantra.wav")
    print(f"      saved: {p}  ({p.stat().st_size:,} bytes)")

    print("\n全部资源生成完毕。")
    print(f"  PNG  : {ASSETS / 'icon.png'}")
    print(f"  ICO  : {ASSETS / 'icon.ico'}")
    print(f"  WAV  : {SOUNDS / 'mantra.wav'}")
