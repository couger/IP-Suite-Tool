"""
IP地址转换器模块

功能：
1. IPv4与IPv6地址相互转换
2. 支持多种IPv6格式显示（扩展、压缩、内嵌、无前导零）
3. 实例管理功能
4. 剪贴板监控
5. 配置内容生成

作者：Assistant
版本：4.0
"""

import os
import sys
import time
import json
import threading
from dataclasses import dataclass

# 标准库导入
import logging

# 第三方库导入
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
from functools import partial
import tkinter as tk
from tkinter import ttk, messagebox

# 本地模块导入
from ui.ui_component_observable_label import ObservableLabel
from ui.ui_component_modified_entry import ModifiedAwareEntry
from ui.gui_styles import Colors, Fonts, Dimensions, configure_styles
from models.model_converter_core import CoreIPConverter
from utils.app_paths import config_path, resource_path

# 统一日志配置
try:
    from utils.logger_config import setup_module_logger

    logger = setup_module_logger("ip_converter", logging.DEBUG)
except ImportError:
    # 降级处理
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(_current_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=os.path.join(logs_dir, "app.log"),
        filemode="w",
    )
    logger = logging.getLogger("ip_converter")


@dataclass
class ConversionConfig:
    """转换配置数据类"""

    conversion_type: str
    src_field: str
    dst_field: str
    format_cls: type


class IPConverter(CoreIPConverter):
    """主应用程序类，负责管理GUI界面和业务逻辑"""

    # 窗口常量
    WINDOW_TITLE = "IPv4/IPv6 转换器"

    # IPv6相关常量
    DEFAULT_IPV6_INSTANCE = "0000:0000:0000:0000:0000:0000:0000:0000"
    DISABLED_IPV6_PREFIX = (
        "- - - - : - - - - : - - - - : - - - - : - - - - : - - - - : "
    )

    # 剪贴板监控间隔（秒）
    CLIPBOARD_CHECK_INTERVAL = 1

    # 默认实例配置
    DEFAULT_JSON_INSTANCE = {
        "1": {
            "area": "默认",
            "ipv6": DEFAULT_IPV6_INSTANCE,
            "combo_select": f"{DEFAULT_IPV6_INSTANCE}（默认）",
        }
    }

    def __init__(self, root):
        """初始化应用程序

        Args:
            root: Tkinter根窗口对象
        """
        self.root = root
        self.parent = root

        # 状态变量
        self.suppress_event = False
        self.ipv6_instances = {}
        self.clipboard_thread = None
        self.monitoring = False

        # 文本区域宽度配置（IPv4, IPv6, Script）
        self.TEXT_AREA_WIDTH = (25, 55, 55)

        # 样式常量
        self.ERROR_BG_COLOR = Colors.ERROR

        # 初始化组件
        self._init_ui()
        self._load_ip_instances()
        self._bind_events()

        # 在组件初始化完成后触发combobox的选择绑定事件
        self.root.after(100, self.on_combobox_select, None)

        # 使用 after 方法在所有组件初始化完成后设置焦点
        self.root.after(
            100,
            lambda: (
                self.text_areas["ipv4"].focus_set()
                if "ipv4" in self.text_areas
                else None
            ),
        )

    def toggle_clipboard_monitor(self):
        """切换剪贴板监控功能"""
        if self.clipboard_monitor_enabled.get():
            self.start_clipboard_monitor()
        else:
            self.stop_clipboard_monitor()

    def _init_ui(self):
        """初始化用户界面组件"""
        # 配置ttk样式
        self.style = ttk.Style()
        configure_styles(self.style)

        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建底部按钮框架（使用grid布局）
        self.sub_frame_ipv6_button = ttk.Frame(self.main_frame)
        self.sub_frame_ipv6_button.grid(row=4, column=1, padx=5, pady=5)

        self.sub_frame_scripts = ttk.Frame(self.main_frame)
        self.sub_frame_scripts.grid(row=4, column=2, padx=5, pady=5)

        # 配置网格布局权重，保持老版三栏视觉比例
        for col, weight in enumerate((1, 2, 2)):
            self.main_frame.grid_columnconfigure(col, weight=weight)
        self.main_frame.grid_rowconfigure(3, weight=1)

        # 创建界面组件
        self._create_instance_selector()
        self._create_input_areas()
        self._create_action_buttons()

    def _create_instance_selector(self):
        """创建实例选择区域"""
        # 使用ttk框架提升一致性
        frame = ttk.Frame(self.main_frame, padding=(0, 5))
        frame.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Combobox组件
        label = tk.Label(frame, text="选择IPv6实例:", font=Fonts.BODY, anchor="w")
        label.pack(side=tk.LEFT, padx=(5, 10))

        self.instance_combobox = ttk.Combobox(
            frame,
            width=60,
            state="readonly",
            values=[v["combo_select"] for v in self.ipv6_instances.values()],
            font=Fonts.BODY,
        )
        self.instance_combobox.pack(side=tk.LEFT)

        # 实例管理按钮
        self.del_ipv6_button = ttk.Button(
            frame,
            text="删除",
            command=self.delete_ipv6_instance,
            style="Accent.TButton",
        )
        self.del_ipv6_button.pack(side=tk.LEFT, padx=(10, 5))

    def _create_input_areas(self):
        """创建输入/显示区域"""
        # IPv6实例输入区
        input_frame = ttk.Frame(self.main_frame, padding=(0, 5))
        input_frame.grid(row=1, column=0, columnspan=3, sticky="ew")

        label = tk.Label(input_frame, text="输入IPv6实例:", font=Fonts.BODY, anchor="w")
        label.pack(side=tk.LEFT, padx=(5, 10))

        self.ipv6_entry = ModifiedAwareEntry(input_frame, width=40)
        self.ipv6_entry.pack(side=tk.LEFT)

        self.area_entry = ttk.Entry(input_frame, width=20)
        self.area_entry.pack(side=tk.LEFT, padx=(5, 5))

        self.add_ipv6_button = ttk.Button(
            input_frame,
            text="添加",
            command=self.add_ipv6_instance,
            style="Accent.TButton",
        )
        self.add_ipv6_button.pack(side=tk.LEFT, padx=5)

        # 前缀显示区
        prefix_frame = ttk.Frame(self.main_frame, padding=(0, 5))
        prefix_frame.grid(row=2, column=0, columnspan=3, sticky="ew")

        label = tk.Label(prefix_frame, text="IPv6 前缀 (96 位):", font=Fonts.BODY)
        label.pack(side=tk.LEFT, padx=(5, 10))

        self.prefix_label = ObservableLabel(
            prefix_frame,
            width=40,
            anchor="w",
            disabled_text=self.DISABLED_IPV6_PREFIX,
            font=Fonts.MONOSPACE,
        )
        self.prefix_label.pack(side=tk.LEFT)

        # 三列文本区域
        self.text_areas = {
            "ipv4": self._create_text_area(3, 0, "IPv4 地址"),
            "ipv6": self._create_text_area(3, 1, "IPv6 地址", disabled=True),
            "script": self._create_text_area(3, 2, "命令语句", disabled=True),
        }

    def _create_text_area(self, row, column, label, disabled=False):
        """创建标准文本区域组件

        Args:
            row: 网格行号
            column: 网格列号
            label: 区域标签
            disabled: 是否禁用编辑
        """
        # 使用ttk框架提升一致性
        frame = ttk.Frame(self.main_frame, padding=5)
        frame.grid(row=row, column=column, sticky="nsew")

        # 顶部控制栏
        control_bar = ttk.Frame(frame)
        control_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))

        # 标签
        label_widget = tk.Label(control_bar, text=label, font=Fonts.HEADING, anchor="w")
        label_widget.pack(side=tk.LEFT)

        # 根据区域类型添加控制组件
        if label == "IPv4 地址":
            self.clipboard_monitor_enabled = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(
                control_bar,
                text="监控剪贴板",
                variable=self.clipboard_monitor_enabled,
                command=self.toggle_clipboard_monitor,
            )
            checkbox.pack(side=tk.LEFT, padx=(10, 5))

        elif label == "IPv6 地址":
            self.ipv6_to_ipv4 = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(
                control_bar,
                text="IPv6转IPv4",
                variable=self.ipv6_to_ipv4,
                command=self.ipv6_to_ipv4_mode,
            )
            checkbox.pack(side=tk.RIGHT, padx=(10, 5))

        elif label == "命令语句":
            # 脚本控制框架
            script_frame = ttk.Frame(control_bar)
            script_frame.pack(side=tk.RIGHT, padx=(10, 5))

            self.script_prefix_var = tk.BooleanVar(value=True)
            checkbox = ttk.Checkbutton(
                script_frame,
                text="脚本",
                variable=self.script_prefix_var,
                command=self._on_script_toggle,
            )
            checkbox.pack(side=tk.LEFT)

            self.vendor_var = tk.StringVar(value="huawei")
            self.vendor_var.trace_variable("w", self._update_script_area)

            self.huawei_radio = ttk.Radiobutton(
                script_frame,
                text="华为",
                variable=self.vendor_var,
                value="huawei",
                state="normal",
            )
            self.huawei_radio.pack(side=tk.LEFT, padx=(10, 5))

            self.h3c_radio = ttk.Radiobutton(
                script_frame,
                text="华三",
                variable=self.vendor_var,
                value="h3c",
                state="normal",
            )
            self.h3c_radio.pack(side=tk.LEFT, padx=5)

        # 文本区域
        state = "disabled" if disabled else "normal"
        bg_color = Colors.BG_DISABLED if disabled else Colors.BG_WHITE

        text_area = tk.Text(
            frame,
            height=12,
            width=self.TEXT_AREA_WIDTH[column],
            wrap=tk.NONE,
            bg=bg_color,
            fg=Colors.TEXT_PRIMARY,
            font=Fonts.MONOSPACE,
            state=state,
            insertbackground=Colors.PRIMARY,  # 光标颜色
        )
        text_area.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5)

        # 垂直滚动条
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_area.yview)
        scrollbar.grid(row=1, column=2, sticky="ns")
        text_area.config(yscrollcommand=scrollbar.set)

        # 配置权重使文本区域可扩展
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)

        return text_area

    def _create_action_buttons(self):
        """创建底部操作按钮"""
        self.ipv6_format_var = tk.StringVar(value="noneleadingzero")

        # IPv6格式选项框架
        format_frame = ttk.Frame(self.sub_frame_ipv6_button)
        format_frame.pack(side=tk.LEFT, padx=5)

        label = tk.Label(format_frame, text="格式:", font=Fonts.SMALL)
        label.pack(side=tk.LEFT, padx=(0, 5))

        options = {
            "exploded": "扩展",
            "compressed": "压缩",
            "embedded": "内嵌",
            "noneleadingzero": "无前导零",
        }

        for key, value in options.items():
            ttk.Radiobutton(
                format_frame,
                text=value,
                variable=self.ipv6_format_var,
                value=key,
                command=partial(self.process_text_area, "format_radiobutton"),
            ).pack(side=tk.LEFT, padx=3)

        # 复制按钮框架
        copy_frame = ttk.Frame(self.sub_frame_scripts)
        copy_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            copy_frame,
            text="复制全部",
            command=self.copy_script_to_clipboard,
            style="Primary.TButton",
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            copy_frame,
            text="复制IPv4",
            command=lambda: self.copy_script_to_clipboard("ipv4"),
            style="Primary.TButton",
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            copy_frame,
            text="复制IPv6",
            command=lambda: self.copy_script_to_clipboard("ipv6"),
            style="Primary.TButton",
        ).pack(side=tk.LEFT, padx=2)

        # 清除按钮
        ttk.Button(
            self.main_frame,
            text="清除",
            command=self.clear_ip_area,
            style="Accent.TButton",
            width=10,
        ).grid(row=4, column=0, padx=5, pady=5)

    def ipv6_to_ipv4_mode(self):
        # 获取Checkbutton的状态
        is_checked = self.ipv6_to_ipv4.get()
        # 根据Checkbutton的状态禁用或启用IPv6实例输入区和前缀显示区
        state_disable = "disabled" if is_checked else "normal"
        state_enable = "normal" if is_checked else "disabled"

        bg_color_disable = self.DISABLED_BG_COLOR if is_checked else "white"
        bg_color_enable = "white" if is_checked else self.DISABLED_BG_COLOR

        self.ipv6_entry.config(state=state_disable)
        self.instance_combobox_state = "disabled" if is_checked else "readonly"
        self.instance_combobox.config(state=self.instance_combobox_state)
        self.add_ipv6_button.config(state=state_disable)
        self.del_ipv6_button.config(state=state_disable)
        self.area_entry.config(state=state_disable)

        self.text_areas["ipv4"].config(state=state_disable)
        self.text_areas["ipv6"].config(state=state_enable)
        self.text_areas["ipv4"].configure(bg=bg_color_disable)
        self.text_areas["ipv6"].configure(bg=bg_color_enable)

        self.prefix_label.disable(is_checked)
        (
            self.text_areas["ipv6"].focus_set()
            if is_checked
            else self.text_areas["ipv4"].focus_set()
        )
        self.process_text_area("ipv6_text" if is_checked else "ipv4_text")

    def _bind_events(self):
        """绑定事件处理程序"""
        # self.ipv6_entry.bind("<KeyRelease>", self.on_ipv6_instance_change)
        self.ipv6_entry.bind("<<Modified>>", self.on_ipv6_instance_change)
        self.instance_combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)
        self.text_areas["ipv4"].bind("<<Modified>>", self.on_ipv4_entry_change)
        self.text_areas["ipv6"].bind("<<Modified>>", self.on_ipv6_entry_change)
        self.prefix_label.bind("<<LabelModified>>", self.on_prefix_label_change)

        # 配置文本标签
        for area in self.text_areas.values():
            area.tag_config("error", background=self.ERROR_BG_COLOR)

    # 在 _load_ip_instances 方法中添加调试信息
    def _load_ip_instances(self):
        """Read user state, or clean bundled defaults on the first launch."""
        try:
            path = config_path("cfg_ipv6_instance_prefix.json")
            source = path if path.exists() else resource_path("defaults", "cfg_ipv6_instance_prefix.json")
            if source.exists():
                with source.open(encoding="utf-8") as handle:
                    instances = json.load(handle)
            else:
                instances = json.loads(json.dumps(self.DEFAULT_JSON_INSTANCE))
            if not isinstance(instances, dict) or not instances:
                raise ValueError("实例配置为空或格式错误")
            for value in instances.values():
                if not isinstance(value, dict) or not all(key in value for key in ("area", "ipv6", "combo_select")):
                    raise ValueError("实例配置缺少必要字段")
                IPv6Address(value["ipv6"])
            self.ipv6_instances = instances
            self._update_combobox()
            self.instance_combobox.set(next(iter(instances.values()))["combo_select"])
            self.on_combobox_select(None)
        except (OSError, ValueError, TypeError) as error:
            logger.error("加载实例失败", exc_info=True)
            messagebox.showerror("错误", f"无法加载实例配置: {error}")

    # 修改 _save_ip_instances 方法
    def _save_ip_instances(self):
        """Persist private prefixes outside source and package resources."""
        try:
            path = config_path("cfg_ipv6_instance_prefix.json")
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.ipv6_instances, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, path)
            self._update_combobox()
        except OSError:
            logger.error("保存实例失败", exc_info=True)
            messagebox.showerror("错误", "无法保存实例配置")

    def _update_combobox(self):
        """更新Combobox选项"""
        self.instance_combobox["values"] = [
            v["combo_select"] for v in self.ipv6_instances.values()
        ]

    def start_clipboard_monitor(self):
        """启动剪贴板监控线程"""
        if not self.monitoring:
            self.monitoring = True
            self.clipboard_thread = threading.Thread(
                target=self.check_clipboard, daemon=True
            )
            self.clipboard_thread.start()

    def stop_clipboard_monitor(self):
        """停止剪贴板监控"""
        self.monitoring = False

    def check_clipboard(self):
        """检查剪贴板内容并检测IP地址"""
        last_content = ""
        while self.monitoring:
            try:
                # 使用父容器获取剪贴板内容
                current_content = self.parent.clipboard_get()
                if current_content != last_content:
                    last_content = current_content
                    # 检查是否包含IP地址
                    ip_addresses = self.extract_ip_addresses(current_content)

                    if ip_addresses:
                        # 根据当前模式过滤IP地址类型
                        if self.ipv6_to_ipv4.get():
                            # 在IPv6转IPv4模式下，只处理IPv6地址
                            filtered_addresses = [
                                ip for ip in ip_addresses if self.is_valid_ipv6(ip)
                            ]
                        else:
                            # 在普通模式下，只处理IPv4地址
                            filtered_addresses = [
                                ip for ip in ip_addresses if self.is_valid_ipv4(ip)
                            ]

                        # 如果有符合条件的IP地址才显示对话框
                        if filtered_addresses:
                            # 将IP地址用换行符连接起来显示
                            ip_text_display = "\n".join(filtered_addresses)

                            # 弹出提示询问是否转换
                            if messagebox.askyesno(
                                "剪贴板监控",
                                f"检测到IP地址:\n{ip_text_display}\n\n是否转换?",
                            ):
                                # 根据IPv6转IPv4模式决定粘贴到哪个文本框
                                if self.ipv6_to_ipv4.get():
                                    # 在IPv6转IPv4模式下，将IPv6地址追加到IPv6文本框
                                    ipv6_addresses = [
                                        ip
                                        for ip in ip_addresses
                                        if self.is_valid_ipv6(ip)
                                    ]
                                    if ipv6_addresses:
                                        # 追加内容而不是替换
                                        current_content = (
                                            self.text_areas["ipv6"]
                                            .get("1.0", tk.END)
                                            .strip()
                                        )
                                        new_content = (
                                            current_content
                                            + ("\n" if current_content else "")
                                            + "\n".join(ipv6_addresses)
                                        )
                                        self.text_areas["ipv6"].delete("1.0", tk.END)
                                        self.text_areas["ipv6"].insert(
                                            "1.0", new_content
                                        )
                                else:
                                    # 在普通模式下，将IPv4地址追加到IPv4文本框
                                    ipv4_addresses = [
                                        ip
                                        for ip in ip_addresses
                                        if self.is_valid_ipv4(ip)
                                    ]
                                    if ipv4_addresses:
                                        # 追加内容而不是替换
                                        current_content = (
                                            self.text_areas["ipv4"]
                                            .get("1.0", tk.END)
                                            .strip()
                                        )
                                        new_content = (
                                            current_content
                                            + ("\n" if current_content else "")
                                            + "\n".join(ipv4_addresses)
                                        )
                                        self.text_areas["ipv4"].delete("1.0", tk.END)
                                        self.text_areas["ipv4"].insert(
                                            "1.0", new_content
                                        )

            except tk.TclError:
                # 剪贴板访问被拒绝或不可用
                pass
            except Exception as e:
                logger.warning("剪贴板监控出错: %s", e)

            # 等待一段时间再检查
            time.sleep(self.CLIPBOARD_CHECK_INTERVAL)

    def _center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = 1100
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _update_prefix_label(self):
        """更新前缀标签显示"""
        ip_str = self.ipv6_entry.get().strip()
        try:
            # 将输入的IPv6地址转换为IPv6Address对象
            ipv6_addr = IPv6Address(ip_str)
            # 获取扩展格式的IPv6地址
            expanded_ipv6_str = ipv6_addr.exploded
            # 截取前96位
            prefix = ":".join(expanded_ipv6_str.split(":")[:6]) + ":"
            self.prefix_label.configure(text=prefix, fg="green")  # 设置文字颜色为绿色
        except (ValueError, AddressValueError):
            # 如果输入的地址无效，清空前缀标签
            self.prefix_label.configure(text="", fg="green")  # 设置文字颜色为绿色

    def validate_ip(self, ip_str, ip_type):
        """验证IP地址格式"""
        try:
            return isinstance(ip_address(ip_str), ip_type)
        except (ValueError, AddressValueError):
            return False

    def is_error_line(self, ip_area, line_num):
        """判断是否为错误行"""
        return (
            True if "error" in self.text_areas[ip_area].tag_names(line_num) else False
        )

    def ip_converse(self, ip_list, conver_type):
        """IP转换核心逻辑"""
        converted = []
        for ip_str in ip_list:
            if ip_str == "":
                converted.append(ip_str)
                continue
            if conver_type == "4to6":

                prefix = self.prefix_label.cget("text")
                embedded_ipv6_str = f"{prefix}{ip_str}"
                format_type = self.ipv6_format_var.get()
                ipv6_addr = IPv6Address(embedded_ipv6_str)

                if format_type == "exploded":
                    ipv6_addr = ipv6_addr.exploded
                elif format_type == "compressed":
                    ipv6_addr = ipv6_addr.compressed
                elif format_type == "embedded":
                    ipv6_addr = str(prefix + ip_str)
                elif format_type == "noneleadingzero":
                    ipv6_addr = ":".join(
                        part.lstrip("0") or "0"
                        for part in ipv6_addr.exploded.split(":")
                    )
                converted.append(str(ipv6_addr))

            elif conver_type == "6to4":

                ipv4_addr = self.extract_ipv4_from_ipv6(ip_str)
                converted.append(ipv4_addr)

            elif conver_type == "6to6":

                ipv6_addr = IPv6Address(ip_str)
                format_type = self.ipv6_format_var.get()
                if format_type == "exploded":
                    ipv6_addr = ipv6_addr.exploded
                elif format_type == "compressed":
                    ipv6_addr = ipv6_addr.compressed
                elif format_type == "embedded":
                    # 提取前96位和后32位
                    ipv6_int = int(ipv6_addr)
                    # ipv6_high_96 = ipv6_int >> 32
                    ipv4_int = ipv6_int & 0xFFFFFFFF
                    ipv4_addr = IPv4Address(ipv4_int)
                    # 拼接前96位和IPv4地址
                    ipv6_high_96_str = ipv6_addr.exploded.rsplit(":", 2)[0]
                    ipv6_addr = f"{ipv6_high_96_str}:{ipv4_addr}"
                elif format_type == "noneleadingzero":
                    ipv6_addr = ":".join(
                        part.lstrip("0") or "0"
                        for part in ipv6_addr.exploded.split(":")
                    )
                converted.append(str(ipv6_addr))

        return converted

    # 业务逻辑方法
    def on_combobox_select(self, event):
        """处理Combobox选择事件"""
        selected = self.instance_combobox.get()
        for details in self.ipv6_instances.values():
            if details["combo_select"] == selected:
                self.ipv6_entry.delete(0, tk.END)
                self.ipv6_entry.insert(0, details["ipv6"])
                self.area_entry.delete(0, tk.END)
                self.area_entry.insert(0, details["area"])
                break

    def on_ipv6_instance_change(self, event):
        """IPv6实例输入变更事件处理"""
        ip_str = self.ipv6_entry.get().strip()
        if not ip_str:
            # 内容为空时，恢复默认状态
            self.ipv6_entry.configure(background="white")
            self.prefix_label.configure(text="", fg="green")
            return

        if self.validate_ip(ip_str, IPv6Address):
            # 正常状态
            self.ipv6_entry.configure(background="white")
            self._update_prefix_label()
        else:
            # 错误状态
            self.ipv6_entry.configure(background=self.ERROR_BG_COLOR)
            self.prefix_label.config(
                text="(格式错误)", fg="red"
            )  # 设置文字颜色为红色，并添加后缀

    def on_prefix_label_change(self, event):
        self.process_text_area("format_prefixlabel")

    def on_ipv4_entry_change(self, event):
        self.text_areas["ipv4"].edit_modified(False)
        self.text_areas["ipv6"].edit_modified(False)
        if not self.ipv6_to_ipv4.get():
            self.process_text_area("ipv4_text")
        else:
            return

    def on_ipv6_entry_change(self, event):
        self.text_areas["ipv4"].edit_modified(False)
        self.text_areas["ipv6"].edit_modified(False)
        if self.ipv6_to_ipv4.get():
            self.process_text_area("ipv6_text")
        else:
            return

    # 获取转换配置
    def _get_conversion_config(self, event_source):
        CONVERSION_MAP = {
            "format_radiobutton": ConversionConfig("6to6", "ipv6", "ipv6", IPv6Address),
            "format_prefixlabel": ConversionConfig("4to6", "ipv4", "ipv6", IPv4Address),
            "ipv4_text": ConversionConfig("4to6", "ipv4", "ipv6", IPv4Address),
            "ipv6_text": ConversionConfig("6to4", "ipv6", "ipv4", IPv6Address),
        }
        return CONVERSION_MAP.get(event_source)

    def process_text_area(self, event_source=None, event=None):
        """处理文本区域内容更新"""

        # 获取转换配置
        if not (config := self._get_conversion_config(event_source)):
            return
        ip_lines = self.text_areas[config.src_field].get("1.0", tk.END).splitlines()

        # 从后往前删除空行
        while ip_lines and not ip_lines[-1].strip():
            ip_lines.pop()

        valid_or_space_ips = []
        for i, line in enumerate(ip_lines):
            line = line.strip()
            if self.validate_ip(line, config.format_cls):
                valid_or_space_ips.append(line)
                self.text_areas[config.src_field].tag_remove(
                    "error", f"{i+1}.0", f"{i+1}.end"
                )
            else:
                valid_or_space_ips.append("")
                self.text_areas[config.src_field].tag_add(
                    "error", f"{i+1}.0", f"{i+1}.end"
                )

        converted_ips = self.ip_converse(valid_or_space_ips, config.conversion_type)
        self._update_text_area(config.dst_field, converted_ips)

        self._update_script_area()

    def _update_text_area(self, target, contents):
        """更新指定文本区域内容"""
        # 保存当前文本区域的状态
        original_state = self.text_areas[target].cget("state")
        self.text_areas[target].config(state="normal")
        self.text_areas[target].delete("1.0", tk.END)
        for i, content in enumerate(contents, 1):
            self.text_areas[target].insert(f"{i}.0", f"{content}\n")
        # 恢复文本区域的状态
        self.text_areas[target].config(state=original_state)

    def _update_script_area(self, *args):
        """更新脚本区域内容"""
        # 根据不同的vendor_variable为prefix_config赋值不同厂商风格的前后缀
        vendor = self.vendor_var.get() if hasattr(self, "vendor_var") else "huawei"

        if vendor == "huawei":
            # 华为风格：address + 掩码位数
            prefix_config = {"ipv4": ("address ", " 32"), "ipv6": ("address ", " 128")}
        elif vendor == "h3c":
            # 华三风格：ip address + ipv6 address（无掩码位数）
            prefix_config = {
                "ipv4": ("network host address ", ""),
                "ipv6": ("network host address ", ""),
            }
        else:
            # 默认华为风格
            prefix_config = {"ipv4": ("address ", " 32"), "ipv6": ("address ", " 128")}

        scripts = []
        for ip_text in ["ipv4", "ipv6"]:
            if self.script_prefix_var.get():
                prefix, postfix = prefix_config[ip_text]
            else:
                prefix, postfix = "", ""

            # for i, line in enumerate(self.text_areas[ip_text].get("1.0", tk.END).splitlines()):
            #     print(self.text_areas[ip_text].tag_names(f"{i+1}.0"))
            scripts += [
                f"{prefix}{line}{postfix}"
                for i, line in enumerate(
                    self.text_areas[ip_text].get("1.0", tk.END).splitlines()
                )
                if line.strip() and not self.is_error_line(ip_text, f"{i+1}.0")
            ] + [""]

        self._update_text_area("script", scripts)

    def extract_ipv4_from_ipv6(self, ip_str):
        """从IPv6地址中提取IPv4地址"""
        ipv6 = IPv6Address(ip_str)
        ipv4_int = int(ipv6) & 0xFFFFFFFF
        ipv4_addr = IPv4Address(ipv4_int)
        return str(ipv4_addr)

    def add_ipv6_instance(self):
        """添加IPv6实例"""
        area = self.area_entry.get().strip()
        ipv6 = self.ipv6_entry.get().strip()

        if not area:
            messagebox.showerror("错误", "区域名称不能为空")
            return
        if not self.validate_ip(ipv6, IPv6Address):
            messagebox.showerror("错误", "IPv6地址格式不正确")
            return

        # 检查重复
        if any(v["area"] == area for v in self.ipv6_instances.values()):
            messagebox.showerror("错误", "区域名称已存在")
            return
        if any(v["ipv6"] == ipv6 for v in self.ipv6_instances.values()):
            messagebox.showerror("错误", "IPv6地址已存在")
            return

        new_key = str(len(self.ipv6_instances) + 1)
        self.ipv6_instances[new_key] = {
            "area": area,
            "ipv6": ipv6,
            "combo_select": f"{ipv6}（{area}）",
        }
        self._save_ip_instances()
        messagebox.showinfo("成功", "实例添加成功")

    def delete_ipv6_instance(self):
        """删除IPv6实例"""
        selected = self.instance_combobox.get()
        if not selected:
            messagebox.showerror("错误", "请选择要删除的实例")
            return

        for key, details in list(self.ipv6_instances.items()):
            if details["combo_select"] == selected:
                del self.ipv6_instances[key]
                self._save_ip_instances()
                self.instance_combobox.set("")
                messagebox.showinfo("成功", "实例删除成功")
                return

    def clear_ip_area(self):
        """清空文本区域"""

        if not self.ipv6_to_ipv4.get():
            self.text_areas["ipv4"].delete("1.0", tk.END)
            self.root.after(100, self.text_areas["ipv4"].focus_set)
        else:
            self.text_areas["ipv6"].delete("1.0", tk.END)
            self.root.after(100, self.text_areas["ipv6"].focus_set)

    def copy_script_to_clipboard(self, ip_type=None):
        """复制脚本到剪贴板

        Args:
            ip_type: 可选参数，指定要复制的IP类型
                    - None: 复制全部内容
                    - "ipv4": 仅复制IPv4相关脚本
                    - "ipv6": 仅复制IPv6相关脚本
        """
        if "script" not in self.text_areas:
            return

        script_content = self.text_areas["script"].get("1.0", tk.END).strip()

        if ip_type is None:
            # 复制全部内容
            result = script_content
        else:
            # 根据ip_type筛选相应的内容
            lines = script_content.splitlines()
            filtered_lines = []

            if ip_type == "ipv4":
                # 复制IPv4部分（在空行之前的内容）
                for line in lines:
                    if line.strip() == "":
                        break  # 遇到空行就停止
                    if line.strip():  # 只添加非空行
                        filtered_lines.append(line)

            elif ip_type == "ipv6":
                # 复制IPv6部分（空行之后的内容）
                empty_line_found = False
                for line in lines:
                    if line.strip() == "":
                        empty_line_found = True
                        continue  # 跳过空行
                    if empty_line_found and line.strip():  # 空行之后的非空行
                        filtered_lines.append(line)

            result = "\n".join(filtered_lines)

        # 清除剪贴板并添加内容
        self.root.clipboard_clear()
        self.root.clipboard_append(result)

    def _on_script_toggle(self):
        """处理脚本Checkbutton切换事件"""
        is_enabled = self.script_prefix_var.get()

        # 控制Radiobutton的有效性
        radio_state = "normal" if is_enabled else "disabled"
        self.huawei_radio.config(state=radio_state)
        self.h3c_radio.config(state=radio_state)

        # 更新脚本区域
        self._update_script_area()

    def set_initial_focus(self):
        """设置初始焦点到主要输入框"""
        try:
            # 确保text_areas字典存在且包含ipv4键
            if hasattr(self, "text_areas") and "ipv4" in self.text_areas:
                self.text_areas["ipv4"].focus_set()
            elif hasattr(self, "ipv6_entry") and self.ipv6_entry:
                # 备选方案：如果text_areas不存在，尝试设置ipv6_entry焦点
                self.ipv6_entry.focus_set()
            else:
                # 最后的备选方案：尝试设置任何可用的输入框焦点
                for attr_name in ["instance_combobox", "area_entry"]:
                    if hasattr(self, attr_name) and getattr(self, attr_name):
                        getattr(self, attr_name).focus_set()
                        break
        except Exception as e:
            logger.debug("设置IP转换器焦点时出错: %s", e)


# 工具提示类


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.id = None
        self.x = self.y = 0

    def show_tooltip(self):
        "Display text in tooltip window"
        if self.tooltip:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tooltip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", 8, "normal"),
        )
        label.pack(ipadx=1)

    def hide_tooltip(self):
        tw = self.tooltip
        self.tooltip = None
        if tw:
            tw.destroy()


def create_tool_tip(widget, text):
    """为指定的widget创建工具提示"""
    tool_tip = ToolTip(widget, text)

    def enter(event):
        tool_tip.show_tooltip()

    def leave(event):
        tool_tip.hide_tooltip()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)

    return tool_tip


if __name__ == "__main__":
    logging.info("Starting application")
    """独立运行调试模式"""
    print("正在启动独立的IP计算器调试模式...")

    try:
        root = tk.Tk()
        root.title("IPv4/IPv6 转换器 - 独立调试模式")
        root.withdraw()  # 先隐藏窗体
        converter = IPConverter(root)
        converter._center_window()  # 居中窗体
        root.update_idletasks()  # 确保所有布局和绘图任务完成
        root.deiconify()  # 显示窗体
        root.mainloop()
    except Exception as e:
        # logging.error(f"Application failed to start: {e}", exc_info=True)
        print(e)
