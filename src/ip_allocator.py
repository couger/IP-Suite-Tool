"""IP地址分配模块，提供IP地址分配和管理功能

Author: IP-Suite-Tool Team
Date: 2026-02-28
Version: 4.0
"""

import datetime
import json
import logging
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional, Union

import openpyxl

from ui.gui_styles import Colors, Fonts
from utils.app_paths import config_path
from utils.table_schema import read_display_table

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = str(config_path("ip_allocator_config.json"))
CONFIG_DIR = os.path.dirname(CONFIG_FILE)


class DragDropFrame(tk.Frame):
    """支持拖拽上传的Frame组件"""

    def __init__(self, parent: tk.Widget, title: str, file_types: list,
                 on_drop_callback: Callable[[str], None], **kwargs) -> None:
        """初始化拖拽上传区域

        Args:
            parent: 父容器
            title: 区域标题
            file_types: 文件类型限制，如 [("图片文件", "*.png *.jpg *.jpeg")]
            on_drop_callback: 文件选择后的回调函数
        """
        super().__init__(parent, **kwargs)
        self.file_types = file_types
        self.on_drop_callback = on_drop_callback
        self.selected_file = None

        self._setup_ui(title)

    def _setup_ui(self, title: str) -> None:
        """设置UI"""
        # 配置边框样式
        self.configure(
            relief=tk.GROOVE,
            borderwidth=2,
            bg=Colors.BG_WHITE,
            highlightthickness=1,
            highlightbackground=Colors.BORDER_NORMAL,
            cursor='hand2'
        )

        # 标题
        title_label = tk.Label(
            self,
            text=title,
            font=Fonts.HEADING,
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_WHITE
        )
        title_label.pack(pady=(8, 4))

        # 提示文本
        self.hint_label = tk.Label(
            self,
            text="点击选择文件或拖拽文件到此处",
            font=Fonts.BODY,
            fg=Colors.TEXT_SECONDARY,
            bg=Colors.BG_WHITE
        )
        self.hint_label.pack(pady=2)

        # 文件名显示
        self.file_label = tk.Label(
            self,
            text="未选择文件",
            font=Fonts.BODY,
            fg=Colors.TEXT_PRIMARY,
            bg=Colors.BG_WHITE,
            wraplength=200
        )
        self.file_label.pack(pady=2, padx=8)

        # 选择按钮
        self.select_btn = tk.Button(
            self,
            text="选择文件",
            command=self._select_file,
            font=Fonts.BODY,
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_WHITE,
            activebackground=Colors.PRIMARY_LIGHT,
            activeforeground=Colors.TEXT_WHITE,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.select_btn.pack(pady=(6, 8))

        # 绑定点击事件
        self.bind('<Button-1>', lambda e: self._select_file())
        title_label.bind('<Button-1>', lambda e: self._select_file())
        self.hint_label.bind('<Button-1>', lambda e: self._select_file())
        self.file_label.bind('<Button-1>', lambda e: self._select_file())

        # 绑定拖拽事件（模拟拖拽效果）
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _select_file(self) -> None:
        """选择文件"""
        # 检查是否启用
        if not self.is_enabled():
            return
        file_path = filedialog.askopenfilename(filetypes=self.file_types)
        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename, fg=Colors.PRIMARY)
            self.hint_label.config(text="已选择文件")
            if self.on_drop_callback:
                self.on_drop_callback(file_path)

    def _on_enter(self, _event: tk.Event) -> None:
        """鼠标进入事件"""
        if self.is_enabled():
            self.configure(bg="#eaf5ff", highlightbackground=Colors.PRIMARY)
            for child in self.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg="#eaf5ff")

    def _on_leave(self, _event: tk.Event) -> None:
        """鼠标离开事件"""
        if self.is_enabled():
            self.configure(bg=Colors.BG_WHITE, highlightbackground=Colors.BORDER_NORMAL)
            for child in self.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=Colors.BG_WHITE)

    def get_file(self) -> Optional[str]:
        """获取选中的文件路径"""
        return self.selected_file

    def clear(self) -> None:
        """清空选择"""
        self.selected_file = None
        self.file_label.config(text="未选择文件", fg=Colors.TEXT_PRIMARY)
        self.hint_label.config(text="点击选择文件或拖拽文件到此处")

    def set_enabled(self, enabled: bool) -> None:
        """设置启用/禁用状态

        Args:
            enabled: True启用，False禁用
        """
        self._enabled = enabled
        if enabled:
            self.configure(
                bg=Colors.BG_WHITE,
                cursor='hand2',
                highlightbackground=Colors.BORDER_NORMAL,
            )
            for child in self.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=Colors.BG_WHITE)
            self.hint_label.config(text="点击选择文件或拖拽文件到此处", fg=Colors.TEXT_SECONDARY)
            self.select_btn.config(state=tk.NORMAL)
        else:
            self.configure(
                bg=Colors.BG_DISABLED,
                cursor='arrow',
                highlightbackground=Colors.BG_GRAY,
            )
            for child in self.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=Colors.BG_DISABLED)
            self.hint_label.config(text="请先完成前置配置", fg=Colors.TEXT_HINT)
            self.select_btn.config(state=tk.DISABLED)

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return getattr(self, '_enabled', True)


class IPPlanDialog(tk.Toplevel):
    """IP规划表编辑对话框（三级页面）"""

    def __init__(self, parent: Union[tk.Tk, tk.Widget],
                 ip_plan_file: Optional[str] = None) -> None:
        """初始化IP规划表对话框

        Args:
            parent: 父窗口
            ip_plan_file: IP规划表文件路径（可选）
        """
        super().__init__(parent)
        self.parent = parent
        self.ip_plan_file = ip_plan_file
        self.plan_columns: list = []

        self.title("IP地址规划")
        self.geometry("1000x600")
        self.transient(parent)  # type: ignore[arg-type]
        self.grab_set()

        self._setup_ui()

        # 如果有文件路径，自动加载
        if ip_plan_file and os.path.exists(ip_plan_file):
            self._load_and_display_ip_plan(ip_plan_file)

    def _setup_ui(self) -> None:
        """设置UI"""
        # 主容器
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="IP地址规划表",
            font=('Microsoft YaHei UI', 14, 'bold')
        )
        title_label.pack(pady=(0, 10))

        # 文件选择区域
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Label(file_frame, text="文件：").pack(side=tk.LEFT)
        self.file_label = ttk.Label(
            file_frame, text="未选择", foreground='gray')
        self.file_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="选择文件",
                   command=self._select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="加载",
                   command=self._load_file).pack(side=tk.LEFT, padx=5)

        # 提示标签
        self.hint_label = ttk.Label(
            main_frame, text="请选择IP地址规划表文件", foreground='gray')
        self.hint_label.pack(pady=5)

        # 操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.add_btn = tk.Button(
            button_frame, text="新增", command=self._add_row,
            font=('Microsoft YaHei UI', 9), bg='#28a745', fg='white',
            relief=tk.FLAT, width=8, cursor='hand2'
        )
        self.add_btn.pack(side=tk.LEFT, padx=5)

        self.edit_btn = tk.Button(
            button_frame, text="编辑", command=self._edit_row,
            font=('Microsoft YaHei UI', 9), bg='#ffc107', fg='black',
            relief=tk.FLAT, width=8, cursor='hand2', state=tk.DISABLED
        )
        self.edit_btn.pack(side=tk.LEFT, padx=5)

        self.delete_btn = tk.Button(
            button_frame, text="删除", command=self._delete_row,
            font=('Microsoft YaHei UI', 9), bg='#dc3545', fg='white',
            relief=tk.FLAT, width=8, cursor='hand2', state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(
            button_frame, text="保存到文件", command=self._save_to_file,
            font=('Microsoft YaHei UI', 9), bg='#007acc', fg='white',
            relief=tk.FLAT, width=10, cursor='hand2', state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.RIGHT, padx=5)

        # Treeview容器
        tree_container = ttk.Frame(main_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=10)

        self.plan_tree = ttk.Treeview(
            tree_container, columns=[], show='headings', height=20)
        self.plan_tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        tree_scroll_y = ttk.Scrollbar(
            tree_container, orient=tk.VERTICAL, command=self.plan_tree.yview)
        tree_scroll_x = ttk.Scrollbar(
            tree_container, orient=tk.HORIZONTAL, command=self.plan_tree.xview)
        self.plan_tree.configure(
            yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.plan_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # 关闭按钮
        close_frame = ttk.Frame(main_frame)
        close_frame.pack(fill=tk.X, pady=10)
        ttk.Button(close_frame, text="关闭", command=self.destroy).pack(
            side=tk.RIGHT, padx=5)

    def _select_file(self) -> None:
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择IP地址规划表",
            filetypes=[("Excel文件", "*.xlsx *.xls")]
        )
        if file_path:
            self.ip_plan_file = file_path
            self.file_label.config(text=os.path.basename(file_path),
                                   foreground='green')

    def _load_file(self) -> None:
        """加载文件"""
        if self.ip_plan_file and os.path.exists(self.ip_plan_file):
            self._load_and_display_ip_plan(self.ip_plan_file)
        else:
            messagebox.showwarning("警告", "请先选择文件")

    def _load_and_display_ip_plan(self, file_path: str) -> None:
        """Read the public table contract, independent of worksheet/site names."""
        try:
            columns, records = read_display_table(file_path)
            for item in self.plan_tree.get_children():
                self.plan_tree.delete(item)
            self._update_tree_columns(columns)
            for values in records:
                self.plan_tree.insert('', tk.END, values=values)
            self.hint_label.config(text=f"已加载 {len(records)} 条记录", foreground=Colors.SUCCESS)
        except Exception as error:
            logger.error("读取表格失败", exc_info=True)
            self.hint_label.config(text=f"读取失败: {error}", foreground=Colors.ERROR)
            messagebox.showerror("错误", f"读取表格失败: {error}")

    def _update_tree_columns(self, columns: list) -> None:
        """更新Treeview列定义"""
        self.plan_columns = columns
        self.plan_tree['columns'] = columns

        for col in columns:
            self.plan_tree.heading(col, text=col)
            width = max(80, len(col) * 12)
            self.plan_tree.column(col, width=width, anchor='center')

    def _on_tree_select(self, _event: tk.Event) -> None:
        """选择事件处理"""
        selected = self.plan_tree.selection()
        if selected:
            self.edit_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        else:
            self.edit_btn.config(state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)

    def _add_row(self) -> None:
        """新增行"""
        if not self.plan_columns:
            messagebox.showwarning("警告", "请先加载IP规划表")
            return
        self._show_edit_dialog(None)

    def _edit_row(self) -> None:
        """编辑行"""
        selected = self.plan_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要编辑的行")
            return

        item = selected[0]
        values = self.plan_tree.item(item, 'values')
        if values == '':
            values = None
        self._show_edit_dialog(item, values)

    def _delete_row(self) -> None:
        """删除行"""
        selected = self.plan_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的行")
            return

        if messagebox.askyesno("确认", "确定要删除选中的行吗？"):
            for item in selected:
                self.plan_tree.delete(item)
            logger.info(f"已删除 {len(selected)} 行数据")
            self._update_record_count()
            self.save_btn.config(state=tk.NORMAL)

    def _show_edit_dialog(self, item_id: Optional[str],
                          values: Optional[tuple] = None) -> None:
        """显示编辑对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("新增数据" if item_id is None else "编辑数据")
        dialog.geometry("600x400")
        dialog.transient(self)  # type: ignore[arg-type]
        dialog.grab_set()

        input_frame = ttk.Frame(dialog, padding="10")
        input_frame.pack(fill=tk.BOTH, expand=True)

        entries = {}

        for i, col in enumerate(self.plan_columns):
            row_frame = ttk.Frame(input_frame)
            row_frame.pack(fill=tk.X, pady=3)

            ttk.Label(row_frame, text=f"{col}:", width=15,
                      anchor='e').pack(side=tk.LEFT, padx=5)

            entry = ttk.Entry(row_frame, width=40)
            entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

            if values and i < len(values):
                entry.insert(0, str(values[i]) if values[i] else '')

            entries[col] = entry

        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)

        def on_save() -> None:
            row_data = [entries[col].get() for col in self.plan_columns]

            if item_id is None:
                self.plan_tree.insert('', tk.END, values=row_data)
                logger.info("新增一行数据")
            else:
                self.plan_tree.item(item_id, values=row_data)
                logger.info("更新一行数据")

            self._update_record_count()
            self.save_btn.config(state=tk.NORMAL)
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        ttk.Button(button_frame, text="保存", command=on_save).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(
            side=tk.LEFT, padx=10)

        dialog.update_idletasks()
        x = dialog.winfo_x() + (dialog.winfo_width() - 600) // 2
        y = dialog.winfo_y() + (dialog.winfo_height() - 400) // 2
        dialog.geometry(f"+{x}+{y}")

    def _update_record_count(self) -> None:
        """更新记录数量"""
        row_count = len(self.plan_tree.get_children())
        self.hint_label.config(text=f"共 {row_count} 条记录", foreground='green')

    def _save_to_file(self) -> None:
        """保存到文件"""
        if not self.plan_columns:
            messagebox.showwarning("警告", "没有数据可保存")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存IP规划表",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx")]
        )

        if not file_path:
            return

        try:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            if sheet is None:
                raise ValueError("无法创建工作表")
            sheet.title = "IP规划表"

            for col_idx, col_name in enumerate(self.plan_columns, 1):
                sheet.cell(row=1, column=col_idx, value=col_name)

            for row_idx, item in enumerate(
                    self.plan_tree.get_children(), 2):
                values = self.plan_tree.item(item, 'values')
                for col_idx, value in enumerate(values, 1):
                    sheet.cell(row=row_idx, column=col_idx, value=value)

            workbook.save(file_path)
            logger.info(f"数据已保存到: {file_path}")
            messagebox.showinfo("成功", f"数据已保存到:\n{file_path}")
            self.save_btn.config(state=tk.DISABLED)

        except Exception as e:
            logger.error(f"保存文件失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")


class IPAllocator:
    """IP地址分配工具类，负责IP地址的分配和管理"""

    def __init__(self, parent: Union[tk.Tk, tk.Widget]) -> None:
        """初始化IP地址分配工具

        Args:
            parent: 父容器组件
        """
        self.parent = parent

        # 存储文件对象
        self.ip_plan_file = None  # IP地址规划表
        self.ip_allocation_file = None  # IP地址分配总表
        self.record_directory = None  # IP地址分配记录目录
        self.image_file = None  # 图片文件
        self.application_file = None  # IP地址申请表

        # 申请表列定义
        self.application_columns: list = []

        self._setup_ui()

        # 加载保存的配置
        self._load_config()

        logger.info("IP地址分配工具初始化完成")

    def _configure_allocator_styles(self) -> None:
        """配置IP地址分配页的局部样式。"""
        style = ttk.Style()
        style.configure(
            "AllocatorTitle.TLabel",
            font=("Microsoft YaHei UI", 15, "bold"),
            foreground=Colors.TEXT_PRIMARY,
        )
        style.configure(
            "AllocatorPanelTitle.TLabel",
            font=("Microsoft YaHei UI", 12, "bold"),
            foreground=Colors.TEXT_PRIMARY,
        )
        style.configure(
            "AllocatorField.TLabel",
            font=Fonts.HEADING,
            foreground=Colors.TEXT_SECONDARY,
        )
        style.configure(
            "AllocatorMuted.TLabel",
            font=Fonts.BODY,
            foreground=Colors.TEXT_HINT,
        )

    def _setup_ui(self) -> None:
        """设置用户界面"""
        self._configure_allocator_styles()

        # 主容器 - 使用PanedWindow实现左右分栏
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # ===== 左侧面板：配置区域 =====
        left_frame = ttk.Frame(main_paned, padding=(12, 10))
        main_paned.add(left_frame, weight=1)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)

        title_row = ttk.Frame(left_frame)
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        title_row.columnconfigure(0, weight=1)
        ttk.Label(
            title_row,
            text="IP地址分配（实验：资料归档）",
            style="AllocatorTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(
            title_row,
            text="请先选择IP地址规划表",
            style="AllocatorMuted.TLabel",
        )
        self.status_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ===== 第一部分：基础配置 =====
        config_frame = ttk.LabelFrame(left_frame, text="基础配置", padding=(12, 8))
        config_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="IP地址规划表", style="AllocatorField.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.plan_label = ttk.Label(config_frame, text="未选择", style="AllocatorMuted.TLabel")
        self.plan_label.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(config_frame, text="选择", command=self._select_ip_plan).grid(
            row=0, column=2, sticky="e", pady=4
        )

        # IP地址规划按钮
        self.plan_btn = tk.Button(
            config_frame,
            text="IP地址规划",
            command=self._open_ip_plan_dialog,
            font=Fonts.BODY,
            bg=Colors.INFO,
            fg=Colors.TEXT_WHITE,
            activebackground="#21bfd8",
            activeforeground=Colors.TEXT_WHITE,
            relief=tk.FLAT,
            width=12,
            height=1,
            cursor='hand2',
            state=tk.DISABLED  # 初始禁用，选择规划表后启用
        )
        self.plan_btn.grid(row=0, column=3, sticky="e", padx=(8, 0), pady=4)

        # IP地址分配总表
        ttk.Label(config_frame, text="IP地址分配总表", style="AllocatorField.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.allocation_label = ttk.Label(config_frame, text="未选择", style="AllocatorMuted.TLabel")
        self.allocation_label.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 8), pady=4)
        self.allocation_btn = ttk.Button(
            config_frame,
            text="选择",
            command=self._select_ip_allocation,
            state=tk.DISABLED,
        )
        self.allocation_btn.grid(row=1, column=3, sticky="e", padx=(8, 0), pady=4)

        # IP地址分配记录目录
        ttk.Label(config_frame, text="分配记录目录", style="AllocatorField.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.directory_label = ttk.Label(config_frame, text="未选择", style="AllocatorMuted.TLabel")
        self.directory_label.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(0, 8), pady=4)
        self.directory_btn = ttk.Button(
            config_frame,
            text="选择",
            command=self._select_record_directory,
            state=tk.DISABLED,
        )
        self.directory_btn.grid(row=2, column=3, sticky="e", padx=(8, 0), pady=4)

        # ===== 第三部分：申请材料上传 =====
        upload_frame = ttk.LabelFrame(left_frame, text="申请材料上传", padding=(12, 8))
        upload_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))

        upload_container = ttk.Frame(upload_frame)
        upload_container.pack(fill=tk.BOTH, expand=True)

        upload_container.columnconfigure(0, weight=1)
        upload_container.columnconfigure(1, weight=1)
        upload_container.rowconfigure(0, weight=1)

        self.image_upload = DragDropFrame(
            upload_container,
            title="上传图片",
            file_types=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif")],
            on_drop_callback=self._on_image_selected
        )
        self.image_upload.grid(row=0, column=0, padx=(0, 6), pady=2, sticky='nsew')
        self.image_upload.set_enabled(False)  # 初始禁用

        self.application_upload = DragDropFrame(
            upload_container,
            title="上传IP地址申请表",
            file_types=[("Excel文件", "*.xlsx *.xls")],
            on_drop_callback=self._on_application_selected
        )
        self.application_upload.grid(row=0, column=1, padx=(6, 0), pady=2, sticky='nsew')
        self.application_upload.set_enabled(False)  # 初始禁用

        # ===== 第四部分：操作按钮 =====
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=3, column=0, sticky="ew")
        button_frame.columnconfigure(0, weight=1)

        self.allocate_btn = tk.Button(
            button_frame,
            text="归档申请",
            command=self._allocate,
            font=('Microsoft YaHei UI', 11, 'bold'),
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_WHITE,
            activebackground=Colors.PRIMARY_LIGHT,
            activeforeground=Colors.TEXT_WHITE,
            relief=tk.FLAT,
            width=14,
            height=2,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.allocate_btn.grid(row=0, column=1, sticky="e")

        # ===== 右侧面板：IP申请表显示区域 =====
        right_frame = ttk.Frame(main_paned, padding=(8, 10, 12, 10))
        main_paned.add(right_frame, weight=2)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)

        # 右侧标题
        ttk.Label(
            right_frame,
            text="IP申请表内容",
            style="AllocatorPanelTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        # 提示标签
        self.app_hint_label = ttk.Label(
            right_frame,
            text="请上传IP地址申请表以查看内容",
            style="AllocatorMuted.TLabel",
        )
        self.app_hint_label.grid(row=1, column=0, sticky="w", pady=(0, 6))

        # 创建Treeview用于显示IP申请表数据
        tree_container = ttk.Frame(right_frame)
        tree_container.grid(row=2, column=0, sticky="nsew")

        self.app_tree = ttk.Treeview(
            tree_container, columns=[], show='headings', height=18)

        tree_scroll_y = ttk.Scrollbar(
            tree_container, orient=tk.VERTICAL, command=self.app_tree.yview)
        tree_scroll_x = ttk.Scrollbar(
            tree_container, orient=tk.HORIZONTAL, command=self.app_tree.xview)
        self.app_tree.configure(
            yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.app_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def _select_ip_plan(self) -> None:
        """选择IP地址规划表"""
        file_path = filedialog.askopenfilename(
            title="选择IP地址规划表",
            filetypes=[("Excel文件", "*.xlsx *.xls")]
        )
        if file_path:
            self.ip_plan_file = file_path
            filename = os.path.basename(file_path)
            self.plan_label.config(text=filename, foreground=Colors.SUCCESS)
            logger.info(f"已选择IP地址规划表: {filename}")
            # 启用IP规划按钮和IP分配总表选择
            self._update_component_states()
            # 保存配置
            self._save_config()

    def _open_ip_plan_dialog(self) -> None:
        """打开IP地址规划对话框"""
        IPPlanDialog(self.parent, self.ip_plan_file)

    def _select_ip_allocation(self) -> None:
        """选择IP地址分配总表"""
        file_path = filedialog.askopenfilename(
            title="选择IP地址分配总表",
            filetypes=[("Excel文件", "*.xlsx *.xls")]
        )
        if file_path:
            self.ip_allocation_file = file_path
            filename = os.path.basename(file_path)
            self.allocation_label.config(text=filename, foreground=Colors.SUCCESS)
            logger.info(f"已选择IP地址分配总表: {filename}")
            # 启用后续组件
            self._update_component_states()
            # 保存配置
            self._save_config()

    def _select_record_directory(self) -> None:
        """选择IP地址分配记录目录"""
        dir_path = filedialog.askdirectory(title="选择IP地址分配记录目录")
        if dir_path:
            self.record_directory = dir_path
            dirname = os.path.basename(dir_path)
            self.directory_label.config(text=dirname, foreground=Colors.SUCCESS)
            logger.info(f"已选择IP地址分配记录目录: {dirname}")

    def _update_component_states(self) -> None:
        """更新组件状态（递进约束）

        约束关系：
        1. 选择IP规划表 -> 启用IP规划按钮和IP分配总表选择
        2. 选择IP分配总表 -> 启用目录选择、上传区域、分配按钮
        """
        # 约束1：IP规划表选择后，启用IP规划按钮和IP分配总表选择
        if self.ip_plan_file:
            self.plan_btn.config(state=tk.NORMAL)
            self.allocation_btn.config(state=tk.NORMAL)
        else:
            self.plan_btn.config(state=tk.DISABLED)
            self.allocation_btn.config(state=tk.DISABLED)
            # 同时禁用后续所有组件
            self.directory_btn.config(state=tk.DISABLED)
            self.image_upload.set_enabled(False)
            self.application_upload.set_enabled(False)
            self.status_label.config(text="请先选择IP地址规划表", foreground=Colors.TEXT_HINT)
            return

        # 约束2：IP分配总表选择后，启用目录选择、上传区域
        if self.ip_allocation_file:
            self.directory_btn.config(state=tk.NORMAL)
            self.image_upload.set_enabled(True)
            self.application_upload.set_enabled(True)
            self._update_allocate_button()
        else:
            self.directory_btn.config(state=tk.DISABLED)
            self.image_upload.set_enabled(False)
            self.application_upload.set_enabled(False)
            self.allocate_btn.config(state=tk.DISABLED)
            self.status_label.config(text="请先选择IP地址分配总表", foreground=Colors.TEXT_HINT)

    def _on_image_selected(self, file_path: str) -> None:
        """图片选择回调"""
        self.image_file = file_path
        logger.info(f"已选择图片: {os.path.basename(file_path)}")
        self._update_allocate_button()

    def _on_application_selected(self, file_path: str) -> None:
        """申请表选择回调"""
        self.application_file = file_path
        logger.info(f"已选择申请表: {os.path.basename(file_path)}")
        self._update_allocate_button()
        # 加载并显示申请表内容
        self._load_and_display_application(file_path)

    def _load_and_display_application(self, file_path: str) -> None:
        """Read the public table contract, independent of worksheet/site names."""
        try:
            columns, records = read_display_table(file_path)
            for item in self.app_tree.get_children():
                self.app_tree.delete(item)
            self._update_app_tree_columns(columns)
            for values in records:
                self.app_tree.insert('', tk.END, values=values)
            self.app_hint_label.config(text=f"已加载 {len(records)} 条记录", foreground=Colors.SUCCESS)
        except Exception as error:
            logger.error("读取表格失败", exc_info=True)
            self.app_hint_label.config(text=f"读取失败: {error}", foreground=Colors.ERROR)
            messagebox.showerror("错误", f"读取表格失败: {error}")

    def _update_app_tree_columns(self, columns: list) -> None:
        """动态更新申请表Treeview的列定义

        Args:
            columns: 列名列表
        """
        self.application_columns = columns
        self.app_tree['columns'] = columns

        for col in columns:
            self.app_tree.heading(col, text=col)
            width = max(80, len(col) * 12)
            self.app_tree.column(col, width=width, anchor='center')

    def _update_allocate_button(self) -> None:
        """更新分配按钮状态"""
        if self.image_file and self.application_file:
            self.allocate_btn.config(state=tk.NORMAL)
            self.status_label.config(text="可以归档申请资料（地址分配尚未接入）", foreground=Colors.SUCCESS)
        else:
            self.allocate_btn.config(state=tk.DISABLED)
            missing = []
            if not self.image_file:
                missing.append("图片")
            if not self.application_file:
                missing.append("申请表")
            self.status_label.config(
                text=f"请先上传: {', '.join(missing)}",
                foreground=Colors.TEXT_HINT
            )

    def _generate_subdirectory_name(self) -> str:
        """生成子目录名称

        格式：8位年月日日期 + 3001开头的4位流水号
        例如：20260227_3001
        """
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        base_dir = self.record_directory or os.getcwd()

        serial_number = 3001
        while True:
            dir_name = f"add{date_str}{serial_number}"
            full_path = os.path.join(base_dir, dir_name)
            if not os.path.exists(full_path):
                break
            serial_number += 1

        return dir_name

    def _allocate(self) -> None:
        """执行分配操作"""
        try:
            if not self.image_file or not self.application_file:
                messagebox.showwarning("警告", "请先上传图片和IP地址申请表")
                return

            if not self.record_directory:
                dir_path = filedialog.askdirectory(title="请选择IP地址分配记录目录")
                if not dir_path:
                    return
                self.record_directory = dir_path

            sub_dir_name = self._generate_subdirectory_name()
            sub_dir_path = os.path.join(self.record_directory, sub_dir_name)

            os.makedirs(sub_dir_path, exist_ok=True)
            logger.info(f"创建子目录: {sub_dir_path}")

            image_ext = os.path.splitext(self.image_file)[1]
            image_dest = os.path.join(
                sub_dir_path,
                f"{sub_dir_name}_{os.path.splitext(os.path.basename(self.image_file))[0]}{image_ext}")
            shutil.copy2(self.image_file, image_dest)
            logger.info(f"复制图片到: {image_dest}")

            app_ext = os.path.splitext(self.application_file)[1]
            app_dest = os.path.join(
                sub_dir_path,
                f"{sub_dir_name}_{os.path.splitext(os.path.basename(self.application_file))[0]}{app_ext}")
            shutil.copy2(self.application_file, app_dest)
            logger.info(f"复制申请表到: {app_dest}")

            messagebox.showinfo("成功", "申请资料已归档。当前实验版本尚未执行地址分配。")

            self.image_upload.clear()
            self.application_upload.clear()
            self.image_file = None
            self.application_file = None
            self._update_allocate_button()

        except Exception as e:
            logger.error(f"分配过程中发生错误: {e}", exc_info=True)
            messagebox.showerror("错误", f"分配失败: {str(e)}")

    def set_initial_focus(self) -> None:
        """设置初始焦点（供外部调用）"""

    def _load_config(self) -> None:
        """加载保存的配置文件

        检查配置文件中记录的路径是否仍然有效，如果有效则自动加载。
        """
        if not os.path.exists(CONFIG_FILE):
            logger.info("配置文件不存在，跳过自动加载")
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

            logger.info(f"加载配置文件: {CONFIG_FILE}")

            # 检查IP规划表路径有效性
            ip_plan_path = config.get('ip_plan_file')
            if ip_plan_path and os.path.isfile(ip_plan_path):
                self.ip_plan_file = ip_plan_path
                filename = os.path.basename(ip_plan_path)
                self.plan_label.config(text=filename, foreground=Colors.SUCCESS)
                logger.info(f"自动加载IP规划表: {filename}")
                last_time = config.get('ip_plan_time', '未知')
                logger.info(f"上次使用时间: {last_time}")

            # 检查IP分配总表路径有效性
            ip_allocation_path = config.get('ip_allocation_file')
            if ip_allocation_path and os.path.isfile(ip_allocation_path):
                self.ip_allocation_file = ip_allocation_path
                filename = os.path.basename(ip_allocation_path)
                self.allocation_label.config(text=filename, foreground=Colors.SUCCESS)
                logger.info(f"自动加载IP分配总表: {filename}")
                last_time = config.get('ip_allocation_time', '未知')
                logger.info(f"上次使用时间: {last_time}")

            # 更新组件状态
            self._update_component_states()

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}", exc_info=True)

    def _save_config(self) -> None:
        """保存当前配置到文件

        保存IP规划表和IP分配总表的路径及时间戳。
        """
        try:
            # 确保配置目录存在
            os.makedirs(CONFIG_DIR, exist_ok=True)

            config = {}
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 保存IP规划表路径
            if self.ip_plan_file:
                config['ip_plan_file'] = self.ip_plan_file
                config['ip_plan_time'] = current_time

            # 保存IP分配总表路径
            if self.ip_allocation_file:
                config['ip_allocation_file'] = self.ip_allocation_file
                config['ip_allocation_time'] = current_time

            # 写入配置文件
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已保存到: {CONFIG_FILE}")

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 模块独立运行入口，用于自测
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    print("[自测模式] 启动IP地址分配模块独立测试...")

    try:
        root = tk.Tk()
        root.title("IP地址分配模块 - 独立测试")
        root.geometry("1200x700")

        allocator = IPAllocator(root)

        print("[自测模式] 模块初始化成功")
        print("[自测模式] GUI窗口已启动，可进行手动测试")

        root.mainloop()

    except Exception as e:
        print(f"[自测模式] 错误: {e}")
        sys.exit(1)
    finally:
        print("[自测模式] 测试结束")
