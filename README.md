# Easy-TodoList

轻量级 Windows 桌面悬浮待办小组件：常驻桌面、半透明磨砂（毛玻璃）、圆角卡片，专注于「记录 / 完成 / 清除」三件事，极简、低占用。

> 仓库地址：<https://github.com/rpvvn/Easy-TodoList>

---

## 产品定位

- 桌面常驻悬浮小组件，无需打开完整页面即可可视化展示待办任务；
- 半透明磨砂（Acrylic / Blur）圆角造型，可透出桌面壁纸、不遮挡桌面图标；
- 深色 / 浅色主题，视觉柔和；
- 轻量运行、后台常驻系统托盘，不占用任务栏。

## 功能特性

- 🧊 半透明磨砂（毛玻璃）+ 圆角悬浮面板，磨砂严格限制在圆角内部，无方形泄露
- 📌 顶部信息栏：应用 Logo + 「N 个待办事项」动态计数 + 添加按钮 + 设置按钮
- 📝 主内容面板：「全部待办」标题 + 内嵌输入框（回车即添加）+ 待办列表
- ✅ 点击任务行标记完成（划横线置灰）
- ⭕ 右下角两个圆形悬浮按钮：打勾（全部标记完成）、打叉（清除已完成，点击即执行）
- ⚙️ 设置视图（整体替换主内容区）：磨砂透明度、窗体圆角大小、桌面置顶、显示/收起顶部栏、锁定位置、锁定大小、开机自启、托盘行为、全局快捷键
- ⌨️ 全局快捷键：唤起组件 / 新建待办（Windows `RegisterHotKey`，无需额外依赖）
- 🖱 任意空白区域拖动窗口、右下角拖动缩放
- 🪟 无边框、窗口置顶、透明度/圆角可调
- 👻 最小化到系统托盘、开机自启
- 💾 数据自动保存

## 界面结构

单窗口内上下两个圆角悬浮面板：

```
┌──────────────────────────────┐
│  [Logo] N个待办事项   ＋  ⚙️  │  ← 顶部信息栏
├──────────────────────────────┤
│  全部待办              ⚙️     │  ← 主内容面板（顶栏收起时齿轮才显示）
│  [输入框：回车添加]           │
│  ── 待办列表 ──               │
│                        ✓  ✕  │  ← 全部完成 / 清除已完成
└──────────────────────────────┘
```

## 快速运行（源码方式）

需要 Python 3.10+：

```bat
cd /d 项目目录
python -m pip install -r requirements.txt
python main.py
```

或直接双击 `run.bat`（会自动检查并安装依赖）。

启动参数：

- `python main.py --hidden`：启动后仅驻留系统托盘，不显示主窗口
- `python main.py --show`：即使设置里开启了「启动时隐藏到托盘」，也强制显示主窗口

## 打包为 exe

双击运行：

```bat
build.bat
```

脚本会自动安装依赖、生成图标并调用 PyInstaller，产出**免安装单文件 exe**：

```text
dist\Easy-TodoList.exe
```

## GitHub Actions 自动打包 + 自动发布

推送带 `v` 前缀的 tag（例如 `v1.0.0`）会触发 `.github/workflows/build-exe.yml`：

1. 在 `windows-latest` 上自动安装依赖、生成图标、用 PyInstaller 打包 exe；
2. 上传 `Easy-TodoList-windows` 构建产物；
3. 自动从 `UpdateLog.md` 提取该版本的更新说明，写入 GitHub Release 的 Release Notes，并附带 `Easy-TodoList.exe`。

手动触发：仓库 **Actions** 页 → **Build Windows EXE** → **Run workflow**。

## 数据位置

- `%APPDATA%\Easy-TodoList\todos.json`：待办数据
- `%APPDATA%\Easy-TodoList\settings.json`：主题、置顶、锁定、透明度、圆角、快捷键等设置

> 首次启动会自动从旧版本 `%APPDATA%\MaterialTodo` 迁移数据。

## 项目结构

```text
main.py              主程序（界面 / 待办逻辑 / 托盘 / 自启 / 磨砂 / 快捷键）
make_icon.py         app.ico 图标生成脚本
run.bat              源码方式快速运行
build.bat            一键打包脚本
Easy-TodoList.spec   PyInstaller 配置
requirements.txt     依赖清单
.github/workflows/   GitHub Actions 自动构建 + 自动发布
README.md            中文说明
README_EN.md         英文说明
UpdateLog.md         更新日志（自动同步到 Release Notes）
```

## 常见问题

- **看不到磨砂效果？** Windows 10/11 需要开启系统透明效果。
- **圆角外有方形磨砂 / 空隙不透明？** 已使用 DWM 区域模糊（`DwmEnableBlurBehindWindow` + `DWM_BB_BLURREGION`）严格裁剪到圆角面板内；若某些 Windows 11 版本该旧接口被弱化，圆角与透明空隙仍是严格正确的。
- **窗口拖不动？** 检查设置里的「锁定位置（禁止拖动）」是否开启。
- **窗口大小改不了？** 检查设置里的「锁定大小（禁止缩放）」是否开启。
- **关闭按钮找不到了？** 关闭按钮会把应用最小化到系统托盘；右键托盘图标可选择「退出」。
- **开机自启失败？** 程序会写注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，安全软件可能拦截。
- **SmartScreen 提示？** 本工具为 PyInstaller 打包的未签名程序，首次运行选择「仍要运行」即可。
