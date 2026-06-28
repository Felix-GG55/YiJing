# 易经三钱法 — Windows .exe 自动构建

这个仓库用 GitHub Actions 在 **Windows runner** 上自动构建 `YiJing.exe`,
双击即跑,无需安装 Python。

## 一键发布流程 (macOS 终端)

### 1. 在 GitHub 创建空仓库

打开 https://github.com/new,Repository name 填 `yijing-release`,
选 Public(公开仓库 Actions 免费),**不要**勾 Add README/.gitignore/license,
点 Create repository。

### 2. 推送代码

把下面的命令粘到终端(`YOUR_USERNAME` 换成你的 GitHub 用户名):

```bash
cd ~/Documents/qi/yijing-release
git init -b main
git add .
git -c user.name="codex" -c user.email="codex@local" commit -m "init: yijing windows exe builder"
git remote add origin https://github.com/YOUR_USERNAME/yijing-release.git
git push -u origin main
```

### 3. 触发构建

#### 方式 A:网页手动触发(简单)

打开 https://github.com/YOUR_USERNAME/yijing-release/actions,
点左侧 `build-windows-exe` → 右侧 `Run workflow` → 绿色按钮。

等 1-3 分钟,完成后:

- 点进 run → 底部 Artifacts → 下载 `YiJing-windows-exe.zip`
- 解压得到 `YiJing.exe`

#### 方式 B:打 tag 自动发 Release

```bash
git tag v1.0
git push origin v1.0
```

会自动创建 GitHub Release 并附 `YiJing.exe`,任何人都能下载。

## 文件清单

| 文件 | 用途 |
|---|---|
| `yi_core.py` | 64 卦数据 + 三钱法逻辑(库) |
| `yi_gui.py` | Tkinter GUI 入口 |
| `.github/workflows/build-windows.yml` | GitHub Actions 构建脚本 |
| `README.md` | 本文件 |

## 数据来源

公版《周易本义》(宋·朱熹),王弼注。

## 许可

公版古籍,代码 MIT。
