# 玄妙易经 · Web 版 (v4.2)

**单 HTML 文件**,双击 `index.html` 即可在浏览器打开,**不需要 Python 服务器**。

## 文件

- `index.html` — **唯一需要打开的文件** (56KB,所有数据 + 算法 + UI 全内联)
- `README.md` — 本文件

## 怎么用

1. **起卦**:点 顶栏 `起卦` 或右下角红色圆按钮
2. **输入所问**:顶栏输入框可填"近期事业/财运/..."(可空)
3. **看三卦**:本卦 / 互卦 / 变卦 并列显示,带 SVG 六爻(老阴/老阳带 × 标)
4. **问 AI**:点 `问道士` → 弹出设置 → 选厂商预设 + 填 API Key → 保存 → 重试

## 支持的 AI 厂商 (OpenAI 兼容 fetch)

- DeepSeek(默认,中文好/便宜)
- OpenAI (gpt-4o-mini)
- 通义千问 Qwen
- 智谱 GLM
- 月之暗面 Moonshot
- MiniMax / MiniMax (MiniMax-Text-01)
- 自定义 URL + Model

API Key 保存在浏览器 `localStorage`,不会上传到任何地方。

## 浏览器要求

- 任意现代浏览器(Chrome / Edge / Firefox / Safari)
- 支持 `fetch` 流式响应(几乎所有现代浏览器)
- 没有 CORS 限制(API 调用由浏览器直接发到厂商)

## 数据来源

- 文王卦序 64 卦 + 8 卦符(从 `../yi_core.py` 自动生成,内联在 HTML 里)
- 卦辞 / 象传 / 爻辞 全部来自《周易》原文
- 卦象显示按传统:`—` 阳爻,`— —` 阴爻,`— × —` 老阴/老阳 (动爻)

## 已知差异 (相对桌面版)

- 没有八卦盘 loader 动画(浏览器 SVG 无 alpha 动画等效替代)
- 没有音频背景音
- 没有 PDF 典籍侧栏(用其他 PDF 阅读器代替)
- 没有启动封面(三根香)

## 怎么重新生成数据

```bash
# 重新从 Python 核心生成数据(脚本:tools/export_web_data.py)
python3 tools/export_web_data.py
```
