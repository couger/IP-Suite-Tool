#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IP脱敏器GUI界面

提供文件中IPv4和IPv6地址脱敏处理功能。

作者: Assistant
版本: 4.0
"""

"""IP脱敏器GUI界面 - 主类定义"""

# 标准库导入（按字母顺序）
import os
import sys
import threading
import logging
from datetime import datetime
from typing import Optional

# 统一日志配置
try:
    from utils.logger_config import setup_module_logger

    logger = setup_module_logger("ip_anonymizer", logging.INFO)
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("ip_anonymizer")

# 第三方库导入
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# 本地模块导入
from models.model_anonymizer_core import IPAnonymizerCore
from models.model_anonymizer_processor import (
    FileProcessor,
    ProcessingResult,
    ProcessingStats,
)


def _safe_print(message):
    """避免Windows GBK控制台无法输出emoji时中断处理流程。"""
    try:
        logging.getLogger(__name__).debug("Processing event")
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_message = str(message).encode(encoding, errors="replace").decode(encoding)
        logging.getLogger(__name__).debug("Processing event")


class IPAnonymizer:
    """IP脱敏器主类"""

    IMPORTABLE_EXTENSIONS = {".xlsx", ".xls", ".txt", ".docx"}

    def __init__(self, parent):
        """初始化IP脱敏器

        Args:
            parent: 父容器
        """

        self.root = parent
        self.parent = parent
        self.processor = FileProcessor(partial_anonymize=True)
        self.ip_core = IPAnonymizerCore(partial_anonymize=True)  # 添加IP核心处理器
        self.selected_files = []
        # self.processing_stats = ProcessingStats()
        self.is_processing = False
        self.processing_thread = None
        self.latest_output_files = []
        self.work_stats_launcher = None

        # 初始化组件
        self._init_ui()
        # self._bind_events()

        # 使用 after 方法在所有组件初始化完成后设置焦点
        self.root.after(
            100,
            lambda: (
                self.import_files_btn.focus_set() if self.import_files_btn else None
            ),
        )

    def set_work_stats_launcher(self, launcher):
        """设置从脱敏结果进入工作统计页的回调"""
        self.work_stats_launcher = launcher

    def _init_ui(self):
        """初始化用户界面组件"""
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建界面组件（移除功能说明部分）
        # self._create_header_section()  # 已删除使用说明部分
        self._create_import_section()
        self._create_settings_section()
        self._create_processing_section()
        self._create_results_section()

        # def _bind_events(self):
        """绑定事件处理"""
        # 实现具体的事件绑定逻辑
        # 绑定窗口关闭事件
        # self.parent.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 绑定按钮事件
        # self.import_btn.bind("<Button-1>", lambda e: self.import_files())
        # self.process_btn.bind("<Button-1>", lambda e: self.start_processing())
        # 其他事件绑定...

    def _on_closing(self):
        """窗口关闭事件处理"""
        if self.is_processing:
            confirm = messagebox.askyesno(
                "确认关闭", "处理正在进行中，确定要关闭程序吗？\n这将中断当前处理任务。"
            )
            if confirm:
                # 停止处理
                self.processor.stop_processing()
                self.parent.destroy()
        else:
            self.parent.destroy()

    def _create_import_section(self):
        """创建文件导入区域"""
        import_frame = ttk.LabelFrame(self.main_frame, text="文件导入", padding="6")
        import_frame.pack(fill=tk.X, pady=(0, 6))

        # 创建主容器，使用grid布局实现左右结构
        main_container = ttk.Frame(import_frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 左侧：文件列表显示区域
        list_frame = ttk.Frame(main_container)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)

        # 创建Treeview来显示文件列表（高度减为4行）
        columns = ("文件名", "路径", "大小", "类型")
        self.files_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=4,
            selectmode="extended",
        )

        # 设置列标题和宽度（更紧凑的列宽）
        self.files_tree.heading("文件名", text="文件名")
        self.files_tree.heading("路径", text="路径")
        self.files_tree.heading("大小", text="大小")
        self.files_tree.heading("类型", text="类型")

        self.files_tree.column("文件名", width=160)
        self.files_tree.column("路径", width=220)
        self.files_tree.column("大小", width=70)
        self.files_tree.column("类型", width=70)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.files_tree.yview
        )
        self.files_tree.configure(yscrollcommand=scrollbar.set)

        self.files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧：操作按钮区域
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=0, column=1, sticky="ns")
        button_frame.columnconfigure(0, weight=1)

        # 创建按钮样式
        button_width = 12

        self.import_files_btn = ttk.Button(
            button_frame,
            text="导入文件",
            command=self._import_files,
            width=button_width,
        )
        self.import_files_btn.grid(row=0, column=0, pady=(0, 6), sticky="ew")

        self.import_folder_btn = ttk.Button(
            button_frame,
            text="导入目录",
            command=self._import_folder,
            width=button_width,
        )
        self.import_folder_btn.grid(row=1, column=0, pady=(0, 6), sticky="ew")

        self.delete_files_btn = ttk.Button(
            button_frame,
            text="删除选中",
            command=self._delete_selected_files,
            width=button_width,
        )
        self.delete_files_btn.grid(row=2, column=0, pady=(0, 6), sticky="ew")

        self.clear_files_btn = ttk.Button(
            button_frame,
            text="清空列表",
            command=self._clear_files_list,
            width=button_width,
        )
        self.clear_files_btn.grid(row=3, column=0, pady=(0, 6), sticky="ew")

    def _create_settings_section(self):
        """创建设置区域"""
        settings_frame = ttk.LabelFrame(self.main_frame, text="脱敏设置", padding="6")
        settings_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(settings_frame, text="仅替换文档中的 IP 文本；不保证去除单位、人员、批注、外链和元数据。公开前须另行检查。", wraplength=850).pack(fill=tk.X, pady=(0, 4))

        # 脱敏程度选择（单行布局）
        degree_frame = ttk.Frame(settings_frame)
        degree_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(degree_frame, text="脱敏程度:").pack(side=tk.LEFT)

        self.anonymize_mode = tk.StringVar(value="partial")
        self.partial_radio = ttk.Radiobutton(
            degree_frame,
            text="部分 IP 遮盖",
            variable=self.anonymize_mode,
            value="partial",
            command=self._on_mode_changed,
        )
        self.partial_radio.pack(side=tk.LEFT, padx=(10, 8))

        self.full_radio = ttk.Radiobutton(
            degree_frame,
            text="全部 IP 替换",
            variable=self.anonymize_mode,
            value="full",
            command=self._on_mode_changed,
        )
        self.full_radio.pack(side=tk.LEFT)

        # 输出目录设置（紧凑布局）
        output_frame = ttk.Frame(settings_frame)
        output_frame.pack(fill=tk.X)

        ttk.Label(output_frame, text="输出目录:").pack(side=tk.LEFT)

        self.output_path_var = tk.StringVar()
        self.output_entry = ttk.Entry(
            output_frame, textvariable=self.output_path_var, width=40
        )
        self.output_entry.pack(side=tk.LEFT, padx=(10, 6), fill=tk.X, expand=True)

        self.browse_output_btn = ttk.Button(
            output_frame, text="浏览", command=self._browse_output_directory
        )
        self.browse_output_btn.pack(side=tk.LEFT)

    def _create_processing_section(self):
        """创建处理控制区域"""
        processing_frame = ttk.LabelFrame(self.main_frame, text="处理控制", padding="6")
        processing_frame.pack(fill=tk.X, pady=(0, 6))

        # 创建主容器，使用grid布局实现左右结构
        main_container = ttk.Frame(processing_frame)
        main_container.pack(fill=tk.X, expand=True)

        # 左侧：进度条区域
        progress_frame = ttk.Frame(main_container)
        progress_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        main_container.columnconfigure(0, weight=1)

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Green.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W)

        # 右侧：控制按钮区域
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=0, column=1, sticky="ns")
        button_frame.columnconfigure(0, weight=1)

        # 创建按钮样式
        button_width = 12

        self.process_btn = ttk.Button(
            button_frame,
            text="开始处理",
            command=self._start_processing,
            style="Accent.TButton",
            width=button_width,
        )
        self.process_btn.grid(row=0, column=0, pady=(0, 6), sticky="ew")

        self.stop_btn = ttk.Button(
            button_frame,
            text="停止处理",
            command=self._stop_processing,
            state=tk.DISABLED,
            width=button_width,
        )
        self.stop_btn.grid(row=1, column=0, pady=(0, 6), sticky="ew")

    def _create_results_section(self):
        """创建结果展示区域"""
        results_frame = ttk.LabelFrame(self.main_frame, text="结果统计", padding="6")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # 创建主容器，使用grid布局实现左右结构
        main_container = ttk.Frame(results_frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 左侧：结果和统计显示区域（作为一个整体）
        left_frame = ttk.Frame(main_container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)

        # 使用PanedWindow将结果和统计作为一个整体容器
        left_paned_window = ttk.PanedWindow(left_frame, orient=tk.VERTICAL)
        left_paned_window.pack(fill=tk.BOTH, expand=True)

        # 上半部分：结果文本框
        results_subframe = ttk.Frame(left_paned_window)
        self.results_text = scrolledtext.ScrolledText(
            results_subframe, height=5, state=tk.DISABLED
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        left_paned_window.add(results_subframe, weight=3)

        # 下半部分：统计信息显示（单行显示）
        stats_subframe = ttk.Frame(left_paned_window)
        self.stats_text = tk.Text(stats_subframe, height=1, state=tk.DISABLED)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        left_paned_window.add(stats_subframe, weight=1)

        # 右侧：控制选项区域
        right_frame = ttk.Frame(main_container)
        right_frame.grid(row=0, column=1, sticky="ns")
        right_frame.columnconfigure(0, weight=1)

        # 创建控制选项标签框架
        # controls_frame = ttk.LabelFrame(right_frame, text="处理选项", padding="6")
        # controls_frame.pack(fill=tk.X, pady=(0, 10))

        # 记录文件选项
        # record_frame = ttk.Frame(controls_frame)
        record_frame = ttk.Frame(results_frame)
        record_frame.pack(fill=tk.X, pady=(0, 6))

        # ttk.Label(record_frame, text="记录文件:").pack(anchor=tk.W)
        self.record_file_var = tk.BooleanVar(value=True)  # 使用BooleanVar替代StringVar
        self.record_checkbox = ttk.Checkbutton(
            # record_frame,
            right_frame,
            text="错误记录",
            variable=self.record_file_var,
        )
        self.record_checkbox.pack(fill=tk.X, pady=(2, 0))

        # 结果验证选项
        # verify_frame = ttk.Frame(controls_frame)
        # verify_frame.pack(fill=tk.X, pady=(0, 6))

        # ttk.Label(verify_frame, text="结果验证:").pack(anchor=tk.W)
        self.verify_result_var = tk.BooleanVar(
            value=False
        )  # 使用BooleanVar替代StringVar
        self.verify_checkbox = ttk.Checkbutton(
            # verify_frame,
            right_frame,
            text="结果验证",
            variable=self.verify_result_var,
        )
        self.verify_checkbox.pack(fill=tk.X, pady=(2, 0))

        self.work_stats_btn = ttk.Button(
            right_frame,
            text="工作统计",
            command=self._open_work_stats,
            state=tk.DISABLED,
            style="Accent.TButton",
            width=12,
        )
        self.work_stats_btn.pack(fill=tk.X, pady=(8, 0))

        # 初始化统计数据
        # self._update_statistics()

    def _get_smart_output_path(self):
        """智能生成输出路径，保持目录结构并添加时间戳"""
        if not self.selected_files:
            return ""

        # 获取所有输入文件的共同父目录
        input_dirs = [os.path.dirname(path) for path in self.selected_files]
        try:
            common_parent = os.path.commonpath(input_dirs)
        except ValueError:
            # 如果没有公共路径，使用第一个文件的目录
            common_parent = os.path.dirname(self.selected_files[0])

        # 标准化路径分隔符
        common_parent = os.path.normpath(common_parent)

        # 添加时间戳后缀
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_name = f"IP脱敏结果_{timestamp}"
        base_output_path = os.path.join(common_parent, base_output_name)

        return base_output_path

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _is_importable_file(self, file_path: str) -> bool:
        """判断文件是否属于脱敏器支持的导入类型。"""
        file_name = os.path.basename(file_path)
        if file_name.startswith("~$"):
            return False
        return os.path.splitext(file_path)[1].lower() in self.IMPORTABLE_EXTENSIONS

    def _add_files_to_list(self, file_paths):
        """添加文件到列表显示"""
        added_count = 0
        skipped_count = 0
        for file_path in file_paths:
            # 标准化路径分隔符
            file_path = os.path.normpath(file_path)

            if not self._is_importable_file(file_path):
                skipped_count += 1
                continue

            if file_path not in self.selected_files:
                # 验证文件访问权限
                if not self.processor.validate_file_access(file_path):
                    messagebox.showwarning("文件访问错误", f"无法访问文件: {file_path}")
                    continue

                self.selected_files.append(file_path)
                file_name = os.path.basename(file_path)
                file_dir = os.path.dirname(file_path)
                try:
                    file_size = self._format_file_size(os.path.getsize(file_path))
                except (OSError, FileNotFoundError) as e:
                    file_size = "无法获取"
                    logger.warning(f"无法获取文件大小: {file_path}, 错误信息: {e}")
                file_ext = os.path.splitext(file_path)[1].lower()
                file_type = self.processor.get_supported_extensions().get(
                    file_ext, "未知"
                )

                self.files_tree.insert(
                    "", tk.END, values=(file_name, file_dir, file_size, file_type)
                )
                added_count += 1

        # 更新输出目录显示为最后一个导入对象的路径
        if self.selected_files and not self.output_path_var.get():
            last_file_dir = os.path.dirname(self.selected_files[-1])
            # 标准化路径并添加时间戳
            normalized_dir = os.path.normpath(last_file_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_output = os.path.join(normalized_dir, f"IP脱敏结果_{timestamp}")
            self.output_path_var.set(default_output)

        if added_count > 0:
            message = f"成功导入 {added_count} 个文件"
            if skipped_count:
                message += f"\n已跳过 {skipped_count} 个非支持类型文件"
            messagebox.showinfo("导入完成", message)
        elif skipped_count:
            messagebox.showwarning(
                "未导入文件",
                "未找到可导入文件。\n支持类型：Excel、TXT、Word(docx)。",
            )

    def _import_files(self):
        """导入文件"""
        if self.is_processing:
            messagebox.showwarning("处理中", "请等待当前处理完成后再导入文件")
            return

        file_paths = filedialog.askopenfilenames(
            title="选择要导入的文件",
            filetypes=[
                ("支持文件", "*.xlsx *.xls *.txt *.docx"),
                ("Excel文件", "*.xlsx *.xls"),
                ("文本文件", "*.txt"),
                ("Word文件", "*.docx"),
            ],
        )

        if file_paths:
            self._add_files_to_list(file_paths)

    def _import_folder(self):
        """导入目录"""
        if self.is_processing:
            messagebox.showwarning("处理中", "请等待当前处理完成后再导入文件")
            return

        folder_path = filedialog.askdirectory(title="选择要导入的目录")

        if folder_path:
            # 获取目录中的所有文件
            file_paths = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._is_importable_file(file_path):
                        file_paths.append(file_path)

            if file_paths:
                self._add_files_to_list(file_paths)
            else:
                messagebox.showwarning(
                    "未导入文件",
                    "目录中没有可导入文件。\n支持类型：Excel、TXT、Word(docx)。",
                )

    def _delete_selected_files(self):
        """删除选中的文件"""
        if self.is_processing:
            messagebox.showwarning("处理中", "请等待当前处理完成后再删除文件")
            return

        selected_items = self.files_tree.selection()
        if not selected_items:
            messagebox.showwarning("无选择", "请先选择要删除的文件")
            return

        # 确认删除
        if len(selected_items) == 1:
            confirm_msg = "确定要删除选中的文件吗？"
        else:
            confirm_msg = f"确定要删除选中的 {len(selected_items)} 个文件吗？"

        if not messagebox.askyesno("确认删除", confirm_msg):
            return

        # 删除选中的文件
        items_to_delete = []
        for item in selected_items:
            # 获取文件信息
            item_values = self.files_tree.item(item, "values")
            if item_values and len(item_values) >= 2:
                file_name = item_values[0]
                file_dir = item_values[1]
                file_path = os.path.join(file_dir, file_name)

                # 从内部列表中移除
                if file_path in self.selected_files:
                    self.selected_files.remove(file_path)
                    items_to_delete.append(item)

        # 从Treeview中删除
        for item in items_to_delete:
            self.files_tree.delete(item)

        messagebox.showinfo("删除成功", f"已删除 {len(items_to_delete)} 个文件")

    def _clear_files_list(self):
        """清空文件列表"""
        if self.is_processing:
            messagebox.showwarning("处理中", "请等待当前处理完成后再清空列表")
            return

        self.selected_files.clear()
        self.files_tree.delete(*self.files_tree.get_children())
        self.output_path_var.set("")

    def _on_mode_changed(self):
        """处理脱敏模式更改"""
        mode = self.anonymize_mode.get()
        self.processor.set_anonymize_mode(mode == "partial")
        self.ip_core.set_anonymize_mode(mode == "partial")

    def _browse_output_directory(self):
        """浏览输出目录"""
        output_dir = filedialog.askdirectory(title="选择输出目录")

        if output_dir:
            self.output_path_var.set(output_dir)

    def _start_processing(self):
        """开始处理文件"""
        if self.is_processing:
            messagebox.showwarning("已在处理", "处理正在进行中，请先停止当前处理")
            return

        if not self.selected_files:
            messagebox.showwarning("无文件", "请先导入要处理的文件")
            return

        if not self.output_path_var.get():
            # 设置智能默认输出目录
            default_output_path = self._get_smart_output_path()
            self.output_path_var.set(default_output_path)

        # 确认处理
        confirm = messagebox.askyesno(
            "确认处理",
            f"确定要处理 {len(self.selected_files)} 个文件吗？\n"
            f"处理后的文件将保存到: {self.output_path_var.get()}",
        )

        if not confirm:
            return

        # 设置处理状态
        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.import_files_btn.config(state=tk.DISABLED)
        self.import_folder_btn.config(state=tk.DISABLED)
        self.delete_files_btn.config(state=tk.DISABLED)
        self.clear_files_btn.config(state=tk.DISABLED)
        self.status_var.set("正在处理...")
        self.latest_output_files = []
        if hasattr(self, "work_stats_btn"):
            self.work_stats_btn.config(state=tk.DISABLED)

        # 清空之前的处理结果
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)

        # 在新线程中执行处理
        file_paths = list(self.selected_files)
        output_path = self.output_path_var.get()
        self.processing_thread = threading.Thread(
            target=self._process_files_thread,
            args=(file_paths, output_path),
            daemon=True,
        )
        self.processing_thread.start()

    def _stop_processing(self):
        """停止处理"""
        if not self.is_processing:
            return

        confirm = messagebox.askyesno("确认停止", "确定要停止当前处理吗？")
        if confirm:
            self.status_var.set("正在停止...")
            self.processor.stop_processing()

    def _process_files_thread(self, file_paths, output_path):
        """在后台线程中处理文件"""
        try:

            def progress_callback(current, total, result):
                progress = (current / total) * 100
                status = f"处理中... ({current}/{total})"

                def update_progress():
                    if not self.is_processing:
                        return
                    self.progress_var.set(progress)
                    self.status_var.set(status)
                    self._append_result_to_display(result)

                self.parent.after(0, update_progress)

            # 执行批量处理（保持目录结构）
            results, stats = self.processor.process_files_batch_with_structure(
                file_paths, output_path, progress_callback
            )
            self.latest_output_files = self._get_work_stats_input_files(results)

            # 执行结果验证（如果启用）
            unprocessed_files = []
            if hasattr(self, "verify_result_var") and self.verify_result_var.get():
                unprocessed_files = self.processor.verify_results(
                    results, self.output_path_var.get()
                )
                # 将验证结果添加到统计信息中
                stats.unprocessed_files = unprocessed_files
                _safe_print(f"🔍 验证完成，发现 {len(unprocessed_files)} 个未处理干净的文件")

            # 保存错误记录（如果启用）
            if hasattr(self, "record_file_var") and self.record_file_var.get():
                # 从处理器获取错误记录并保存到统一结果文件
                error_records_to_save = []

                # 收集处理器的错误记录
                if (
                    hasattr(self.processor, "error_records")
                    and self.processor.error_records
                ):
                    error_records_to_save.extend(self.processor.error_records)

                # 如果没有错误记录，添加一条处理成功的记录
                if not error_records_to_save:
                    error_records_to_save.append(
                        {
                            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "文件路径": "N/A",
                            "工作表名": "N/A",
                            "行号": "N/A",
                            "列号": "N/A",
                            "原始内容": "N/A",
                            "错误信息": "处理完成，无错误发生",
                        }
                    )

                # 保存到统一结果记录文件
                self._save_to_unified_result(
                    output_path,
                    stats,
                    error_records_to_save,
                    unprocessed_files,
                )

            def finish_success():
                self.processing_stats = stats
                self._update_statistics()
                if self.is_processing:
                    self._show_completion_message(stats, unprocessed_files)

            self.parent.after(0, finish_success)

        except Exception as e:
            if self.is_processing:
                error_message = str(e)
                self.parent.after(
                    0,
                    lambda message=error_message: messagebox.showerror(
                        "处理错误", f"处理过程中发生错误:\n{message}"
                    ),
                )
        finally:
            self.parent.after(0, self._reset_ui_state)

    def _reset_ui_state(self):
        """重置UI状态"""
        self.is_processing = False
        self.process_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.import_files_btn.config(state=tk.NORMAL)
        self.import_folder_btn.config(state=tk.NORMAL)
        self.delete_files_btn.config(state=tk.NORMAL)
        self.clear_files_btn.config(state=tk.NORMAL)
        if hasattr(self, "work_stats_btn"):
            state = tk.NORMAL if self.latest_output_files else tk.DISABLED
            self.work_stats_btn.config(state=state)
        self.status_var.set("就绪")

    def _get_work_stats_input_files(self, results: list[ProcessingResult]) -> list[str]:
        """获取传递给工作统计页的文件列表，失败文件回退到原始文件。"""
        file_paths = []
        for result in results:
            output_path = getattr(result, "output_path", "")
            if output_path and os.path.exists(output_path):
                file_paths.append(output_path)
            elif os.path.exists(result.file_path):
                file_paths.append(result.file_path)
        return file_paths

    def _open_work_stats(self):
        """打开工作统计页，并载入最终脱敏文件列表"""
        if not self.latest_output_files:
            messagebox.showwarning("无脱敏结果", "当前没有可用于工作统计的脱敏结果文件")
            return

        if self.work_stats_launcher is None:
            messagebox.showwarning("功能不可用", "工作统计页尚未初始化")
            return

        self.work_stats_launcher(self.latest_output_files)

    def _append_result_to_display(self, result: ProcessingResult):
        """将处理结果添加到显示区域"""
        self.results_text.config(state=tk.NORMAL)

        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icon = (
            "✅"
            if result.status == "success"
            else "❌" if result.status == "error" else "⚠️"
        )

        result_text = (
            f"[{timestamp}] {status_icon} {os.path.basename(result.file_path)}"
        )
        if result.status == "success":
            result_text += f" - 处理成功 (发现 {result.ip_count} 个IP地址)"
        elif result.status == "error":
            result_text += f" - 处理失败: {result.error_message}"
        else:
            result_text += f" - 已跳过: {result.error_message}"

        self.results_text.insert(tk.END, result_text + "\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)

    def _update_statistics_display(self):
        """更新统计信息显示"""
        self._update_statistics()  # 调用实际的统计更新方法

    def _show_completion_message(
        self, stats: ProcessingStats, unprocessed_files: Optional[list] = None
    ):
        """显示处理完成消息，包含验证结果"""
        # 构建基础消息
        if stats.failed_files > 0:
            message_type = "处理完成（部分失败）"
            message = (
                f"处理完成，但有 {stats.failed_files} 个文件处理失败！\n\n"
                f"总文件数: {stats.total_files}\n"
                f"成功处理: {stats.successful_files}\n"
                f"处理失败: {stats.failed_files}\n"
                f"已跳过: {stats.skipped_files}\n"
                f"发现IP地址总数: {stats.total_ips_found}\n"
                f"处理耗时: {stats.processing_time:.2f}秒"
            )
        else:
            message_type = "处理完成"
            message = (
                f"所有文件处理完成！\n\n"
                f"总文件数: {stats.total_files}\n"
                f"成功处理: {stats.successful_files}\n"
                f"已跳过: {stats.skipped_files}\n"
                f"发现IP地址总数: {stats.total_ips_found}\n"
                f"处理耗时: {stats.processing_time:.2f}秒"
            )

        # 添加验证结果信息
        if unprocessed_files is not None and len(unprocessed_files) > 0:
            message += f"\n\n⚠️ 验证发现 {len(unprocessed_files)} 个文件未处理干净："
            for i, file_path in enumerate(unprocessed_files[:5], 1):  # 只显示前5个
                message += f"\n  {i}. {os.path.basename(file_path)}"
            if len(unprocessed_files) > 5:
                message += f"\n  ... 还有 {len(unprocessed_files) - 5} 个文件"
        elif unprocessed_files is not None:
            message += "\n\n✅ 验证通过：所有文件均已正确脱敏"

        messagebox.showinfo(message_type, message)

    def _update_statistics(self):
        """更新统计信息显示"""
        if not hasattr(self, "stats_text"):
            return

        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)

        if hasattr(self, "processing_stats"):
            stats = self.processing_stats

            # 构建详细的统计信息
            stats_parts = [
                f"📊 总文件数: {stats.total_files}",
                f"✅ 成功: {stats.successful_files}",
                f"❌ 失败: {stats.failed_files}",
                f"⏭️ 跳过: {stats.skipped_files}",
                f"🔢 发现IP地址总数: {stats.total_ips_found}",
                f"⏱️ 处理耗时: {stats.processing_time:.2f}秒",
            ]

            # 如果有验证结果，添加到统计信息中
            if hasattr(stats, "unprocessed_files") and stats.unprocessed_files:
                unprocessed_count = len(stats.unprocessed_files)
                if unprocessed_count > 0:
                    stats_parts.append(f"⚠️ 未处理干净文件: {unprocessed_count}个")
                else:
                    stats_parts.append("✅ 验证通过: 所有文件已正确脱敏")

            # 组合所有统计信息并插入
            stats_text = " | ".join(stats_parts)
            self.stats_text.insert(1.0, stats_text)

            # 设置文本框格式
            self.stats_text.config(
                state=tk.DISABLED, bg="#f0f8ff", fg="#333333", relief="flat"
            )

            # 添加视觉效果
            self.stats_text.tag_configure("highlight", background="#e6f3ff")
            self.stats_text.tag_add("highlight", "1.0", "1.end")
        else:
            # 默认显示
            self.stats_text.insert(1.0, "📊 暂无处理统计信息")
            self.stats_text.config(state=tk.DISABLED, bg="#f5f5f5", fg="#999999")

    def _save_to_unified_result(
        self, output_path, stats, error_records, unprocessed_files=None
    ):
        """保存到统一的结果记录文件"""
        try:
            import pandas as pd

            # from openpyxl import Workbook

            # 创建统一结果记录文件路径
            result_file_path = os.path.join(output_path, "结果记录.xlsx")

            # 准备统计摘要数据
            summary_data = [
                {"项目": "总文件数", "数值": stats.total_files},
                {"项目": "成功处理文件数", "数值": stats.successful_files},
                {"项目": "处理失败文件数", "数值": stats.failed_files},
                {"项目": "跳过文件数", "数值": stats.skipped_files},
                {"项目": "发现IP地址总数", "数值": stats.total_ips_found},
                {"项目": "处理耗时(秒)", "数值": round(stats.processing_time, 2)},
            ]

            # 添加验证结果统计
            if unprocessed_files is not None:
                summary_data.append(
                    {
                        "项目": "验证结果",
                        "数值": (
                            "通过"
                            if len(unprocessed_files) == 0
                            else f"未通过 ({len(unprocessed_files)}个文件)"
                        ),
                    }
                )

            summary_df = pd.DataFrame(summary_data)

            # 准备错误记录数据
            error_df = pd.DataFrame(error_records) if error_records else None

            # 准备未处理文件数据
            unprocessed_df = None
            if unprocessed_files:
                unprocessed_data = []
                for file_path in unprocessed_files:
                    unprocessed_data.append(
                        {
                            "文件路径": file_path,
                            "问题描述": "文件中仍存在未脱敏的IP地址",
                        }
                    )
                unprocessed_df = pd.DataFrame(unprocessed_data)

            # 保存到Excel文件（多个工作表）
            with pd.ExcelWriter(result_file_path, engine="openpyxl") as writer:
                # 保存统计摘要
                summary_df.to_excel(writer, index=False, sheet_name="处理统计")
                summary_worksheet = writer.sheets["处理统计"]

                # 调整统计表列宽
                for column in summary_worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except (AttributeError, TypeError):
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    summary_worksheet.column_dimensions[column_letter].width = (
                        adjusted_width
                    )

                # 保存错误记录
                if error_df is not None and not error_df.empty:
                    error_df.to_excel(writer, index=False, sheet_name="错误记录")
                    error_worksheet = writer.sheets["错误记录"]

                    # 调整错误记录表列宽
                    for column in error_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        error_worksheet.column_dimensions[column_letter].width = (
                            adjusted_width
                        )
                else:
                    # 即使没有错误也创建空的错误记录表
                    empty_error_df = pd.DataFrame(
                        [
                            {
                                "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "文件路径": "N/A",
                                "工作表名": "N/A",
                                "行号": "N/A",
                                "列号": "N/A",
                                "原始内容": "N/A",
                                "错误信息": "处理完成，无错误发生",
                            }
                        ]
                    )
                    empty_error_df.to_excel(writer, index=False, sheet_name="错误记录")
                    error_worksheet = writer.sheets["错误记录"]
                    # 调整列宽
                    for column in error_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        error_worksheet.column_dimensions[column_letter].width = (
                            adjusted_width
                        )

                # 保存未处理文件列表（如果有）
                if unprocessed_df is not None and not unprocessed_df.empty:
                    unprocessed_df.to_excel(writer, index=False, sheet_name="验证结果")
                    unprocessed_worksheet = writer.sheets["验证结果"]

                    # 调整验证结果表列宽
                    for column in unprocessed_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        unprocessed_worksheet.column_dimensions[column_letter].width = (
                            adjusted_width
                        )
                elif unprocessed_files is not None:
                    # 即使没有未处理文件也创建验证结果表，显示验证通过
                    verification_success_df = pd.DataFrame(
                        [
                            {
                                "验证状态": "通过",
                                "验证时间": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "备注": "所有文件均已正确脱敏",
                            }
                        ]
                    )
                    verification_success_df.to_excel(
                        writer, index=False, sheet_name="验证结果"
                    )
                    verification_worksheet = writer.sheets["验证结果"]
                    # 调整列宽
                    for column in verification_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                pass
                        adjusted_width = min(max_length + 2, 30)
                        verification_worksheet.column_dimensions[
                            column_letter
                        ].width = adjusted_width

            _safe_print(f"✅ 统一结果记录已保存到: {result_file_path}")

        except Exception as e:
            _safe_print(f"❌ 保存统一结果记录时出错: {str(e)}")

    def _save_error_records(self, error_records, output_path):
        """保存错误记录到Excel文件"""
        try:
            import pandas as pd

            # from openpyxl import Workbook

            if not error_records:
                return

            # 创建错误记录文件路径
            error_file_path = os.path.join(output_path, "错误记录.xlsx")

            # 创建DataFrame
            df = pd.DataFrame(error_records)

            # 保存到Excel
            with pd.ExcelWriter(error_file_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="错误记录")

                # 获取工作表对象以调整列宽
                worksheet = writer.sheets["错误记录"]

                # 自动调整列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except (AttributeError, TypeError):
                            pass

                    # 设置列宽，最大不超过50
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            _safe_print(f"✅ 错误记录已保存到: {error_file_path}")

        except Exception as e:
            _safe_print(f"❌ 保存错误记录时出错: {str(e)}")

    def set_initial_focus(self):
        """设置初始焦点到主要输入组件"""
        try:
            # 优先设置文件导入按钮焦点（因为它是最常用的操作起点）
            if hasattr(self, "import_files_btn") and self.import_files_btn:
                self.import_files_btn.focus_set()
            # 备选方案：设置文件树焦点
            elif hasattr(self, "files_tree") and self.files_tree:
                self.files_tree.focus_set()
            else:
                # 最后的备选方案：尝试设置处理按钮焦点
                if hasattr(self, "process_btn") and self.process_btn:
                    self.process_btn.focus_set()
        except Exception as e:
            logging.getLogger(__name__).debug("Processing event")


def main():
    """独立运行入口点"""
    # 获取可执行文件所在目录
    if getattr(sys, "frozen", False):
        # 打包后的exe环境
        application_path = os.path.dirname(sys.executable)
    else:
        # 开发环境
        application_path = os.path.dirname(os.path.abspath(__file__))

    logging.getLogger(__name__).debug("Processing event")
    logger.info("启动IP脱敏器独立调试模式")

    try:
        # 创建主窗口
        root = tk.Tk()
        root.title("IP脱敏器 - 独立调试模式")

        # 设置窗口大小和居中
        window_width = 1000
        window_height = 700
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 创建工具实例
        app = IPAnonymizer(root)

        # 设置窗口关闭事件处理
        def on_closing():
            if app.is_processing:
                confirm = messagebox.askyesno(
                    "确认关闭",
                    "处理正在进行中，确定要关闭程序吗？\n这将中断当前处理任务。",
                )
                if confirm:
                    # 停止处理
                    app.processor.stop_processing()
                    root.destroy()
            else:
                root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # 设置样式
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # 启动主循环
        logger.info("IP脱敏器GUI已启动")
        root.mainloop()

    except Exception as e:
        logger.error(f"启动IP脱敏器时发生错误: {str(e)}")
        logger.error("错误详情:", exc_info=True)
        logging.getLogger(__name__).debug("Processing event")
        input("按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
