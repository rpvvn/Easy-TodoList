# -*- coding: utf-8 -*-
"""
Easy-TodoList —— 桌面悬浮待办小组件。

界面结构（单窗口，上下两个圆角悬浮面板）：
- 顶部信息栏：应用 Logo + 「N个待办事项」计数，右侧彩色加号添加按钮、彩色齿轮设置按钮；
- 下方主内容面板：「全部待办」标题、内嵌输入框、单行待办列表（点击标记完成）、
  右下角对勾（全部完成）/ 叉号（清除已完成）悬浮按钮。

保留能力：半透明磨砂圆角、系统托盘、开机自启、置顶、透明度/圆角调节、全局快捷键。
"""

from __future__ import annotations

import ctypes
import json
import math
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCloseEvent,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtNetwork import (
    QLocalServer,
    QLocalSocket,
)

APP_ID = "Easy-TodoList.App"
APP_NAME = "Easy-TodoList"
APP_DISPLAY_NAME = "Easy-TodoList"

# 项目仓库地址（设置面板 / 托盘菜单 / 页脚按钮都会跳转到此地址）
GITHUB_REPO_URL = "https://github.com/rpvvn/Easy-TodoList"

# 旧版本数据目录名（用于首次启动时迁移旧数据）
OLD_APP_NAME = "MaterialTodo"

AUTOSTART_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# 单实例检测使用的本地 socket 名称（Windows 下映射为命名管道，Linux 下为 socket 文件）
SINGLE_INSTANCE_KEY = "Easy-TodoList.SingleInstance"
WM_HOTKEY = 0x0312
WM_SYSCOMMAND = 0x0112
WM_MOVING = 0x0216
SC_SIZE = 0xF000
SC_MOVE = 0xF010

# 全局快捷键修饰符与热键 ID
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
HOTKEY_ID_SHOW = 1
HOTKEY_ID_NEW_TODO = 2

# 窗体默认圆角（可配置）；窗口不再预留透明外边距，面板即窗口，磨砂背景与面板完全重合。
DEFAULT_CORNER_RADIUS = 28
WINDOW_OUTER_MARGIN = 0


# ---------------------------------------------------------------------------
# 颜色系统（Material Design 风格）
# ---------------------------------------------------------------------------

DARK_COLORS = {
    "theme": "dark",
    "card": QColor(24, 26, 33, 184),
    "text": "#EEF1F7",
    "subtext": "#9AA4B5",
    "input": "#191C23",
    "surface": "#252934",
    "surface_hover": "#2D3340",
    "surface_active": "#343B4A",
    "surface_solid": "#222530",
    "surface_alpha": "rgba(37, 41, 52, 200)",
    "surface_hover_alpha": "rgba(45, 51, 64, 220)",
    "panel_alpha": "rgba(28, 31, 40, 205)",
    "border": "rgba(255, 255, 255, 24)",
    "border_strong": "rgba(255, 255, 255, 44)",
    "primary": "#5B7CFA",
    "primary_hover": "#7290FF",
    "primary_pressed": "#4A67E0",
    "primary_soft": "rgba(91, 124, 250, 42)",
    "on_primary": "#FFFFFF",
    "track_off": "#3B4250",
    "scroll": "rgba(255, 255, 255, 52)",
    "danger": "#FF6B6B",
    "danger_soft": "rgba(255, 107, 107, 32)",
    "success": "#69D68C",
    "shadow": QColor(0, 0, 0, 150),
}

LIGHT_COLORS = {
    "theme": "light",
    "card": QColor(248, 250, 255, 184),
    "text": "#1B1D24",
    "subtext": "#6B7280",
    "input": "#FFFFFF",
    "surface": "#F0F2F8",
    "surface_hover": "#E7EAF3",
    "surface_active": "#DCE1EE",
    "surface_solid": "#FFFFFF",
    "surface_alpha": "rgba(255, 255, 255, 215)",
    "surface_hover_alpha": "rgba(240, 242, 248, 240)",
    "panel_alpha": "rgba(252, 253, 255, 220)",
    "border": "rgba(20, 24, 40, 22)",
    "border_strong": "rgba(20, 24, 40, 46)",
    "primary": "#4F6BF5",
    "primary_hover": "#4160E8",
    "primary_pressed": "#3551D2",
    "primary_soft": "rgba(79, 107, 245, 32)",
    "on_primary": "#FFFFFF",
    "track_off": "#D8DCE8",
    "scroll": "rgba(20, 24, 40, 60)",
    "danger": "#E5484D",
    "danger_soft": "rgba(229, 72, 77, 28)",
    "success": "#2F9E5F",
    "shadow": QColor(32, 40, 80, 90),
}


# ---------------------------------------------------------------------------
# 配置与存储
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "theme": "dark",
    "opacity": 100,
    "topmost": False,
    "start_in_tray": False,
    "close_to_tray": True,
    "autostart": False,
    "corner_radius": DEFAULT_CORNER_RADIUS,
    "show_top_bar": True,
    "lock_position": False,
    "lock_size": False,
    "show_hotkey": "Ctrl+Alt+T",
    "new_todo_hotkey": "Ctrl+Alt+N",
    "geometry": None,
}


class Config:
    """负责 todos.json 与 settings.json 的读写。"""

    def __init__(self):
        base = os.environ.get("APPDATA")
        self.base_dir = Path(base) / APP_NAME if base else Path.home() / f".{APP_NAME.lower()}"
        self.todos_path = self.base_dir / "todos.json"
        self.settings_path = self.base_dir / "settings.json"
        self.settings = dict(DEFAULT_SETTINGS)
        self.todos: list[dict] = []
        self._migrate_old_data(base)
        self.load()

    def _migrate_old_data(self, base):
        """从旧版本 MaterialTodo 数据目录迁移到 Easy-TodoList（仅首次）。"""
        try:
            if self.base_dir.exists():
                return
            if not base:
                return
            old_dir = Path(base) / OLD_APP_NAME
            if not old_dir.exists():
                return
            self.base_dir.mkdir(parents=True, exist_ok=True)
            for name in ("todos.json", "settings.json"):
                src = old_dir / name
                if src.exists():
                    try:
                        (self.base_dir / name).write_bytes(src.read_bytes())
                    except OSError:
                        pass
        except OSError:
            pass

    @property
    def colors(self) -> dict:
        return DARK_COLORS if self.settings.get("theme") == "dark" else LIGHT_COLORS

    def load(self):
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key in DEFAULT_SETTINGS:
                    if key in data:
                        self.settings[key] = data[key]
        except (OSError, json.JSONDecodeError):
            pass

        try:
            opacity = int(self.settings.get("opacity", 100))
        except (TypeError, ValueError):
            opacity = 100
        self.settings["opacity"] = max(40, min(100, opacity))

        try:
            radius = int(self.settings.get("corner_radius", DEFAULT_CORNER_RADIUS))
        except (TypeError, ValueError):
            radius = DEFAULT_CORNER_RADIUS
        self.settings["corner_radius"] = max(8, min(40, radius))

        self.settings["theme"] = "dark" if self.settings.get("theme") != "light" else "light"
        self.settings["topmost"] = bool(self.settings.get("topmost"))
        self.settings["start_in_tray"] = bool(self.settings.get("start_in_tray"))
        self.settings["close_to_tray"] = bool(self.settings.get("close_to_tray"))
        self.settings["autostart"] = bool(self.settings.get("autostart"))
        self.settings["show_top_bar"] = bool(self.settings.get("show_top_bar", True))
        self.settings["lock_position"] = bool(self.settings.get("lock_position"))
        self.settings["lock_size"] = bool(self.settings.get("lock_size"))
        self.settings["show_hotkey"] = str(self.settings.get("show_hotkey", "Ctrl+Alt+T"))
        self.settings["new_todo_hotkey"] = str(self.settings.get("new_todo_hotkey", "Ctrl+Alt+N"))

        try:
            data = json.loads(self.todos_path.read_text(encoding="utf-8"))
            todos = data.get("todos", []) if isinstance(data, dict) else []
            clean = []
            for t in todos:
                if not isinstance(t, dict) or not str(t.get("title", "")).strip():
                    continue
                if not t.get("id"):
                    t["id"] = uuid.uuid4().hex[:14]
                t["done"] = bool(t.get("done"))
                clean.append(t)
            self.todos = clean
        except (OSError, json.JSONDecodeError):
            self.todos = []

    def save_settings(self):
        self._atomic_write(self.settings_path, self.settings)

    def save_todos(self):
        self._atomic_write(self.todos_path, {"version": 1, "todos": self.todos})

    @staticmethod
    def _atomic_write(path: Path, payload):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Windows Acrylic / Blur 背景效果
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    from ctypes import wintypes

    class _DWM_BLURBEHIND(ctypes.Structure):
        _fields_ = [
            ("dwFlags", ctypes.c_uint),
            ("fEnable", ctypes.c_int),
            ("hRgnBlur", wintypes.HRGN),
            ("fTransitionOnMaximized", ctypes.c_int),
        ]


def _is_native_windows() -> bool:
    """仅当运行在真实 Windows 窗口平台（非 offscreen 等测试平台）时返回 True。"""
    if sys.platform != "win32":
        return False
    app = QGuiApplication.instance()
    return bool(app) and app.platformName().lower().startswith("windows")


def _make_rounded_region(rects: list[tuple[int, int, int, int, int]]):
    """把多个 (x, y, w, h, radius) 物理像素圆角矩形合并为一个 HRGN（RGN_OR 并集）。"""
    if not rects:
        return None
    gdi32 = ctypes.windll.gdi32
    gdi32.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
    gdi32.CreateRoundRectRgn.restype = wintypes.HRGN
    gdi32.CreateRectRgn.argtypes = [ctypes.c_int] * 4
    gdi32.CreateRectRgn.restype = wintypes.HRGN
    gdi32.CombineRgn.argtypes = [wintypes.HRGN, wintypes.HRGN, wintypes.HRGN, ctypes.c_int]
    gdi32.CombineRgn.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL

    region = None
    for x, y, w, h, radius in rects:
        if w <= 0 or h <= 0:
            continue
        ellipse = max(2, int(radius) * 2)
        rgn = gdi32.CreateRoundRectRgn(x, y, x + w + 1, y + h + 1, ellipse, ellipse)
        if not rgn:
            continue
        if region is None:
            region = rgn
        else:
            combined = gdi32.CreateRectRgn(0, 0, 0, 0)
            gdi32.CombineRgn(combined, region, rgn, 2)  # RGN_OR
            gdi32.DeleteObject(region)
            gdi32.DeleteObject(rgn)
            region = combined
    return region


class WindowsEffects:
    """用 DWM 区域模糊实现「仅在圆角面板内磨砂」，避免模糊溢出到圆角外或中间空隙。"""

    @staticmethod
    def apply_region_blur(hwnd: int, region) -> None:
        if sys.platform != "win32" or not hwnd or not region:
            return
        try:
            bb = _DWM_BLURBEHIND()
            bb.dwFlags = 1 | 2  # DWM_BB_ENABLE | DWM_BB_BLURREGION
            bb.fEnable = 1
            bb.hRgnBlur = region
            bb.fTransitionOnMaximized = 0
            enable_blur = ctypes.windll.dwmapi.DwmEnableBlurBehindWindow
            enable_blur.argtypes = [wintypes.HWND, ctypes.POINTER(_DWM_BLURBEHIND)]
            enable_blur.restype = ctypes.c_long
            enable_blur(wintypes.HWND(hwnd), ctypes.byref(bb))
        except Exception:
            pass


def _set_windows_app_id() -> None:
    if sys.platform == "win32":
        try:
            set_app_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            set_app_id.argtypes = [ctypes.c_wchar_p]
            set_app_id.restype = ctypes.c_long
            set_app_id(APP_ID)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 单实例守护（重复运行检测）
# ---------------------------------------------------------------------------

class SingleInstanceServer(QObject):
    """监听本地 socket：已有实例运行时，新实例把启动意图转发过来。"""

    show_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)

    def listen(self) -> bool:
        if self._server.isListening():
            return True
        # 清理可能残留的 socket（Linux 下崩溃后可能遗留文件）
        QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        return self._server.listen(SINGLE_INSTANCE_KEY)

    def _on_new_connection(self):
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(lambda c=conn: self._on_ready_read(c))
        conn.disconnected.connect(conn.deleteLater)

    def _on_ready_read(self, conn):
        msg = bytes(conn.readAll()).decode("utf-8", "replace").strip().lower()
        # 普通启动或显式 --show 时唤起主窗口；--hidden/--tray 则保持现状
        if msg != "hide":
            self.show_requested.emit()
        conn.disconnectFromServer()


def _notify_existing_instance(argv: list[str]) -> bool:
    """若已有实例在运行，把本次启动意图转发过去并返回 True。"""
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_KEY)
    if not socket.waitForConnected(250):
        return False
    force_hide = ("--hidden" in argv or "--tray" in argv) and "--show" not in argv
    socket.write(b"hide" if force_hide else b"show")
    socket.flush()
    socket.waitForBytesWritten(250)
    socket.disconnectFromServer()
    return True


# ---------------------------------------------------------------------------
# 开机自启
# ---------------------------------------------------------------------------

def _autostart_command() -> str:
    exe = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{exe}"'
    if sys.platform == "win32" and exe.name.lower() == "python.exe":
        pyw = exe.with_name("pythonw.exe")
        if pyw.exists():
            exe = pyw
    script = Path(__file__).resolve()
    return f'"{exe}" "{script}"'


def set_autostart(enabled: bool) -> tuple[bool, str]:
    command = _autostart_command()
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            with key:
                if enabled:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True, ""
        except OSError as exc:
            return False, str(exc)

    desktop_file = Path.home() / ".config" / "autostart" / "easy-todolist.desktop"
    try:
        if enabled:
            desktop_file.parent.mkdir(parents=True, exist_ok=True)
            desktop_file.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={APP_DISPLAY_NAME}\n"
                f"Exec={command}\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            desktop_file.unlink(missing_ok=True)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def is_autostart_enabled() -> bool:
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY, 0, winreg.KEY_QUERY_VALUE)
            with key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except OSError:
            return False
    return (Path.home() / ".config" / "autostart" / "easy-todolist.desktop").exists()


# ---------------------------------------------------------------------------
# 全局快捷键
# ---------------------------------------------------------------------------

_MOD_TO_TEXT = [
    (MOD_CONTROL, "Ctrl"),
    (MOD_ALT, "Alt"),
    (MOD_SHIFT, "Shift"),
    (MOD_WIN, "Win"),
]

_VK_TO_TEXT = {ord("A") + i: chr(ord("A") + i) for i in range(26)}
_VK_TO_TEXT.update({ord("0") + i: str(i) for i in range(10)})
for i in range(1, 13):
    _VK_TO_TEXT[0x70 + i - 1] = f"F{i}"  # VK_F1 = 0x70
_VK_TO_TEXT.update({
    0x20: "Space",
    0x0D: "Enter",
    0x09: "Tab",
    0x2E: "Delete",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x21: "PageUp",
    0x22: "PageDown",
    0x23: "End",
    0x24: "Home",
})

_TEXT_TO_VK: dict[str, int] = {}
for _vk, _text in _VK_TO_TEXT.items():
    _TEXT_TO_VK[_text] = _vk
    _TEXT_TO_VK[_text.lower()] = _vk


def parse_hotkey(text) -> tuple[int, int]:
    """解析 "Ctrl+Alt+T" 为 (modifiers, vk)。无效时返回 (0, 0)。"""
    mods = 0
    vk = 0
    if not text:
        return 0, 0
    parts = [p.strip() for p in text.split("+") if p.strip()]
    if not parts:
        return 0, 0
    for part in parts[:-1]:
        low = part.lower()
        if low in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif low == "alt":
            mods |= MOD_ALT
        elif low == "shift":
            mods |= MOD_SHIFT
        elif low in ("win", "windows", "cmd", "super"):
            mods |= MOD_WIN
        else:
            return 0, 0
    key = parts[-1]
    vk = _TEXT_TO_VK.get(key)
    if vk is None:
        if len(key) == 1:
            vk = ord(key.upper())
            if not (ord("A") <= vk <= ord("Z") or ord("0") <= vk <= ord("9")):
                return 0, 0
        else:
            return 0, 0
    return mods, vk


def format_hotkey(mods: int, vk: int) -> str:
    parts = [text for m, text in _MOD_TO_TEXT if mods & m]
    key = _VK_TO_TEXT.get(vk, "")
    if not key:
        return ""
    parts.append(key)
    return "+".join(parts)


def register_hotkey(hwnd: int, hotkey_id: int, text) -> bool:
    if not _is_native_windows():
        return False
    mods, vk = parse_hotkey(text)
    if not vk:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        user32.RegisterHotKey.restype = wintypes.BOOL
        return bool(user32.RegisterHotKey(wintypes.HWND(hwnd), hotkey_id, mods, vk))
    except Exception:
        return False


def unregister_hotkey(hwnd: int, hotkey_id: int) -> None:
    if not _is_native_windows():
        return
    try:
        user32 = ctypes.windll.user32
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.UnregisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey(wintypes.HWND(hwnd), hotkey_id)
    except Exception:
        pass


def _qt_key_to_vk(e: QKeyEvent) -> int:
    key = e.key()
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return ord("A") + (key - Qt.Key.Key_A)
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return ord("0") + (key - Qt.Key.Key_0)
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        return 0x70 + (key - Qt.Key.Key_F1)
    m = {
        Qt.Key.Key_Space: 0x20,
        Qt.Key.Key_Return: 0x0D,
        Qt.Key.Key_Enter: 0x0D,
        Qt.Key.Key_Tab: 0x09,
        Qt.Key.Key_Delete: 0x2E,
        Qt.Key.Key_Up: 0x26,
        Qt.Key.Key_Down: 0x28,
        Qt.Key.Key_Left: 0x25,
        Qt.Key.Key_Right: 0x27,
        Qt.Key.Key_PageUp: 0x21,
        Qt.Key.Key_PageDown: 0x22,
        Qt.Key.Key_End: 0x23,
        Qt.Key.Key_Home: 0x24,
    }
    return m.get(key, 0)


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def _parse_color(value) -> QColor:
    """把颜色配置转成 QColor，兼容 #RRGGBB / rgba(...) / QColor。"""
    if isinstance(value, QColor):
        return QColor(value)
    if isinstance(value, str):
        text = value.strip()
        if text.lower().startswith("rgba(") and text.endswith(")"):
            parts = [p.strip() for p in text[5:-1].split(",")]
            if len(parts) >= 3:
                try:
                    r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    a = int(float(parts[3])) if len(parts) >= 4 else 255
                    return QColor(r, g, b, a)
                except ValueError:
                    pass
        return QColor(text)
    return QColor(value)


def _mix_color(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        round(c1.red() + (c2.red() - c1.red()) * t),
        round(c1.green() + (c2.green() - c1.green()) * t),
        round(c1.blue() + (c2.blue() - c1.blue()) * t),
        round(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


def _format_time(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return str(iso).replace("T", " ")[:16]
    now = datetime.now().astimezone()
    if dt.tzinfo is None:
        dt = dt.astimezone()
    if dt.date() == now.date():
        return f"今天 {dt:%H:%M}"
    if dt.year == now.year:
        return f"{dt:%m-%d} {dt:%H:%M}"
    return f"{dt:%Y-%m-%d}"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _draw_app_logo(p: QPainter, rect: QRectF, colors: dict) -> None:
    """绘制 app.ico 同款 logo：蓝色圆角方块 + 白色对勾。"""
    path = QPainterPath()
    path.addRoundedRect(rect, rect.width() * 0.27, rect.height() * 0.27)
    p.fillPath(path, QBrush(_parse_color(colors["primary"])))
    pen = QPen(
        _parse_color(colors["on_primary"]),
        max(2.0, rect.width() * 0.10),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    check = QPainterPath()
    check.moveTo(rect.x() + rect.width() * 0.30, rect.y() + rect.height() * 0.52)
    check.lineTo(rect.x() + rect.width() * 0.44, rect.y() + rect.height() * 0.66)
    check.lineTo(rect.x() + rect.width() * 0.70, rect.y() + rect.height() * 0.36)
    p.drawPath(check)


def _make_icon(colors: dict) -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_app_logo(p, QRectF(4, 4, 56, 56), colors)
    p.end()
    return QIcon(pix)


# ---------------------------------------------------------------------------
# 矢量图标
# ---------------------------------------------------------------------------

def _draw_vector_icon(p: QPainter, kind: str, rect: QRectF, color: QColor) -> None:
    """在 rect 内用矢量路径绘制图标（清晰、抗锯齿、随主题变色）。"""
    w = rect.width()
    h = rect.height()
    sw = max(1.3, w * 0.085)
    pen = QPen(color, sw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    def pt(fx: float, fy: float) -> QPointF:
        return QPointF(rect.x() + w * fx, rect.y() + h * fy)

    cx = rect.x() + w * 0.5
    cy = rect.y() + h * 0.5

    if kind == "minus":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(pt(0.28, 0.5), pt(0.72, 0.5))
    elif kind == "close":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(pt(0.30, 0.30), pt(0.70, 0.70))
        p.drawLine(pt(0.70, 0.30), pt(0.30, 0.70))
    elif kind == "plus":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(pt(0.5, 0.24), pt(0.5, 0.76))
        p.drawLine(pt(0.24, 0.5), pt(0.76, 0.5))
    elif kind == "plus_filled":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawRoundedRect(QRectF(rect.x() + w * 0.42, rect.y() + h * 0.20, w * 0.16, h * 0.60), w * 0.05, w * 0.05)
        p.drawRoundedRect(QRectF(rect.x() + w * 0.20, rect.y() + h * 0.42, w * 0.60, h * 0.16), w * 0.05, w * 0.05)
    elif kind == "check":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(pt(0.26, 0.52).x(), pt(0.26, 0.52).y())
        path.lineTo(pt(0.44, 0.70).x(), pt(0.44, 0.70).y())
        path.lineTo(pt(0.74, 0.32).x(), pt(0.74, 0.32).y())
        p.drawPath(path)
    elif kind == "sun":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r_in = w * 0.17
        r_out = w * 0.28
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(
                QPointF(cx + math.cos(a) * r_in, cy + math.sin(a) * r_in),
                QPointF(cx + math.cos(a) * r_out, cy + math.sin(a) * r_out),
            )
        p.drawEllipse(QPointF(cx, cy), w * 0.115, w * 0.115)
    elif kind == "moon":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        r = w * 0.26
        path = QPainterPath()
        path.addEllipse(QPointF(cx, cy), r, r)
        bite = QPainterPath()
        bite.addEllipse(QPointF(cx + r * 0.55, cy - r * 0.48), r * 0.85, r * 0.85)
        p.drawPath(path.subtracted(bite))
    elif kind == "pin":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect.x() + w * 0.36, rect.y() + h * 0.12, w * 0.28, h * 0.30), w * 0.07, w * 0.07)
        path.moveTo(rect.x() + w * 0.41, rect.y() + h * 0.42)
        path.lineTo(rect.x() + w * 0.59, rect.y() + h * 0.42)
        path.lineTo(cx, rect.y() + h * 0.90)
        path.closeSubpath()
        p.drawPath(path)
    elif kind in ("lock", "unlock"):
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        body = QRectF(rect.x() + w * 0.26, rect.y() + h * 0.46, w * 0.48, h * 0.38)
        p.drawRoundedRect(body, w * 0.09, w * 0.09)
        arc = QRectF(rect.x() + w * 0.30, rect.y() + h * 0.14, w * 0.40, h * 0.38)
        if kind == "unlock":
            p.drawArc(arc, 180 * 16, -150 * 16)
        else:
            p.drawArc(arc, 180 * 16, -180 * 16)
        p.drawLine(QPointF(cx, rect.y() + h * 0.58), QPointF(cx, rect.y() + h * 0.68))
        p.drawEllipse(QPointF(cx, rect.y() + h * 0.73), w * 0.045, w * 0.045)
    elif kind == "gear":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r0 = w * 0.19
        r1 = w * 0.28
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            p.drawLine(
                QPointF(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                QPointF(cx + math.cos(a) * r1, cy + math.sin(a) * r1),
            )
        p.drawEllipse(QPointF(cx, cy), w * 0.16, w * 0.16)
        p.drawEllipse(QPointF(cx, cy), w * 0.06, w * 0.06)
    elif kind == "gear_filled":
        # 彩色实心齿轮（类似 ⚙️）
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        path.addEllipse(QPointF(cx, cy), w * 0.20, w * 0.20)
        r_mid = w * 0.27
        r_tooth = w * 0.075
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            path.addEllipse(QPointF(cx + math.cos(a) * r_mid, cy + math.sin(a) * r_mid), r_tooth, r_tooth)
        path.addEllipse(QPointF(cx, cy), w * 0.085, w * 0.085)
        p.drawPath(path)
    elif kind == "pencil":
        # 铅笔（类似 ✏️）
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(pt(0.30, 0.70), pt(0.58, 0.42))
        p.drawLine(pt(0.58, 0.42), pt(0.74, 0.26))
        p.drawLine(pt(0.68, 0.32), pt(0.74, 0.26))
        p.drawLine(pt(0.26, 0.74), pt(0.36, 0.64))


# ---------------------------------------------------------------------------
# 基础自定义控件
# ---------------------------------------------------------------------------

class IconButton(QAbstractButton):
    """图标按钮：用 QPainter 绘制矢量图标，避免 emoji/文本字形发虚或渲染不一致。"""

    def __init__(self, icon: str, color_provider, checkable: bool = False,
                 tooltip: str = "", size: int = 30, active_icon: str | None = None,
                 danger: bool = False, muted: bool = False, colored: bool = False,
                 danger_always: bool = False):
        super().__init__()
        self._icon = icon
        self._active_icon = active_icon or icon
        self._provider = color_provider
        self._danger = danger
        self._muted = muted
        self._colored = colored
        self._danger_always = danger_always
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        if tooltip:
            self.setToolTip(tooltip)

    def set_icon(self, icon: str):
        if icon != self._icon:
            self._icon = icon
            self.update()

    def set_active(self, active: bool):
        if self.isCheckable():
            self.setChecked(active)

    def _current_icon(self) -> str:
        if self.isCheckable() and self.isChecked():
            return self._active_icon
        return self._icon

    def sizeHint(self):
        return QSize(self.width(), self.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._provider()
        w = self.width()

        bg = None
        if self.isChecked():
            bg = _parse_color(c["primary_soft"])
        elif self.underMouse() and self.isEnabled():
            bg = _parse_color(c["danger_soft"] if (self._danger or self._danger_always) else c["surface_hover"])
        if bg is not None and bg.alpha() > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(bg))
            p.drawEllipse(QRectF(1, 1, w - 2, w - 2))

        if self._colored:
            fg = _parse_color(c["primary_hover"] if self.underMouse() else c["primary"])
        elif self._danger_always:
            fg = _parse_color(c["danger"])
        elif self._danger and self.underMouse() and not self.isChecked():
            fg = _parse_color(c["danger"])
        elif self.isChecked():
            fg = _parse_color(c["primary"])
        elif self._muted and not self.underMouse():
            fg = _parse_color(c["subtext"])
        else:
            fg = _parse_color(c["text"])
        if not self.isEnabled():
            fg.setAlpha(max(40, fg.alpha() // 2))

        _draw_vector_icon(p, self._current_icon(), QRectF(0, 0, w, w), fg)
        p.end()


class FAB(QAbstractButton):
    """右下角圆形悬浮按钮：图标内嵌于半透明圆形底色中。"""

    def __init__(self, icon: str, color_provider, tooltip: str = "", size: int = 46,
                 tone: str = "neutral", danger_hover: bool = False):
        super().__init__()
        self._icon = icon
        self._provider = color_provider
        self._tone = tone
        self._danger_hover = danger_hover
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        if tooltip:
            self.setToolTip(tooltip)

    def sizeHint(self):
        return QSize(self.width(), self.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._provider()
        w = self.width()
        hover = self.underMouse() and self.isEnabled()

        if self._tone == "primary":
            bg = _parse_color(c["primary"] if hover else c["primary_soft"])
            fg = _parse_color(c["on_primary"] if hover else c["primary"])
        elif self._danger_hover and hover:
            bg = _parse_color(c["danger"])
            fg = _parse_color(c["on_primary"])
        else:
            bg = _parse_color(c["surface_hover_alpha"] if hover else c["surface_alpha"])
            fg = _parse_color(c["text"])

        p.setPen(QPen(_parse_color(c["border_strong"]), 1.0))
        p.setBrush(QBrush(bg))
        p.drawEllipse(QRectF(1.5, 1.5, w - 3, w - 3))
        _draw_vector_icon(p, self._icon, QRectF(0, 0, w, w), fg)
        p.end()


class MaterialSwitch(QAbstractButton):
    """Material 风格开关。"""

    def __init__(self, color_provider, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._provider = color_provider
        self._offset = 1.0 if checked else 0.0
        self._anim: QPropertyAnimation | None = None
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(46, 26)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggled.connect(self._on_toggled)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._set_offset(1.0 if checked else 0.0)

    def _on_toggled(self, checked: bool):
        self._animate_to(checked)

    def _animate_to(self, checked: bool):
        if self._anim is not None:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(170)
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _set_offset(self, value: float):
        self._offset = max(0.0, min(1.0, value))
        self.update()

    def _get_offset(self) -> float:
        return self._offset

    offset = Property(float, _get_offset, _set_offset)

    def sizeHint(self):
        return QSize(46, 26)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._provider()
        track_off = QColor(c["track_off"])
        primary = QColor(c["primary"])
        track = _mix_color(track_off, primary, self._offset)
        track.setAlpha(220)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track))
        p.drawRoundedRect(QRectF(0, 3, self.width(), self.height() - 6), 10, 10)

        knob_d = 20
        x = 3 + (self.width() - knob_d - 6) * self._offset
        y = (self.height() - knob_d) / 2
        p.setBrush(QBrush(QColor(c["on_primary"])))
        p.setPen(QPen(QColor(0, 0, 0, 32), 1))
        p.drawEllipse(QRectF(x + 0.5, y + 0.5, knob_d, knob_d))
        p.end()


class CheckButton(QAbstractButton):
    """Material 圆形复选框。"""

    def __init__(self, color_provider, parent: QWidget | None = None):
        super().__init__(parent)
        self._provider = color_provider
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(26, 26)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._provider()
        rect = QRectF(4, 4, 18, 18)
        if self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(c["primary"])))
            p.drawEllipse(rect)
            pen = QPen(QColor(c["on_primary"]), 2.0, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(9.0, 13.0)
            path.lineTo(11.8, 15.8)
            path.lineTo(16.8, 10.2)
            p.drawPath(path)
        else:
            color = QColor(c["primary"]) if self.underMouse() else QColor(c["track_off"])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(color, 2.0))
            p.drawEllipse(rect.adjusted(0.5, 0.5, -0.5, -0.5))
        p.end()


class ElideLabel(QLabel):
    """单行省略号标签。"""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self._full = text

    def setText(self, text: str):
        self._full = text
        self._update_elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self):
        fm = self.fontMetrics()
        super().setText(fm.elidedText(self._full, Qt.TextElideMode.ElideRight, max(20, self.width())))


class HotkeyEdit(QAbstractButton):
    """全局快捷键录制控件：点击后按下组合键即可录制。"""

    hotkey_changed = Signal(str)

    def __init__(self, color_provider, hotkey: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._provider = color_provider
        self._hotkey = hotkey
        self._recording = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(30)
        self.setMinimumWidth(120)

    def hotkey(self) -> str:
        return self._hotkey

    def set_hotkey(self, text: str):
        self._hotkey = text
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._recording = True
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if not self._recording:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_Escape:
            self._recording = False
            self.update()
            event.accept()
            return
        mods = 0
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            mods |= MOD_CONTROL
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            mods |= MOD_ALT
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            mods |= MOD_SHIFT
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            mods |= MOD_WIN
        vk = _qt_key_to_vk(event)
        if vk and mods:
            self._hotkey = format_hotkey(mods, vk)
            self._recording = False
            self.update()
            self.clearFocus()
            self.hotkey_changed.emit(self._hotkey)
        event.accept()

    def focusOutEvent(self, event):
        self._recording = False
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._provider()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg = _parse_color(c["primary_soft"] if self._recording else c["surface_solid"])
        border = _parse_color(c["border_strong"] if self._recording else c["border"])
        p.setPen(QPen(border, 1.0))
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(rect, 8, 8)
        text = "请按下快捷键…" if self._recording else (self._hotkey or "未设置")
        color = _parse_color(c["primary"] if self._recording else c["text"])
        p.setPen(QPen(color))
        font = self.font()
        font.setPointSize(9)
        p.setFont(font)
        p.drawText(rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        p.end()


class DragController(QObject):
    """在滚动区域空白处拖动窗口。"""

    def __init__(self, window: QWidget):
        super().__init__(window)
        self._win = window
        self._start_global: QPoint | None = None
        self._window_start: QPoint | None = None

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            if not self._win.drag_locked():
                self._start_global = event.globalPosition().toPoint()
                self._window_start = self._win.pos()
            return False
        if t == QEvent.Type.MouseMove and self._start_global is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                delta = event.globalPosition().toPoint() - self._start_global
                self._win.move(self._window_start + delta)
                return True
        if t == QEvent.Type.MouseButtonRelease:
            self._start_global = None
            self._window_start = None
        return False


class ResizeGrip(QWidget):
    """右下角拖动调整窗口大小（可被「锁定大小」禁用）。"""

    def __init__(self, window: QWidget):
        super().__init__(window)
        self._win = window
        self._start_global: QPoint | None = None
        self._start_size: QSize | None = None
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("拖动调整大小")

    def _locked(self) -> bool:
        return bool(self._win.cfg.settings.get("lock_size"))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._win.cfg.colors
        pen = QPen(_parse_color(c["subtext"]), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(11, 3, 3, 11)
        p.drawLine(13, 3, 3, 13)
        p.drawLine(15, 3, 3, 15)
        p.end()

    def mousePressEvent(self, event: QMouseEvent):
        if self._locked():
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_global = event.globalPosition().toPoint()
            self._start_size = self._win.size()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._start_global is None or self._locked():
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        delta = event.globalPosition().toPoint() - self._start_global
        new_w = max(self._win.minimumWidth(), min(self._win.maximumWidth(), self._start_size.width() + delta.x()))
        new_h = max(self._win.minimumHeight(), min(self._win.maximumHeight(), self._start_size.height() + delta.y()))
        self._win.resize(new_w, new_h)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._start_global = None
        self._start_size = None
        event.accept()


class RoundedPanel(QWidget):
    """圆角悬浮面板基类：自绘圆角背景 + 支持空白区域拖动。"""

    def __init__(self, window: QWidget, radius: float = DEFAULT_CORNER_RADIUS):
        super().__init__(window)
        self._win = window
        self._radius = radius
        self._drag_start: QPoint | None = None
        self._window_start: QPoint | None = None

    def _colors(self) -> dict:
        cfg = getattr(self._win, "cfg", None)
        return cfg.colors if cfg is not None else DARK_COLORS

    def set_radius(self, radius: float):
        self._radius = radius
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._colors()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        p.fillPath(path, QBrush(_parse_color(c["panel_alpha"])))
        p.setPen(QPen(_parse_color(c["border"]), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self._win.drag_locked():
            self._drag_start = event.globalPosition().toPoint()
            self._window_start = self._win.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._drag_start
            self._win.move(self._window_start + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start = None
        self._window_start = None
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# 顶部信息栏
# ---------------------------------------------------------------------------

class CountBadge(QWidget):
    """待办清单图标（不再显示红色数量角标）。"""

    def __init__(self, color_provider, size: int = 30):
        super().__init__()
        self._provider = color_provider
        self.setFixedSize(size, size)

    def set_count(self, count: int):
        pass  # 数量只通过文字「N个待办事项」展示

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._provider()
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        _draw_app_logo(p, rect, c)
        p.end()


class TopBar(RoundedPanel):
    """顶部信息栏（独立悬浮条）。"""

    def __init__(self, window: QWidget, color_provider):
        super().__init__(window, 0.0)
        self.setFixedHeight(56)
        self._provider = color_provider

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 10, 6)
        lay.setSpacing(10)

        self._badge = CountBadge(color_provider, 30)
        self._badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self._count_label = QLabel("0个待办事项")
        self._count_label.setObjectName("topbarCount")
        self._count_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self._count_label, 0, Qt.AlignmentFlag.AlignVCenter)

        lay.addStretch(1)

        self.add_btn = IconButton("plus_filled", color_provider, tooltip="新建待办", size=34, colored=True)
        self.settings_btn = IconButton("gear_filled", color_provider, checkable=True, tooltip="设置", size=34, colored=True)
        lay.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.add_btn.clicked.connect(window.reveal_add_input)
        self.settings_btn.toggled.connect(window.set_settings_open)

    def set_radii_for_radius(self, radius: float):
        self.set_radius(min(radius, 18.0))

    def update_count(self, count: int):
        self._badge.set_count(count)
        self._count_label.setText(f"{count}个待办事项")


# ---------------------------------------------------------------------------
# 待办行
# ---------------------------------------------------------------------------

class TodoRow(QFrame):
    toggled = Signal(str, bool)
    edit_requested = Signal(str, str)
    delete_requested = Signal(str)

    def __init__(self, todo: dict, color_provider, parent: QWidget | None = None):
        super().__init__(parent)
        self.todo = todo
        self._provider = color_provider
        self._editing = False
        self.setObjectName("todoRow")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 7, 6, 7)
        lay.setSpacing(8)

        self.check = CheckButton(color_provider, self)
        lay.addWidget(self.check, 0, Qt.AlignmentFlag.AlignVCenter)

        self.title = ElideLabel(todo.get("title", ""), self)
        self.title.setObjectName("todoTitle")
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self.title, 1)

        self.editor = QLineEdit(self)
        self.editor.setObjectName("editInput")
        self.editor.hide()
        lay.addWidget(self.editor, 1)

        self.edit_btn = IconButton("pencil", color_provider, tooltip="编辑", size=24, muted=True)
        self.delete_btn = IconButton("close", color_provider, tooltip="删除", size=24, danger_always=True)
        self.edit_btn.hide()
        self.delete_btn.hide()
        lay.addWidget(self.edit_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self.delete_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.check.toggled.connect(lambda checked: self.toggled.emit(self.todo.get("id", ""), checked))
        self.edit_btn.clicked.connect(self._begin_edit)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.todo.get("id", "")))
        self.editor.returnPressed.connect(self._commit_edit)
        self.editor.editingFinished.connect(self._commit_edit)

        self.update_appearance()

    def update_appearance(self):
        done = bool(self.todo.get("done"))
        c = self._provider()
        font = self.title.font()
        font.setStrikeOut(done)
        self.title.setFont(font)
        if done:
            self.title.setStyleSheet(f"color: {c['subtext']};")
        else:
            self.title.setStyleSheet("")
        self.check.blockSignals(True)
        self.check.setChecked(done)
        self.check.blockSignals(False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self._editing:
            self.toggled.emit(self.todo.get("id", ""), not bool(self.todo.get("done")))
            event.accept()
            return
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._editing:
            self.edit_btn.show()
            self.delete_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.edit_btn.hide()
        self.delete_btn.hide()
        super().leaveEvent(event)

    def _begin_edit(self):
        if self._editing:
            return
        self._editing = True
        self.editor.setText(self.todo.get("title", ""))
        self.title.hide()
        self.edit_btn.hide()
        self.delete_btn.hide()
        self.editor.show()
        self.editor.setFocus(Qt.FocusReason.MouseFocusReason)
        self.editor.selectAll()

    def _commit_edit(self):
        if not self._editing:
            return
        self._editing = False
        text = self.editor.text().strip()
        old = str(self.todo.get("title", "")).strip()
        self.editor.hide()
        self.title.show()
        if text and text != old:
            self.todo["title"] = text
            self.title.setText(text)
            self.edit_requested.emit(self.todo.get("id", ""), text)
        else:
            self.update_appearance()


# ---------------------------------------------------------------------------
# 主内容面板
# ---------------------------------------------------------------------------

class MainPanel(RoundedPanel):
    def __init__(self, window: QWidget, color_provider):
        super().__init__(window, 0.0)
        self._provider = color_provider

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.title_label = QLabel("全部待办")
        self.title_label.setObjectName("mainTitle")
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.settings_btn = IconButton("gear_filled", color_provider, checkable=True, tooltip="设置", size=28, colored=True)
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)
        title_row.addWidget(self.settings_btn)
        lay.addLayout(title_row)

        self.settings_btn.toggled.connect(window.set_settings_open)

        self._input = QLineEdit(self)
        self._input.setObjectName("todoInput")
        self._input.setPlaceholderText("输入待办事项，按 Enter 保存")
        self._input.setFixedHeight(38)
        self._input.returnPressed.connect(window._add_from_input)
        lay.addWidget(self._input)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 8, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._list_container)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.viewport().setStyleSheet("background: transparent;")
        self._drag_controller = DragController(window)
        self._scroll.viewport().installEventFilter(self._drag_controller)
        lay.addWidget(self._scroll, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch(1)
        self.check_all_btn = FAB("check", color_provider, tooltip="全部标记完成", size=44, tone="primary")
        self.clear_completed_btn = FAB("close", color_provider, tooltip="清除已完成", size=44, tone="primary")
        self._grip = ResizeGrip(window)
        footer.addWidget(self.check_all_btn, 0, Qt.AlignmentFlag.AlignBottom)
        footer.addWidget(self.clear_completed_btn, 0, Qt.AlignmentFlag.AlignBottom)
        footer.addSpacing(2)
        footer.addWidget(self._grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        lay.addLayout(footer)

        self.check_all_btn.clicked.connect(window.mark_all_done)
        self.clear_completed_btn.clicked.connect(window.clear_completed)

    def set_radii_for_radius(self, radius: float):
        self.set_radius(radius)

    @property
    def input(self) -> QLineEdit:
        return self._input

    @property
    def list_layout(self):
        return self._list_layout

    @property
    def scroll(self) -> QScrollArea:
        return self._scroll


# ---------------------------------------------------------------------------
# 设置面板
# ---------------------------------------------------------------------------

class SettingsPanel(RoundedPanel):
    def __init__(self, window: QWidget):
        super().__init__(window, 0.0)
        self._win = window

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(6)
        self._back_btn = IconButton("close", lambda: window.cfg.colors, tooltip="返回待办", size=28)
        title = QLabel("设置")
        title.setObjectName("sectionLabel")
        head.addWidget(self._back_btn)
        head.addWidget(title)
        head.addStretch(1)
        lay.addLayout(head)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(2, 2, 8, 2)
        v.setSpacing(9)
        self._scroll.setWidget(content)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.viewport().setStyleSheet("background: transparent;")
        lay.addWidget(self._scroll, 1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(1, 1)

        self._theme_switch = self._make_switch(self._on_theme_changed, window.cfg.settings.get("theme") == "dark")
        self._topmost_switch = self._make_switch(self._on_topmost_changed, window.cfg.settings.get("topmost"))
        self._topbar_switch = self._make_switch(self._on_topbar_changed, window.cfg.settings.get("show_top_bar"))
        self._lock_position_switch = self._make_switch(self._on_lock_position_changed, window.cfg.settings.get("lock_position"))
        self._lock_size_switch = self._make_switch(self._on_lock_size_changed, window.cfg.settings.get("lock_size"))
        self._autostart_switch = self._make_switch(self._on_autostart_changed, window.cfg.settings.get("autostart"))
        self._tray_switch = self._make_switch(self._on_start_tray_changed, window.cfg.settings.get("start_in_tray"))
        self._close_tray_switch = self._make_switch(self._on_close_tray_changed, window.cfg.settings.get("close_to_tray"))

        rows = [
            ("深色模式", self._theme_switch),
            ("桌面置顶", self._topmost_switch),
            ("显示顶部信息栏", self._topbar_switch),
            ("锁定位置（禁止拖动）", self._lock_position_switch),
            ("锁定大小（禁止缩放）", self._lock_size_switch),
            ("开机自启", self._autostart_switch),
            ("启动时隐藏到托盘", self._tray_switch),
            ("关闭时最小化到托盘", self._close_tray_switch),
        ]
        for row, (text, switch) in enumerate(rows):
            label = QLabel(text)
            label.setObjectName("settingLabel")
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(switch, row, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.addLayout(grid)

        opacity_row = QHBoxLayout()
        opacity_label = QLabel("磨砂透明度")
        opacity_label.setObjectName("settingLabel")
        self._opacity_value = QLabel("100%")
        self._opacity_value.setObjectName("opacityValue")
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(40, 100)
        self._opacity_slider.setValue(int(window.cfg.settings.get("opacity")))
        self._opacity_slider.setFixedWidth(130)
        self._opacity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(opacity_label)
        opacity_row.addStretch(1)
        opacity_row.addWidget(self._opacity_value)
        opacity_row.addSpacing(8)
        opacity_row.addWidget(self._opacity_slider)
        v.addLayout(opacity_row)

        radius_row = QHBoxLayout()
        radius_label = QLabel("窗体圆角大小")
        radius_label.setObjectName("settingLabel")
        self._radius_value = QLabel(f"{window.cfg.settings.get('corner_radius')}px")
        self._radius_value.setObjectName("opacityValue")
        self._radius_slider = QSlider(Qt.Orientation.Horizontal)
        self._radius_slider.setRange(8, 40)
        self._radius_slider.setValue(int(window.cfg.settings.get("corner_radius")))
        self._radius_slider.setFixedWidth(130)
        self._radius_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._radius_slider.valueChanged.connect(self._on_radius_changed)
        radius_row.addWidget(radius_label)
        radius_row.addStretch(1)
        radius_row.addWidget(self._radius_value)
        radius_row.addSpacing(8)
        radius_row.addWidget(self._radius_slider)
        v.addLayout(radius_row)

        hotkey_head = QLabel("全局快捷键")
        hotkey_head.setObjectName("settingLabel")
        v.addWidget(hotkey_head)

        show_hk_row = QHBoxLayout()
        show_hk_label = QLabel("唤起组件")
        show_hk_label.setObjectName("settingLabel")
        self._show_hotkey_edit = HotkeyEdit(lambda: window.cfg.colors, window.cfg.settings.get("show_hotkey"), self)
        self._show_hotkey_edit.hotkey_changed.connect(self._on_show_hotkey_changed)
        show_hk_row.addWidget(show_hk_label)
        show_hk_row.addStretch(1)
        show_hk_row.addWidget(self._show_hotkey_edit)
        v.addLayout(show_hk_row)

        new_hk_row = QHBoxLayout()
        new_hk_label = QLabel("新建待办")
        new_hk_label.setObjectName("settingLabel")
        self._new_hotkey_edit = HotkeyEdit(lambda: window.cfg.colors, window.cfg.settings.get("new_todo_hotkey"), self)
        self._new_hotkey_edit.hotkey_changed.connect(self._on_new_hotkey_changed)
        new_hk_row.addWidget(new_hk_label)
        new_hk_row.addStretch(1)
        new_hk_row.addWidget(self._new_hotkey_edit)
        v.addLayout(new_hk_row)

        self._github_btn = QPushButton("GitHub 项目仓库  ↗")
        self._github_btn.setObjectName("githubButton")
        self._github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._github_btn.clicked.connect(self._open_github)
        v.addWidget(self._github_btn)

        self._back_btn.clicked.connect(lambda: self._win.set_settings_open(False))

    def _make_switch(self, handler, default: bool) -> MaterialSwitch:
        switch = MaterialSwitch(lambda: self._win.cfg.colors, checked=default, parent=self)
        switch.toggled.connect(handler)
        return switch

    def set_radii_for_radius(self, radius: float):
        self.set_radius(radius)

    def sync_from_cfg(self):
        cfg = self._win.cfg
        pairs = [
            (self._theme_switch, cfg.settings.get("theme") == "dark"),
            (self._topmost_switch, cfg.settings.get("topmost")),
            (self._topbar_switch, cfg.settings.get("show_top_bar")),
            (self._lock_position_switch, cfg.settings.get("lock_position")),
            (self._lock_size_switch, cfg.settings.get("lock_size")),
            (self._autostart_switch, cfg.settings.get("autostart")),
            (self._tray_switch, cfg.settings.get("start_in_tray")),
            (self._close_tray_switch, cfg.settings.get("close_to_tray")),
        ]
        for switch, value in pairs:
            switch.blockSignals(True)
            switch.setChecked(value)
            switch.blockSignals(False)
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(int(cfg.settings.get("opacity")))
        self._opacity_slider.blockSignals(False)
        self._opacity_value.setText(f"{int(cfg.settings.get('opacity'))}%")
        self._radius_slider.blockSignals(True)
        self._radius_slider.setValue(int(cfg.settings.get("corner_radius")))
        self._radius_slider.blockSignals(False)
        self._radius_value.setText(f"{int(cfg.settings.get('corner_radius'))}px")
        self._show_hotkey_edit.set_hotkey(cfg.settings.get("show_hotkey"))
        self._new_hotkey_edit.set_hotkey(cfg.settings.get("new_todo_hotkey"))

    # ---- 设置回调 ----
    def _on_theme_changed(self, checked: bool):
        self._win.set_theme("dark" if checked else "light")

    def _on_topmost_changed(self, checked: bool):
        self._win.set_topmost(checked)

    def _on_topbar_changed(self, checked: bool):
        self._win.set_setting("show_top_bar", checked)
        self._win._update_top_bar_visibility()

    def _on_lock_position_changed(self, checked: bool):
        self._win.set_setting("lock_position", checked)

    def _on_lock_size_changed(self, checked: bool):
        self._win.set_setting("lock_size", checked)
        self._win._update_resize_cursor()

    def _on_autostart_changed(self, checked: bool):
        self._win.set_autostart(checked)

    def _on_start_tray_changed(self, checked: bool):
        self._win.set_setting("start_in_tray", checked)

    def _on_close_tray_changed(self, checked: bool):
        self._win.set_setting("close_to_tray", checked)

    def _on_opacity_changed(self, value: int):
        self._win.set_opacity(value)

    def _on_radius_changed(self, value: int):
        self._win.set_corner_radius(value)

    def _on_show_hotkey_changed(self, text: str):
        self._win.set_hotkey("show_hotkey", text)

    def _on_new_hotkey_changed(self, text: str):
        self._win.set_hotkey("new_todo_hotkey", text)

    def _open_github(self):
        QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))


# ---------------------------------------------------------------------------
# QSS
# ---------------------------------------------------------------------------

def build_qss(c: dict) -> str:
    return f"""
    * {{
        outline: none;
    }}
    QWidget {{
        background: transparent;
        color: {c['text']};
        font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Noto Sans SC", sans-serif;
        font-size: 13px;
    }}
    QToolTip {{
        background-color: {c['surface_solid']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 5px 8px;
    }}
    QLabel#topbarCount {{
        color: {c['text']};
        font-size: 13px;
        font-weight: 600;
    }}
    QLabel#mainTitle {{
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#sectionLabel {{
        font-size: 14px;
        font-weight: 600;
    }}
    QLabel#settingLabel {{
        color: {c['text']};
        font-size: 12px;
    }}
    QLabel#opacityValue {{
        color: {c['primary']};
        font-size: 12px;
        font-weight: 600;
        min-width: 36px;
    }}
    QLineEdit#todoInput {{
        background-color: {c['input']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 8px 14px;
        font-size: 13px;
        color: {c['text']};
        selection-background-color: {c['primary']};
    }}
    QLineEdit#todoInput:focus {{
        border: 1px solid {c['primary']};
        background-color: {c['surface_solid']};
    }}
    QLineEdit#editInput {{
        background-color: {c['surface_solid']};
        border: 1px solid {c['primary']};
        border-radius: 8px;
        padding: 6px 8px;
        color: {c['text']};
        font-size: 12px;
        selection-background-color: {c['primary']};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px 0 2px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['scroll']};
        border-radius: 3px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['primary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QFrame#todoRow {{
        background-color: {c['surface_alpha']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}
    QFrame#todoRow:hover {{
        background-color: {c['surface_hover_alpha']};
        border: 1px solid {c['border_strong']};
    }}
    QLabel#todoTitle {{
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton#githubButton {{
        background-color: {c['primary_soft']};
        color: {c['primary']};
        border: none;
        border-radius: 12px;
        padding: 8px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#githubButton:hover {{
        background-color: {c['primary']};
        color: {c['on_primary']};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c['track_off']};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {c['primary']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c['on_primary']};
        border: 2px solid {c['primary']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QMenu {{
        background-color: {c['surface_solid']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        background: transparent;
        padding: 7px 18px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {c['surface_hover']};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 6px;
    }}
    QMessageBox {{
        background-color: {c['surface_solid']};
    }}
    QMessageBox QLabel {{
        color: {c['text']};
    }}
    QMessageBox QPushButton {{
        background-color: {c['primary']};
        color: {c['on_primary']};
        border: none;
        border-radius: 8px;
        padding: 6px 16px;
        min-width: 60px;
    }}
    """


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------

class MainWindow(QWidget):
    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg
        self._really_quit = False
        self._tray_notice_shown = False
        self._tray_available = False
        self._tray: QSystemTrayIcon | None = None
        self._tray_theme: str | None = None
        self._geometry_save_timer = QTimer(self)
        self._geometry_save_timer.setSingleShot(True)
        self._geometry_save_timer.setInterval(450)
        self._geometry_save_timer.timeout.connect(self._save_geometry)
        self._effects_timer = QTimer(self)
        self._effects_timer.setSingleShot(True)
        self._effects_timer.setInterval(140)
        self._effects_timer.timeout.connect(self._apply_win_effects)

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setWindowFlags(flags)
        if cfg.settings.get("topmost"):
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setWindowIcon(_make_icon(cfg.colors))
        self.setMinimumSize(340, 460)
        self.setMaximumSize(560, 820)

        geometry = cfg.settings.get("geometry")
        if isinstance(geometry, list) and len(geometry) == 4:
            try:
                w = max(self.minimumWidth(), min(self.maximumWidth(), int(geometry[2])))
                h = max(self.minimumHeight(), min(self.maximumHeight(), int(geometry[3])))
                self.setGeometry(int(geometry[0]), int(geometry[1]), w, h)
            except (TypeError, ValueError):
                self.resize(400, 620)
        else:
            self.resize(400, 620)

        self._build_ui()
        self.apply_theme()
        self._setup_tray()
        self._restore_geometry_if_needed()
        self.setWindowOpacity(int(cfg.settings.get("opacity")) / 100.0)
        self._sync_controls()

        if cfg.settings.get("autostart"):
            ok, _ = set_autostart(True)
            if not ok:
                cfg.settings["autostart"] = False
                cfg.save_settings()
                self._sync_controls()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(WINDOW_OUTER_MARGIN, WINDOW_OUTER_MARGIN, WINDOW_OUTER_MARGIN, WINDOW_OUTER_MARGIN)
        outer.setSpacing(14)

        provider = lambda: self.cfg.colors

        self._top_bar = TopBar(self, provider)
        outer.addWidget(self._top_bar)

        self._main_panel = MainPanel(self, provider)
        self._settings = SettingsPanel(self)
        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._main_panel)   # 页面 0：待办视图
        self._stack.addWidget(self._settings)     # 页面 1：设置视图
        outer.addWidget(self._stack, 1)

        self._update_top_bar_visibility()

    # -------------------------------------------------------------- 主题
    def apply_theme(self):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_qss(self.cfg.colors))
        icon = _make_icon(self.cfg.colors)
        self.setWindowIcon(icon)
        if app:
            app.setWindowIcon(icon)
        self._update_radii()
        self._top_bar.update()
        self._main_panel.update()
        self._settings.update()
        self._sync_controls()
        self._rebuild_todos()
        if self.isVisible():
            self._effects_timer.start(0)

    def _update_radii(self):
        radius = float(self.cfg.settings.get("corner_radius", DEFAULT_CORNER_RADIUS))
        self._top_bar.set_radii_for_radius(radius)
        self._main_panel.set_radii_for_radius(radius)
        self._settings.set_radii_for_radius(radius)

    def toggle_theme(self):
        self.set_theme("light" if self.cfg.settings.get("theme") == "dark" else "dark")

    def set_theme(self, theme: str):
        if theme not in ("dark", "light"):
            return
        self.cfg.settings["theme"] = theme
        self.cfg.save_settings()
        self.apply_theme()

    # -------------------------------------------------------------- 设置
    def set_setting(self, key: str, value):
        self.cfg.settings[key] = value
        self.cfg.save_settings()
        self._sync_controls()

    def set_topmost(self, enabled: bool):
        self.set_setting("topmost", bool(enabled))
        self._apply_topmost_flag()

    def _apply_topmost_flag(self):
        wants = bool(self.cfg.settings.get("topmost"))
        has = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if wants == has:
            return
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, wants)
        if was_visible:
            self.show()
            self.setWindowOpacity(int(self.cfg.settings.get("opacity")) / 100.0)

    def set_opacity(self, value: int):
        value = max(40, min(100, int(value)))
        self.cfg.settings["opacity"] = value
        self.cfg.save_settings()
        self.setWindowOpacity(value / 100.0)
        self._sync_controls()

    def set_corner_radius(self, value: int):
        value = max(8, min(40, int(value)))
        self.cfg.settings["corner_radius"] = value
        self.cfg.save_settings()
        self._update_radii()
        if self.isVisible():
            self._effects_timer.start(0)
        self._sync_controls()

    def set_hotkey(self, key: str, text: str):
        self.cfg.settings[key] = str(text)
        self.cfg.save_settings()
        self._register_hotkeys()

    def set_autostart(self, enabled: bool):
        ok, error = set_autostart(bool(enabled))
        if ok:
            self.cfg.settings["autostart"] = bool(enabled)
            self.cfg.save_settings()
            self._sync_controls()
        else:
            self._sync_controls()
            if not self.isVisible():
                self.show_main_window()
            QMessageBox.warning(self, APP_DISPLAY_NAME, f"开机自启设置失败：\n{error}")

    def set_settings_open(self, open_: bool):
        self._stack.setCurrentIndex(1 if open_ else 0)
        if open_:
            self._settings.sync_from_cfg()
        for btn in (self._top_bar.settings_btn, self._main_panel.settings_btn):
            btn.blockSignals(True)
            btn.set_active(bool(open_))
            btn.blockSignals(False)
        if self.isVisible():
            self._effects_timer.start(0)

    def settings_open(self) -> bool:
        return self._stack.currentWidget() is self._settings

    def drag_locked(self) -> bool:
        return bool(self.cfg.settings.get("lock_position"))

    def _update_resize_cursor(self):
        locked = bool(self.cfg.settings.get("lock_size"))
        self._main_panel._grip.setCursor(
            Qt.CursorShape.ArrowCursor if locked else Qt.CursorShape.SizeFDiagCursor
        )

    def _update_top_bar_visibility(self):
        show = bool(self.cfg.settings.get("show_top_bar", True))
        self._top_bar.setVisible(show)
        self._main_panel.settings_btn.setVisible(not show)
        if self.isVisible():
            self._effects_timer.start(0)

    def _open_github(self):
        QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))

    # -------------------------------------------------------------- 待办
    def reveal_add_input(self):
        self.show_main_window()
        if self.settings_open():
            self.set_settings_open(False)
        self._main_panel.input.setFocus(Qt.FocusReason.OtherFocusReason)
        self._main_panel.input.selectAll()

    def _add_from_input(self):
        text = self._main_panel.input.text().strip()
        if not text:
            self._main_panel.input.setFocus()
            return
        self._add_todo_text(text)
        self._main_panel.input.clear()
        self._main_panel.input.setFocus()

    def _add_todo_text(self, text: str):
        text = text.strip()
        if not text:
            return
        todo = {
            "id": uuid.uuid4().hex[:14],
            "title": text,
            "done": False,
            "created_at": _now_iso(),
            "completed_at": None,
            "updated_at": _now_iso(),
        }
        self.cfg.todos.insert(0, todo)
        self.cfg.save_todos()
        self._rebuild_todos()
        self._main_panel.scroll.verticalScrollBar().setValue(0)

    def _sorted_todos(self):
        pending = [t for t in self.cfg.todos if not t.get("done")]
        completed = [t for t in self.cfg.todos if t.get("done")]
        pending.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        completed.sort(key=lambda t: t.get("completed_at", "") or t.get("created_at", ""), reverse=True)
        return pending + completed

    def _rebuild_todos(self):
        while self._main_panel.list_layout.count():
            item = self._main_panel.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        todos = self._sorted_todos()
        for todo in todos:
            row = TodoRow(todo, lambda: self.cfg.colors)
            row.toggled.connect(self._on_row_toggled)
            row.edit_requested.connect(self._on_row_edited)
            row.delete_requested.connect(self._on_row_deleted)
            self._main_panel.list_layout.addWidget(row)
        self._main_panel.list_layout.addStretch(1)
        self._refresh_summary()

    def _on_row_toggled(self, todo_id: str, done: bool):
        QTimer.singleShot(0, lambda: self._apply_toggle(todo_id, done))

    def _apply_toggle(self, todo_id: str, done: bool):
        for todo in self.cfg.todos:
            if todo.get("id") == todo_id:
                todo["done"] = bool(done)
                todo["completed_at"] = _now_iso() if done else None
                todo["updated_at"] = _now_iso()
                break
        self.cfg.save_todos()
        self._rebuild_todos()

    def _on_row_edited(self, todo_id: str, title: str):
        for todo in self.cfg.todos:
            if todo.get("id") == todo_id:
                todo["title"] = title
                todo["updated_at"] = _now_iso()
                break
        self.cfg.save_todos()
        self._refresh_summary()

    def _on_row_deleted(self, todo_id: str):
        QTimer.singleShot(0, lambda: self._apply_delete(todo_id))

    def _apply_delete(self, todo_id: str):
        self.cfg.todos = [t for t in self.cfg.todos if t.get("id") != todo_id]
        self.cfg.save_todos()
        self._rebuild_todos()

    def mark_all_done(self):
        if not self.cfg.todos:
            return
        changed = False
        for todo in self.cfg.todos:
            if not todo.get("done"):
                todo["done"] = True
                todo["completed_at"] = _now_iso()
                todo["updated_at"] = _now_iso()
                changed = True
        if changed:
            self.cfg.save_todos()
            self._rebuild_todos()

    def clear_completed(self):
        if not any(t.get("done") for t in self.cfg.todos):
            return
        self.cfg.todos = [t for t in self.cfg.todos if not t.get("done")]
        self.cfg.save_todos()
        self._rebuild_todos()

    def _refresh_summary(self):
        total = len(self.cfg.todos)
        done = sum(1 for t in self.cfg.todos if t.get("done"))
        pending = total - done
        self._top_bar.update_count(pending)
        self._settings.sync_from_cfg()

    # -------------------------------------------------------------- 控件同步
    def _sync_controls(self):
        self._refresh_summary()
        self._update_resize_cursor()
        self._sync_tray()

    # -------------------------------------------------------------- 托盘
    def has_tray(self) -> bool:
        return self._tray_available

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_available = False
            return
        self._tray_available = True
        self._tray = QSystemTrayIcon(_make_icon(self.cfg.colors), self)
        self._tray.setToolTip(APP_DISPLAY_NAME)
        self._tray_menu = QMenu()

        self._tray_show_action = QAction("显示主窗口", self._tray_menu)
        self._tray_show_action.triggered.connect(self.show_main_window)
        self._tray_menu.addAction(self._tray_show_action)

        self._tray_add_action = QAction("新建待办", self._tray_menu)
        self._tray_add_action.triggered.connect(self._focus_new_todo)
        self._tray_menu.addAction(self._tray_add_action)

        self._tray_menu.addSeparator()

        self._tray_topmost_action = QAction("窗口置顶", self._tray_menu)
        self._tray_topmost_action.setCheckable(True)
        self._tray_topmost_action.triggered.connect(self.set_topmost)
        self._tray_menu.addAction(self._tray_topmost_action)

        self._tray_autostart_action = QAction("开机自启", self._tray_menu)
        self._tray_autostart_action.setCheckable(True)
        self._tray_autostart_action.triggered.connect(self.set_autostart)
        self._tray_menu.addAction(self._tray_autostart_action)

        self._tray_github_action = QAction("GitHub 项目仓库", self._tray_menu)
        self._tray_github_action.triggered.connect(self._open_github)
        self._tray_menu.addAction(self._tray_github_action)

        self._tray_menu.addSeparator()
        self._tray_quit_action = QAction("退出", self._tray_menu)
        self._tray_quit_action.triggered.connect(self._quit_app)
        self._tray_menu.addAction(self._tray_quit_action)

        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.show_main_window()

    def _sync_tray(self):
        if self._tray is None:
            return
        if self._tray_theme != self.cfg.settings.get("theme"):
            self._tray.setIcon(_make_icon(self.cfg.colors))
            self._tray_theme = self.cfg.settings.get("theme")
        self._tray_topmost_action.blockSignals(True)
        self._tray_topmost_action.setChecked(bool(self.cfg.settings.get("topmost")))
        self._tray_topmost_action.blockSignals(False)
        self._tray_autostart_action.blockSignals(True)
        self._tray_autostart_action.setChecked(bool(self.cfg.settings.get("autostart")))
        self._tray_autostart_action.blockSignals(False)

    def show_main_window(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowOpacity(int(self.cfg.settings.get("opacity")) / 100.0)

    def _focus_new_todo(self):
        self.reveal_add_input()

    def _toggle_visible_from_hotkey(self):
        if self.isVisible() and not self.isMinimized():
            self.hide_to_tray()
        else:
            self.show_main_window()

    def hide_to_tray(self):
        if self._tray_available:
            self._save_geometry()
            self.hide()
            if not self._tray_notice_shown:
                self._tray.showMessage(
                    APP_DISPLAY_NAME,
                    "应用仍在系统托盘运行。\n双击托盘图标可重新打开窗口。",
                    QSystemTrayIcon.MessageIcon.Information,
                    2200,
                )
                self._tray_notice_shown = True
            return True
        return False

    def minimize_or_tray(self):
        if not self.hide_to_tray():
            self.showMinimized()

    def _quit_app(self):
        self._really_quit = True
        self._save_geometry()
        self._unregister_hotkeys()
        if self._tray is not None:
            self._tray.hide()
        QApplication.instance().quit()

    # -------------------------------------------------------------- 热键
    def _register_hotkeys(self):
        if not _is_native_windows():
            return
        hwnd = int(self.winId())
        self._unregister_hotkeys()
        register_hotkey(hwnd, HOTKEY_ID_SHOW, self.cfg.settings.get("show_hotkey"))
        register_hotkey(hwnd, HOTKEY_ID_NEW_TODO, self.cfg.settings.get("new_todo_hotkey"))

    def _unregister_hotkeys(self):
        if not _is_native_windows():
            return
        try:
            hwnd = int(self.winId())
            unregister_hotkey(hwnd, HOTKEY_ID_SHOW)
            unregister_hotkey(hwnd, HOTKEY_ID_NEW_TODO)
        except Exception:
            pass

    # -------------------------------------------------------------- 窗口事件
    def _restore_geometry_if_needed(self):
        geometry = self.cfg.settings.get("geometry")
        if isinstance(geometry, list) and len(geometry) == 4:
            try:
                w = max(self.minimumWidth(), min(self.maximumWidth(), int(geometry[2])))
                h = max(self.minimumHeight(), min(self.maximumHeight(), int(geometry[3])))
                self.setGeometry(int(geometry[0]), int(geometry[1]), w, h)
            except (TypeError, ValueError):
                pass
        self._ensure_window_visible()

    def _ensure_window_visible(self):
        frame = self.frameGeometry()
        for screen in QGuiApplication.screens():
            avail = screen.availableGeometry()
            intersection = frame.intersected(avail)
            if intersection.width() >= 120 and intersection.height() >= 80:
                return
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            x = avail.x() + max(0, (avail.width() - self.width()) // 2)
            y = avail.y() + max(0, (avail.height() - self.height()) // 2)
            self.move(x, y)

    def _save_geometry(self):
        self.cfg.settings["geometry"] = [self.x(), self.y(), self.width(), self.height()]
        self.cfg.save_settings()

    def _build_panel_region(self):
        """返回所有可见圆角面板的并集 HRGN（物理像素）。"""
        dpr = self.devicePixelRatioF()
        radius = float(self.cfg.settings.get("corner_radius", DEFAULT_CORNER_RADIUS))
        candidates = []
        if self._top_bar.isVisible():
            candidates.append((self._top_bar, min(radius, 18.0)))
        current = self._stack.currentWidget()
        candidates.append((current, radius))
        rects = []
        for panel, r in candidates:
            if not panel.isVisible():
                continue
            pos = panel.mapTo(self, QPoint(0, 0))
            w = round(panel.width() * dpr)
            h = round(panel.height() * dpr)
            if w <= 0 or h <= 0:
                continue
            rects.append((round(pos.x() * dpr), round(pos.y() * dpr), w, h, round(r * dpr)))
        return _make_rounded_region(rects)

    def _apply_win_effects(self):
        if not (_is_native_windows() and self.isVisible()):
            return
        try:
            region = self._build_panel_region()
            if not region:
                return
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            # 1) 窗口形状裁剪为各圆角面板的并集：圆角外与中间空隙完全透明，点击可穿透
            user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
            user32.SetWindowRgn.restype = ctypes.c_int
            if not user32.SetWindowRgn(wintypes.HWND(hwnd), region, 1):
                gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
                gdi32.DeleteObject.restype = wintypes.BOOL
                gdi32.DeleteObject(region)
                return
            # 2) 仅在面板区域做磨砂模糊（region 已被系统接管，此处仅引用）
            WindowsEffects.apply_region_blur(hwnd, region)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._effects_timer.start(0)

    def closeEvent(self, event: QCloseEvent):
        if self._really_quit:
            self._save_geometry()
            event.accept()
            return
        if self.cfg.settings.get("close_to_tray") and self.hide_to_tray():
            event.ignore()
            return
        self._save_geometry()
        self._unregister_hotkeys()
        event.accept()
        QApplication.instance().quit()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._geometry_save_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._geometry_save_timer.start()
        if self.isVisible():
            self._effects_timer.start()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self._main_panel.input.clear()
            self._main_panel.input.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    def nativeEvent(self, event_type, message):
        if _is_native_windows():
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    if int(msg.wParam) == HOTKEY_ID_SHOW:
                        self._toggle_visible_from_hotkey()
                    elif int(msg.wParam) == HOTKEY_ID_NEW_TODO:
                        self._focus_new_todo()
                    return True, 0
            except Exception:
                pass
        return super().nativeEvent(event_type, message)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> int:
    _set_windows_app_id()
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    raw_argv = list(sys.argv)
    force_show = "--show" in raw_argv
    start_hidden = ("--hidden" in raw_argv or "--tray" in raw_argv) and not force_show
    argv = [a for a in raw_argv if a not in ("--hidden", "--tray", "--show")]

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    # 单实例检测：已有实例在运行时，把本次启动意图转发过去并退出本实例
    if _notify_existing_instance(raw_argv):
        return 0

    guard = SingleInstanceServer()
    if not guard.listen():
        # 竞态下另一实例抢先监听：再通知一次并退出
        _notify_existing_instance(raw_argv)
        return 0

    cfg = Config()
    if cfg.settings.get("start_in_tray") and not force_show:
        start_hidden = True

    window = MainWindow(cfg)
    guard.setParent(window)
    guard.show_requested.connect(window.show_main_window)
    window._sync_tray()
    if _is_native_windows():
        window._register_hotkeys()

    if start_hidden and not window._tray_available:
        start_hidden = False

    if not start_hidden:
        window.show()
    else:
        pass

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
