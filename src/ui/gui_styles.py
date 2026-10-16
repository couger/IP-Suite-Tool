"""统一的GUI样式配置模块

提供所有GUI组件的样式常量和辅助函数，确保界面风格一致性。

作者: IP-Suite-Tool Team
版本: 4.0
"""

import tkinter as tk
from tkinter import ttk


# ==================== 颜色常量 ====================
class Colors:
    """应用程序颜色方案"""

    # 主色调 - 蓝色系
    PRIMARY = "#007acc"
    PRIMARY_LIGHT = "#1a8cff"
    PRIMARY_DARK = "#005fa3"

    # 背景色
    BG_LIGHT = "#f5f5f5"
    BG_WHITE = "#ffffff"
    BG_GRAY = "#e8e8e8"
    BG_DISABLED = "#f0f0f0"

    # 文本颜色
    TEXT_PRIMARY = "#333333"
    TEXT_SECONDARY = "#666666"
    TEXT_HINT = "#999999"
    TEXT_WHITE = "#ffffff"

    # 状态颜色
    SUCCESS = "#28a745"
    WARNING = "#ffc107"
    ERROR = "#dc3545"
    INFO = "#17a2b8"

    # 边框颜色
    BORDER_NORMAL = "#cccccc"
    BORDER_ERROR = "#ff0000"
    BORDER_FOCUS = "#007acc"


# ==================== 字体常量 ====================
class Fonts:
    """应用程序字体配置"""

    # Microsoft YaHei UI - Windows推荐中文字体
    TITLE = ("Microsoft YaHei UI", 12, "bold")
    HEADING = ("Microsoft YaHei UI", 10, "bold")
    BODY = ("Microsoft YaHei UI", 9)
    SMALL = ("Microsoft YaHei UI", 8)
    MONOSPACE = ("Consolas", 9)


# ==================== 尺寸常量 ====================
class Dimensions:
    """常用UI元素尺寸"""

    # 输入框宽度
    INPUT_WIDTH_SMALL = 15
    INPUT_WIDTH_MEDIUM = 25
    INPUT_WIDTH_LARGE = 40

    # 按钮尺寸
    BUTTON_HEIGHT = 28
    BUTTON_WIDTH = 100

    # 间距
    PADDING_TIGHT = 3
    PADDING_NORMAL = 6
    PADDING_SPACIOUS = 10
    PADDING_LARGE = 15

    # 组件高度
    TREEVIEW_HEIGHT = 8
    TEXTAREA_HEIGHT = 12


# ==================== 样式配置函数 ====================
def configure_styles(style: ttk.Style) -> None:
    """配置所有ttk样式"""

    # 按钮样式
    style.configure(
        "Primary.TButton",
        foreground=Colors.TEXT_WHITE,
        background=Colors.PRIMARY,
        padding=(10, 5),
    )
    style.map(
        "Primary.TButton",
        background=[("active", Colors.PRIMARY_LIGHT), ("pressed", Colors.PRIMARY_DARK)],
    )

    # Accent按钮（用于主要操作）
    style.configure(
        "Accent.TButton",
        foreground=Colors.TEXT_WHITE,
        background=Colors.PRIMARY,
        padding=(10, 5),
    )

    style.configure(
        "Green.Horizontal.TProgressbar",
        troughcolor=Colors.BG_GRAY,
        background=Colors.SUCCESS,
        lightcolor="#34ce57",
        darkcolor="#1e7e34",
    )

    # 标签样式
    style.configure("Title.TLabel", font=Fonts.TITLE)
    style.configure("Heading.TLabel", font=Fonts.HEADING)
    style.configure("Body.TLabel", font=Fonts.BODY)

    # Frame样式
    style.configure(
        "Primary.TFrame", background=Colors.BG_LIGHT, relief=tk.GROOVE, borderwidth=1
    )

    # LabelFrame样式
    style.configure(
        "Primary.TLabelframe.Label", font=Fonts.HEADING, foreground=Colors.TEXT_PRIMARY
    )


def create_ttk_button(
    parent, text: str, command=None, style: str = "Accent.TButton", **kwargs
) -> ttk.Button:
    """创建统一样式的按钮"""
    btn_kwargs = {
        "master": parent,
        "text": text,
        "command": command,
        "style": style,
        "padding": (10, 3),
        **kwargs,
    }
    return ttk.Button(**btn_kwargs)


def create_ttk_label(
    parent, text: str, font: tuple = None, foreground: str = None, **kwargs
) -> tk.Label:
    """创建统一样式的标签"""
    label_kwargs = {
        "master": parent,
        "text": text,
        "font": font or Fonts.BODY,
        "foreground": foreground or Colors.TEXT_PRIMARY,
        **kwargs,
    }
    return tk.Label(**label_kwargs)


def create_ttk_entry(parent, width: int = 20, style: str = None, **kwargs) -> ttk.Entry:
    """创建统一样式的输入框"""
    entry_kwargs = {"master": parent, "width": width, **kwargs}
    if style:
        entry_kwargs["style"] = style
    return ttk.Entry(**entry_kwargs)


def create_ttk_combobox(
    parent, values: list = None, state: str = "readonly", width: int = 20, **kwargs
) -> ttk.Combobox:
    """创建统一样式的下拉框"""
    combo_kwargs = {
        "master": parent,
        "values": values or [],
        "state": state,
        "width": width,
        **kwargs,
    }
    return ttk.Combobox(**combo_kwargs)


def create_ttk_frame(
    parent, relief: str = tk.GROOVE, borderwidth: int = 1, padding: int = 10, **kwargs
) -> ttk.Frame:
    """创建统一样式的框架"""
    frame_kwargs = {
        "master": parent,
        "relief": relief,
        "borderwidth": borderwidth,
        "padding": padding,
        **kwargs,
    }
    return ttk.Frame(**frame_kwargs)


def create_ttk_labelframe(
    parent, text: str, padding: int = 6, **kwargs
) -> ttk.LabelFrame:
    """创建统一样式的标签框架"""
    frame_kwargs = {"master": parent, "text": text, "padding": padding, **kwargs}
    return ttk.LabelFrame(**frame_kwargs)


def create_treeview(
    parent, columns: tuple = None, height: int = 8, **kwargs
) -> ttk.Treeview:
    """创建统一样式的Treeview"""
    tree_kwargs = {
        "master": parent,
        "columns": columns or (),
        "show": "headings",
        "height": height,
        **kwargs,
    }
    return ttk.Treeview(**tree_kwargs)


def create_text_widget(parent, width: int = 40, height: int = 12, **kwargs) -> tk.Text:
    """创建统一样式的文本框"""
    text_kwargs = {
        "master": parent,
        "width": width,
        "height": height,
        "font": Fonts.MONOSPACE,
        "bg": Colors.BG_WHITE,
        **kwargs,
    }
    return tk.Text(**text_kwargs)


def create_progressbar(
    parent, mode: str = "determinate", maximum: int = 100, **kwargs
) -> ttk.Progressbar:
    """创建统一样式的进度条"""
    progress_kwargs = {
        "master": parent,
        "mode": mode,
        "maximum": maximum,
        "length": 300,
        **kwargs,
    }
    return ttk.Progressbar(**progress_kwargs)
