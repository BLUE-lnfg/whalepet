# WhalePet 🐋

一个基于 PySide6 构建的 Windows 高清桌宠，支持多角色管理、动态配置与 60fps 丝滑帧动画。

> **当前版本：V0.9.0 (Pre-release)**
> 距离 V1.0 正式版仅剩“角色素材完善与最终打包”。由于开发者本地环境存在严重的底层 DLL 冲突，本版本暂不提供开箱即用的 exe 安装包，仅提供完整源码供开发者自行编译。

---

## ✨ 核心特性

- **多角色系统**：内置 `default`（圣聆初雪）与 `klms-test`（克莱门莎）两套形象，支持在设置面板中**瞬间热切换**，无需重启。
- **高性能动画引擎**：支持 WebM / GIF 格式，自动转码为 480px / 60fps 帧序列，支持左右镜像翻转，智能 LRU 缓存。
- **动态行为调度**：
  - 自动散步（不出屏、方向与朝向一致）
  - 随机朝向翻转（鼠标交互与随机逻辑分离）
  - 备用待机动画轮换（若无素材则自动跳过，不报错）
- **沉浸式语音系统**：闲置触发、点击触发、15 分钟无交互特殊语音、22:30 熬夜语音。支持中日双语，不连续重复。
- **现代设置面板**：无边框 Win11 风格，深浅色跟随系统。包含语音、行为、外观、系统、日志等页面，修改设置**即刻生效**。
- **日志与自启**：内置日志监控面板，实时抓取终端输出；支持注册表开机自启。

---

## 📁 素材与角色结构

游戏内的动图、语音均由用户自由替换。在项目根目录的 `profiles/` 下，每一个文件夹代表一个独立角色：

```text
profiles/
├── default/              # 角色 1 (当前为圣聆初雪)
│   ├── profile.json      # 元数据（名称、作者等）
│   └── assets/
│       ├── actions/      # 放动图（idle, click, walk, idle_alt1 等）
│       └── voice/        # 放语音（zh-CN, ja-JP）
└── klms-test/            # 角色 2 (当前为克莱门莎)
```

> **添加新素材**：在对应的 `actions/` 或 `voice/` 目录下放入文件后，运行 `python tools/import_assets.py` 自动生成缓存即可。

---

## 🛠 开发与编译指南

**环境要求**：Windows 10/11，Python 3.11+，推荐使用 Conda。

```powershell
# 1. 克隆仓库
git clone https://github.com/BLUE-lnfg/whalepet.git
cd whalepet

# 2. 创建环境并安装依赖
conda create -n whalepet python=3.11 -y
conda activate whalepet
pip install PySide6 av pillow pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 生成动画缓存（必须）
python tools/import_assets.py

# 4. 本地运行
python main.py
```

### 编译打包
```powershell
pyinstaller WhalePet.spec --clean
# 产物位于 dist/WhalePet/ 目录下
```

---

## ⚠️ 素材版权声明

**代码部分**：采用 MIT 协议开源。

**角色素材**：当前内置的“圣聆初雪”与“克莱门莎”形象及语音，版权归鹰角网络（Hypergryph）与《明日方舟》所有。仅作为个人学习与技术演示使用，**不得用于任何商业用途**。如需公开分发，请自行替换为拥有版权的素材。

---

## 💬 作者的话

作者是一个学生，由于找不到高清高帧率且能独立运行的桌宠，决定自己用 AI 辅助开发一个。整个项目的代码逻辑、架构设计均由 AI 编写，作者负责需求制定与测试验收。

目前 V0.9.0 已经实现了除“角色素材全量铺设”外的所有核心功能。如果在使用或二次开发中遇到 bug，欢迎提交 Issue。
