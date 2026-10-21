# WhalePet 🐋

一个 Windows 桌宠，鲸鱼娘形象(暂未实现，目前暂无素材，用其他形象代替）。基于 PySide6 构建，支持 60fps 帧动画、随机语音、自动散步、开机自启。

> 本项目完全由 AI 辅助开发，如有 bug 欢迎提 Issue。

---

## ✨ 功能特性

- **透明置顶桌宠**：无边框、不占任务栏、贴底站立，可水平拖动，纵向位置可调并持久化
- **60fps 帧动画**：支持 GIF / WebM 导入，自动缩放到 480px 并抽帧到 60fps，保证流畅与高清
- **动作系统**：idle / click / walk 三种动作，左右朝向自动镜像，随机翻面
- **随机语音**：闲置触发（5 分钟–1 小时可调）、点击触发、15 分钟无交互特殊语音、22:30 熬夜特殊语音，支持中日双语种，不连续重复
- **自动散步**：桌宠会自己沿着屏幕底部走动，不出屏，方向与朝向一致
- **完整设置面板**：语音、行为、外观、系统四页，深浅色跟随 Windows 10/11 系统主题
- **开机自启**：写入注册表，绿色版路径移动后自动修正
- **素材全开放**：动画、语音、配置均可自行替换

---

## 📥 下载安装

前往 [Releases](https://github.com/BLUE-lnfg/whalepet/releases) 下载最新的 `Setup_WhalePet_vx.x.x.exe`，双击安装。

**系统要求**：Windows 10 / 11（64 位），无需安装 Python 或任何运行库。

安装位置：`%LOCALAPPDATA%\Programs\WhalePet\`（无需管理员权限）

---

## 🎨 自定义素材

安装后进入程序目录：

```
%LOCALAPPDATA%\Programs\WhalePet\profiles\default\assets\
```

| 目录 | 放什么 | 格式 |
|---|---|---|
| `actions\idle\` | 待机动画 | `.gif` / `.webm`，单文件 |
| `actions\click\` | 点击动画 | 同上 |
| `actions\walk\` | 散步动画 | 同上 |
| `voice\zh-CN\` | 中文闲置语音 | `.wav`（PCM 16-bit） |
| `voice\zh-CN\click\` | 中文点击语音 | `.wav` |
| `voice\zh-CN\special\no_interaction\` | 15 分钟无交互语音 | `.wav` |
| `voice\zh-CN\special\late_night\` | 熬夜特殊语音 | `.wav` |
| `voice\ja-JP\` | 日文语音（结构同上） | `.wav` |

**替换动画后需要重新导入**（在源码目录执行）：

```powershell
python tools/import_assets.py
```

**替换语音后直接重启程序即可**，无需额外操作。

---

## 🛠 开发

### 环境要求

- Python 3.11+
- Windows 10 / 11

### 快速开始

```powershell
git clone https://github.com/BLUE-lnfg/whalepet.git
cd whalepet
conda create -n whalepet python=3.11 -y
conda activate whalepet
python -m pip install PySide6 av pillow
python main.py
```

### 项目结构

```
whalepet/
├── main.py                 # 入口
├── app/
│   ├── animation/          # 帧播放器、状态机
│   ├── assets/             # 素材导入、加载
│   ├── behavior/           # 语音、散步等行为调度
│   ├── config/             # 配置管理与迁移
│   ├── services/           # 音频、主题、托盘、自启
│   └── ui/                 # 桌宠窗口、设置面板
├── profiles/default/       # 素材与配置方案
│   ├── assets/             # 用户可编辑的源素材
│   └── .cache/             # 导入后生成的帧序列（可重建）
├── tools/                  # 开发工具与测试脚本
├── WhalePet.spec           # PyInstaller 配置
└── installer.iss           # Inno Setup 安装包配置
```

### 技术栈

| 组件 | 用途 |
|---|---|
| PySide6 | GUI、动画绘制、多媒体播放 |
| PyAV | WebM 解码 |
| Pillow | GIF 解码、图像缩放 |
| PyInstaller | 打包成独立 exe |
| Inno Setup | 制作安装程序 |

---

## 📦 打包发布

```powershell
# 1. 打包成独立文件夹
pyinstaller WhalePet.spec --clean

# 2. 用 Inno Setup 6 打开 installer.iss，按 Ctrl+F9 编译
# 产物位于 installer_output\Setup_WhalePet_vx.x.x.exe
```

---

## ⚠️ 素材版权声明

本项目**代码部分**采用 MIT 协议开源。

**角色形象与语音素材**（当前使用的克莱门莎形象与语音）**版权归鹰角网络（Hypergryph）与《明日方舟》所有**，仅作为**个人学习与桌宠演示**使用，**不得用于任何商业用途**。

如果你想在公开场合分发本桌宠，请自行替换 `profiles/default/assets/` 下的素材为你有权使用的资源。仓库仅提供代码框架与素材替换机制。

---

## 💬 作者的话

作者是一个学生，平时喜欢折腾些小工具。找了一圈都没找到**高清、高帧率、又能独立于 DSH 运行**的大肥鱼桌宠，于是决定自己写一个。

由于目前手头缺乏原创素材，暂时用《明日方舟》的角色**克莱门莎**代替，语音与角色形象均来自游戏。等以后有合适的原创形象，会考虑替换。

**整个项目的代码开发过程完全由 AI 完成**，作者主要负责需求描述、方向决策和测试验收。因此，如果使用中遇到任何 bug 或不符合预期的地方，非常欢迎提 [Issue](https://github.com/BLUE-lnfg/whalepet/issues)，会尽快修复。

如果这个项目对你有帮助，欢迎点个 ⭐ Star。

---

## 📄 License

代码部分：[MIT License](LICENSE)

素材部分：见上方「素材版权声明」。