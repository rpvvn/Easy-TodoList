# MaterialTodo（待办清单）

一个 Windows 桌面待办事项小工具：**无原生边框、半透明磨砂圆角卡片**，可以透出后面的云层桌面壁纸，整体风格偏向现代移动端 Material Design。

## 功能

- 🌗 深色模式 / 浅色模式一键切换
- 🪟 无 Windows 原生窗口边框，整体为半透明磨砂圆角卡片
- 🌫 通过 Windows 10/11 的 Acrylic / Blur 效果模糊并透出桌面壁纸
- ✅ 主体区域显示全部待办（添加、编辑、勾选完成、删除、清除已完成）
- 🔒 锁定窗口位置，禁止拖动（同时拦截系统“移动”命令）
- 📌 窗口置顶开关
- 💾 数据自动保存到 `%APPDATA%\MaterialTodo\`
- 👻 启动时隐藏到系统托盘（设置中开启，或命令行加 `--hidden`）
- 🚀 开机自启（写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`）
- 🎚 窗口不透明度 40%～100% 可调
- 🔗 GitHub 项目仓库入口（窗口底部、设置面板、托盘菜单均可跳转）

## 快速运行（源码方式）

需要 Python 3.10+，然后：

```bat
cd /d 项目目录
python -m pip install -r requirements.txt
python main.py
```

或者直接双击 `run.bat`（会自动检查并安装依赖）。

启动参数：

- `python main.py --hidden`：启动后只驻留系统托盘，不显示主窗口
- `python main.py --show`：即使设置里开启了“启动时隐藏”，也强制显示主窗口

## 打包为 exe

直接双击运行：

```bat
build.bat
```

脚本会自动安装依赖、生成图标并调用 PyInstaller。产物位于：

```text
dist\MaterialTodo.exe
```

> 提示：打包前请先打开 `main.py`，把 `GITHUB_REPO_URL` 改成你自己的仓库地址。

## 使用 GitHub Actions 自动构建 exe

本项目包含 `.github/workflows/build-exe.yml`。推送到 GitHub 后：

1. 打开仓库的 **Actions** 页面；
2. 选择 **Build Windows EXE** 工作流；
3. 点击 **Run workflow** 手动运行；
4. 构建完成后，在运行记录底部下载 `MaterialTodo-windows` 制品压缩包，解压即得 exe。

## 项目结构

```text
main.py             主程序（界面 / 待办逻辑 / 托盘 / 自启 / 磨砂效果）
make_icon.py        app.ico 图标生成脚本
run.bat             源码方式快速运行
build.bat           一键打包脚本
requirements.txt    依赖清单
.github/workflows/  GitHub Actions 自动构建
```

## 数据位置

- `%APPDATA%\MaterialTodo\todos.json`：待办数据
- `%APPDATA%\MaterialTodo\settings.json`：主题、置顶、锁定、透明度等设置

## 常见问题

- **看不到磨砂效果？** Windows 10/11 需要开启系统透明效果。应用会优先尝试 Acrylic，失败时自动回退到传统 Blur。
- **窗口拖动不了？** 检查右上角锁按钮或设置中的“锁定窗口位置”是否开启；开启后点击锁按钮即可恢复拖动。
- **关闭按钮找不到了？** 关闭按钮会把应用最小化到系统托盘；如需完全退出，请右键托盘图标选择“退出”。
- **开机自启失败？** 程序会尝试写注册表，安全软件可能拦截；请以普通用户权限运行，或手动在注册表 Run 键添加带 `--hidden` 的命令。
- **SmartScreen 提示？** 本工具为 PyInstaller 打包的未签名程序，首次运行若出现 Windows 提示，选择“仍要运行”即可；如有条件可自行购买代码签名证书签名。
