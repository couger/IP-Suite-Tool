"""
IP地址空间计算器模块

功能：
1. 计算IPv4和IPv6地址的网络信息
2. 支持掩码/前缀计算
3. 支持反向参数推导
"""

import os
import json
import logging
import ipaddress
import tkinter as tk
from tkinter import ttk, messagebox

# 统一日志配置
try:
    from utils.logger_config import setup_module_logger

    logger = setup_module_logger("ip_calculator", logging.INFO)
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("ip_calculator")

# 导入网络空间模型
from models.model_network_space import NetworkSpace

# 新增：用于存储生成的网段结果，供子窗口使用
_generated_subnets_cache = []


# 定义默认参数映射常量，避免在多个异常处理块中重复定义
DEFAULT_PARAM_MAPPING = {
    "ip_address": "ip_component",
    "ip_type": "ip_type_component",
    "network_address": "network_component",
    "broadcast_address": "broadcast_component",
    "subnet_mask": "mask_DDN_component",
    "wildcard_mask": "wildcard_component",
    "cidr_notation": "cidr_component",
    "first_host_ip": "first_ip_component",
    "last_host_ip": "last_ip_component",
    "available_host_count": "available_count_component",
    "possible_subnet_count": "available_subnet_component",
    "subnet_position_index": "subnet_order_component",
    "host_index_in_subnet": "ip_order_component",
    "address_family_bit_length": "address_family_bit_length_component",
    "mask_length": "mask_length_component",
}


class IPSubnetCalculator:
    def __init__(self, parent):
        # 首先创建主框架
        self.root = parent
        self.frame = ttk.Frame(parent)

        # 从配置文件加载参数映射，带改进的错误处理
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # 使用os.path.join正确处理路径分隔符
            config_path = os.path.join(script_dir, "cfgs", "cfg_mapping_config.json")

            # 验证路径安全性
            normalized_path = os.path.normpath(config_path)
            if not normalized_path.startswith(os.path.normpath(script_dir)):
                raise ValueError("Invalid configuration file path")

            with open(config_path, "r", encoding="utf-8") as f:
                # config_data = json.load(f)
                # self.param_mapping = {item['model_property']: item['gui_element']
                #                       for item in config_data['parameter_mappings']}
                self.param_mapping = json.load(f)
        except FileNotFoundError:
            print("警告: 找不到 cfg_mapping_config.json 文件，使用默认映射")
            # 默认映射，以防配置文件丢失
            self.param_mapping = DEFAULT_PARAM_MAPPING.copy()
        except json.JSONDecodeError as e:
            print(f"警告: cfg_mapping_config.json 文件格式错误: {e}，使用默认映射")
            # 使用默认映射
            self.param_mapping = DEFAULT_PARAM_MAPPING.copy()
        except ValueError as e:
            print(f"警告: 配置文件路径验证失败: {e}，使用默认映射")
            self.param_mapping = DEFAULT_PARAM_MAPPING.copy()
        except PermissionError as e:
            print(f"警告: 无法访问配置文件: {e}，使用默认映射")
            self.param_mapping = DEFAULT_PARAM_MAPPING.copy()
        except Exception as e:
            print(f"警告: 加载配置文件时发生未知错误: {e}，使用默认映射")
            self.param_mapping = DEFAULT_PARAM_MAPPING.copy()

        # 初始化所有将要用到的属性
        self.ip_entry = None
        self.mask_entry = None
        self.ip_type_component = None
        self.network_component = None
        self.broadcast_component = None
        self.subnet_mask_component = None
        self.wildcard_component = None
        self.cidr_component = None
        self.first_ip_component = None
        self.last_ip_component = None
        self.available_count_component = None
        self.available_subnet_component = None
        self.subnet_order_component = None
        self.ip_order_component = None
        self.address_family_bit_length_component = None
        self.available_count_frame = None
        self.mask_len_component = None
        self.mask_DDN_component = None
        self.ip_component = None  # 显示IP地址
        self.mask_length_component = None  # 显示掩码长度
        # self.host_count_component = None  # 显示主机数量
        # self.subnet_count_component = None  # 显示子网数量

        # 创建模型实例
        self.model = NetworkSpace()
        # 注册自身为观察者
        self.model.add_observer(self)

        logger.debug("IPSubnetCalculator initialized - attributes set to None")
        self._create_widgets()

        # 验证GUI元素是否与配置文件匹配
        self._verify_gui_elements()

        # 初始化output_map，将模型属性映射到GUI组件实例（必须在_create_widgets后调用）
        self.output_map = self._generate_output_map()

        # 检查是否在创建组件后有默认值
        logger.debug(
            "IP Entry initial value: %r",
            self.ip_entry.get() if self.ip_entry else "N/A",
        )
        logger.debug(
            "Mask Entry initial value: %r",
            self.mask_entry.get() if self.mask_entry else "N/A",
        )

        # 使用 after 方法在所有组件初始化完成后设置焦点
        self.root.after(
            100, lambda: self.ip_entry.focus_set() if self.ip_entry else None
        )

        self.frame.pack(fill=tk.BOTH, expand=True)

        # 集中绑定所有事件
        self._bind_events()

    def _bind_events(self):
        """集中绑定所有事件"""
        # IP输入框回车跳转到掩码输入框
        if self.ip_entry and self.mask_entry:
            self.ip_entry.bind("<Return>", lambda event: self.mask_entry.focus_set())

        # 掩码输入框回车触发计算
        if self.mask_entry:
            self.mask_entry.bind("<Return>", lambda event: self._handle_mask_enter())

        # 可用主机数输入框回车触发计算
        if self.available_count_component:
            self.available_count_component.bind(
                "<Return>", lambda event: self.set_ip_and_available_count()
            )

        # 可用子网数输入框回车触发计算
        if self.available_subnet_component:
            self.available_subnet_component.bind(
                "<Return>", lambda event: self.set_ip_and_available_subnet_count()
            )

    def _handle_mask_enter(self):
        """处理掩码输入框的回车事件"""
        if self.mask_entry is not None:
            mask_value = self.mask_entry.get().strip()
        else:
            mask_value = ""
        if "." in mask_value:  # 包含点号，认为是子网掩码
            self.set_ip_and_subnet_mask()
        else:  # 否则认为是前缀长度
            self.set_ip_and_mask_length()

    def _verify_gui_elements(self):
        """验证GUI元素是否与配置文件匹配"""
        missing_elements = []

        for model_prop, gui_element in self.param_mapping.items():
            if not hasattr(self, gui_element):
                missing_elements.append(
                    f"模型属性'{model_prop}'对应的GUI元素'{gui_element}'未定义"
                )

        if missing_elements:
            error_msg = "GUI配置验证失败，以下元素缺失：\n" + "\n".join(
                missing_elements
            )
            print(f"ERROR: {error_msg}")
            messagebox.showerror("配置错误", error_msg)
        else:
            print("GUI配置验证通过：所有模型属性都有对应的GUI元素")

    def _generate_output_map(self):
        """根据self.param_mapping生成output_map，将模型属性映射到GUI组件实例"""
        output_map = {}
        for model_prop, gui_element_name in self.param_mapping.items():
            if hasattr(self, gui_element_name):
                gui_element = getattr(self, gui_element_name)
                output_map[model_prop] = gui_element
            else:
                print(f"警告: GUI元素'{gui_element_name}'不存在于实例中")
        return output_map

    def on_model_change(self, prop_name, value):
        """当模型属性发生变化时的回调函数"""
        # 处理错误信息 - 弹出消息窗口
        if prop_name == "has_error" and value:  # 只有当有错误时才弹窗
            error_msg = getattr(self.model, "error_message", "")
            if error_msg:
                messagebox.showerror("模型计算错误", str(error_msg))

        # 根据属性名更新相应的GUI组件（排除错误相关属性）
        if prop_name not in ["has_error", "error_message"]:
            output_widget = self.output_map.get(prop_name)
            if output_widget:
                # 保存当前状态
                # current_state = output_widget.cget('state')

                # 检查值是否为空或无效 - 最小改动的关键部分
                is_empty = (
                    value is None
                    or (isinstance(value, str) and value.strip() == "")
                    or (isinstance(value, (int, float)) and value < 0)
                )

                # 设置为正常状态以允许修改
                if isinstance(output_widget, ttk.Entry):
                    output_widget.config(state="normal")
                    # 清空并插入新值
                    output_widget.delete(0, tk.END)

                    if is_empty:
                        # 如果值为空，显示N/A并禁用控件
                        output_widget.insert(0, "N/A")
                        output_widget.config(state="disabled")
                    else:
                        output_widget.insert(0, str(value))
                        # 恢复原始状态（除了默认禁用的）
                        if prop_name not in [
                            "subnet_position_index",
                            "host_index_in_subnet",
                            "subnet_mask",
                            "wildcard_mask",
                        ]:
                            output_widget.config(state="normal")
                        else:
                            output_widget.config(state="readonly")
                elif isinstance(output_widget, ttk.Label):
                    # Label 控件的处理逻辑
                    if is_empty:
                        output_widget.config(text="N/A", foreground="gray")
                    else:
                        output_widget.config(text=str(value), foreground="black")

    def reset_fields(self):
        """重置所有输入和输出字段"""
        # 检查控件是否存在后再操作
        if self.ip_entry is not None:
            self.ip_entry.delete(0, tk.END)
        if self.mask_entry is not None:
            self.mask_entry.delete(0, tk.END)

        # 清空所有输出文本框
        # 原来的attrs_to_reset列表方式（已注释）
        # attrs_to_reset = [
        #     "ip_type_component", "network_component", "broadcast_component",
        #     "subnet_mask_component", "wildcard_component", "cidr_component",
        #     "mask_len_component",
        #     "available_count_component", "first_ip_component", "last_ip_component",
        #     "ip_order_component", "available_subnet_component", "subnet_order_component",
        #     "address_family_bit_length_component", "mask_length_component",
        # ]
        #
        # for attr_name in attrs_to_reset:
        #     if hasattr(self, attr_name) and getattr(self, attr_name) is not None:
        #         widget = getattr(self, attr_name)
        #         if isinstance(widget, ttk.Entry):
        #             widget.delete(0, tk.END)
        #         elif isinstance(widget, ttk.Label):
        #             widget.config(text="")

        # 新的逻辑：遍历所有GUI组件进行重置
        for attr_name in dir(self):
            # 获取属性
            attr = getattr(self, attr_name)
            # 检查是否是Entry或Label组件
            if isinstance(attr, ttk.Entry):
                # 对于只读的Entry，需要临时启用再清空
                if attr.cget("state") != "normal":
                    # current_state = attr.cget('state')
                    attr.config(state="normal")
                    attr.delete(0, tk.END)
                    if attr_name in [
                        "subnet_order_component",
                        "ip_order_component",
                        "mask_DDN_component",
                        "wildcard_component",
                    ]:
                        attr.config(state="readonly")
                else:
                    attr.delete(0, tk.END)
            elif isinstance(attr, ttk.Label):
                attr.config(text="")

    def _create_widgets(self):
        # 配置frame的网格权重，使其可以扩展
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        # 主容器框架 - 只使用单列布局
        main_container = ttk.Frame(self.frame)
        main_container.grid(row=1, column=0, sticky="nsew")
        main_container.columnconfigure(0, weight=1)

        # 地址输入区 - 将IP输入和IP类型放在同一行
        input_frame = ttk.Frame(main_container)
        input_frame.grid(row=0, column=0, pady=10, padx=10, sticky="ew")

        ttk.Label(input_frame, text="输入IP:").grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )
        self.ip_entry = ttk.Entry(input_frame, width=20)
        self.ip_entry.grid(row=0, column=1, padx=5)

        # IP地址类型标签放在IP输入框旁边
        ttk.Label(input_frame, text="类型:").grid(
            row=0, column=2, padx=(10, 5), pady=2, sticky="w"
        )
        self.ip_type_component = ttk.Label(input_frame, width=5, anchor="w")
        self.ip_type_component.grid(row=0, column=3, padx=5)

        # 添加掩码总长度标签
        ttk.Label(input_frame, text="掩码总长度:").grid(
            row=0, column=4, padx=(10, 5), pady=2, sticky="w"
        )
        self.address_family_bit_length_component = ttk.Label(
            input_frame, width=15, anchor="w"
        )
        self.address_family_bit_length_component.grid(row=0, column=5, padx=5)

        # 其他参数区域 - 分别显示/设置各项参数
        result_frame = ttk.Frame(main_container)
        result_frame.grid(
            row=1, column=0, pady=10, padx=10, sticky="nsew"
        )  # 修改：row从2改为1

        # 配置结果显示文本框
        # 添加"掩码/前缀"行，使用与其他行相同的布局结构
        # 先创建标签和容器
        # 添加序号0
        ttk.Label(result_frame, text="0", width=2, anchor="center").grid(
            row=0, column=0, padx=(5, 0), pady=2, sticky="w"
        )
        ttk.Label(result_frame, text="掩码/前缀:").grid(
            row=0, column=1, padx=(0, 5), pady=2, sticky="w"
        )
        mask_prefix_container = ttk.Frame(result_frame)
        mask_prefix_container.grid(row=0, column=2, padx=5, pady=2, sticky="ew")

        # 掩码/前缀输入框
        self.mask_entry = ttk.Entry(mask_prefix_container)
        # self.mask_entry.grid(row=0, column=2, padx=5)
        self.mask_entry.pack(side=tk.LEFT)

        # 计算按钮 - 根据内容判断执行哪个计算函数
        def handle_calculation():
            """根据掩码输入框的内容判断是掩码还是前缀长度"""
            if self.mask_entry is not None:
                mask_value = self.mask_entry.get().strip()
            else:
                mask_value = ""
            if "." in mask_value:  # 包含点号，认为是子网掩码
                self.set_ip_and_subnet_mask()
            else:  # 否则认为是前缀长度
                self.set_ip_and_mask_length()

        calc_by_mask_btn = ttk.Button(
            mask_prefix_container,
            text="计算",
            command=handle_calculation,
            style="Accent.TButton",
        )
        calc_by_mask_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 添加点分十进制显示
        ttk.Label(mask_prefix_container, text="点分十进制:", width=12, anchor="w").pack(
            side=tk.LEFT, padx=(5, 5)
        )
        self.mask_DDN_component = ttk.Entry(
            mask_prefix_container, width=15, state="readonly", justify="left"
        )
        self.mask_DDN_component.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)

        # 添加反掩码显示
        ttk.Label(mask_prefix_container, text="反掩码:", width=8, anchor="w").pack(
            side=tk.LEFT, padx=(5, 5)
        )
        self.wildcard_component = ttk.Entry(
            mask_prefix_container, width=60, state="readonly", justify="left"
        )
        self.wildcard_component.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)

        # 添加序号1
        ttk.Label(result_frame, text="1", width=2, anchor="center").grid(
            row=1, column=0, padx=(5, 0), pady=2, sticky="w"
        )
        ttk.Label(result_frame, text="主机数量:").grid(
            row=1, column=1, padx=(0, 5), pady=2, sticky="w"
        )
        available_count_container = ttk.Frame(result_frame)
        available_count_container.grid(row=1, column=2, padx=5, pady=2, sticky="ew")

        self.available_count_component = ttk.Entry(available_count_container)
        self.available_count_component.pack(side=tk.LEFT, fill=tk.X, expand=True)

        calc_by_count_btn = ttk.Button(
            available_count_container,
            text="计算",
            command=self.set_ip_and_available_count,
            style="Accent.TButton",
        )
        calc_by_count_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 添加IP序号显示框
        ttk.Label(
            available_count_container, text="当前IP是第:", width=12, anchor="w"
        ).pack(side=tk.LEFT, padx=(5, 5))
        self.ip_order_component = ttk.Entry(
            available_count_container, width=10, state="readonly", justify="left"
        )
        self.ip_order_component.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        self.ip_order_component_suffix = ttk.Label(
            available_count_container, text="台主机", width=80, anchor="w"
        )
        self.ip_order_component_suffix.pack(side=tk.LEFT, padx=(5, 5))

        # 添加序号2
        ttk.Label(result_frame, text="2", width=2, anchor="center").grid(
            row=2, column=0, padx=(5, 0), pady=2, sticky="w"
        )
        ttk.Label(result_frame, text="子网数量:").grid(
            row=2, column=1, padx=(0, 5), pady=2, sticky="w"
        )
        available_subnet_container = ttk.Frame(result_frame)
        available_subnet_container.grid(row=2, column=2, padx=5, pady=2, sticky="ew")

        self.available_subnet_component = ttk.Entry(available_subnet_container)
        self.available_subnet_component.pack(side=tk.LEFT, fill=tk.X, expand=True)

        calc_by_subnet_btn = ttk.Button(
            available_subnet_container,
            text="计算",
            command=self.set_ip_and_available_subnet_count,
            style="Accent.TButton",
        )
        calc_by_subnet_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 添加子网序号显示框
        ttk.Label(
            available_subnet_container, text="当前子网是第:", width=12, anchor="w"
        ).pack(side=tk.LEFT, padx=(5, 5))
        self.subnet_order_component = ttk.Entry(
            available_subnet_container, width=10, state="readonly", justify="left"
        )
        self.subnet_order_component.pack(
            side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True
        )
        self.subnet_order_component_suffix = ttk.Label(
            available_subnet_container, text="个子网", width=80, anchor="w"
        )
        self.subnet_order_component_suffix.pack(side=tk.LEFT, padx=(5, 5))

        labels_and_attrs = [
            ("CIDR表示法:", "cidr_component", "entry"),
            ("网络地址:", "network_component", "entry"),
            ("起始主机地址:", "first_ip_component", "entry"),  # 新增：起始主机地址
            ("末尾主机地址:", "last_ip_component", "entry"),  # 新增：末尾主机地址
            ("广播地址:", "broadcast_component", "entry"),
        ]

        # 创建标签和文本框，添加序号 (从序号3开始)
        # rows = len(labels_and_attrs)
        for i, (label_text, attr_name, widget_type) in enumerate(labels_and_attrs):
            # 添加序号 (3-12)
            ttk.Label(result_frame, text=str(i + 3), width=2, anchor="center").grid(
                row=i + 3, column=0, padx=(5, 0), pady=2, sticky="w"
            )
            ttk.Label(result_frame, text=label_text).grid(
                row=i + 3, column=1, padx=(0, 5), pady=2, sticky="w"
            )

            # 根据 widget_type 创建不同类型的控件
            if widget_type == "label":
                setattr(self, attr_name, ttk.Label(result_frame, width=30, anchor="w"))
            else:  # 默认为 entry
                setattr(self, attr_name, ttk.Entry(result_frame, width=30))

            getattr(self, attr_name).grid(
                row=i + 3, column=2, padx=5, pady=2, sticky="ew"
            )

        # 配置列权重以便文本框扩展
        result_frame.columnconfigure(2, weight=1)

        # 配置行权重以便结果区域扩展
        # 修改：row从2改为1，因为result_frame现在在row=1
        main_container.rowconfigure(1, weight=1)
        main_container.columnconfigure(0, weight=1)

        # 配置主容器权重
        self.frame.rowconfigure(1, weight=1)

        # 底部工具栏 - 添加重置按钮和其他操作按钮
        toolbar_frame = ttk.Frame(main_container)
        toolbar_frame.grid(row=2, column=0, pady=10, padx=10, sticky="ew")
        toolbar_frame.columnconfigure(1, weight=1)  # 让重置按钮靠右对齐

        # 添加一些说明文字或空白占位
        ttk.Label(toolbar_frame, text="操作工具:").pack(side=tk.LEFT, padx=(0, 10))

        # 后续网段生成控件
        self._build_subnet_generation_ui(toolbar_frame)

        # 重置按钮 - 放在右侧，避免误触
        reset_btn = ttk.Button(
            toolbar_frame,
            text="重置",
            command=self.reset_fields,
            style="Secondary.TButton",  # 使用次要按钮样式
        )
        reset_btn.pack(side=tk.RIGHT)

        # 添加调试信息
        print(
            "DEBUG: IPSubnetCalculator widgets created - first_ip_component and last_ip_component created"
        )

    def _validate_ip_for_calculation(self, ip_str):
        """验证IP地址是否可用于计算，排除特殊用途地址"""
        try:
            ip = ipaddress.ip_address(ip_str)

            # 检查是否为IPv4地址
            if isinstance(ip, ipaddress.IPv4Address):
                # 排除0.0.0.0/8 (0.x.x.x) - 除非是0.0.0.0本身用于特殊目的
                if ip.packed[0] == 0:
                    return False, "0.x.x.x地址段不可用于子网计算"

                # 排除127.x.x.x - 回环地址
                if ip.packed[0] == 127:
                    return False, "127.x.x.x是回环地址，不可用于子网计算"

                # 排除255.255.255.255 - 广播地址
                if ip_str == "255.255.255.255":
                    return False, "255.255.255.255是广播地址，不可用于子网计算"

            elif isinstance(ip, ipaddress.IPv6Address):
                # 排除未指定地址 :: 或 ::1 (回环)
                if ip_str.lower() in ["::", "::1"]:
                    return False, "无效的IPv6地址，不可用于子网计算"

                # 检查是否为未指定地址 (::)
                if ip.packed == b"\x00" * 16:
                    return False, "IPv6未指定地址 (::) 不可用于子网计算"

        except ValueError:
            return False, "无效的IP地址格式"

        return True, ""

    def _is_valid_netmask(self, mask_str):
        """检查是否为有效的子网掩码（复制自NetworkSpace模型）"""
        import re

        # 检查格式是否为xxx.xxx.xxx.xxx
        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", mask_str):
            return False

        # 分割成4个八位组
        octets = [int(x) for x in mask_str.split(".")]

        # 检查每个八位组是否在有效范围内
        for octet in octets:
            if octet < 0 or octet > 255:
                return False

        # 检查掩码是否是连续的1后面跟连续的0
        # 即掩码不能是类似 11110111.11111111.00000000.00000000 这样的不连续形式
        mask_str_binary = "".join(
            [bin(int(x))[2:].zfill(8) for x in mask_str.split(".")]
        )
        # 检查是否有"01"子串，如果有，则表示不连续
        if "01" in mask_str_binary:
            return False

        return True

    def set_ip_and_mask_length(self):
        """根据输入的IP地址和掩码长度设置模型属性"""
        try:
            if self.ip_entry is None:
                raise ValueError("IP地址输入框未初始化")
            if self.mask_entry is None:
                raise ValueError("掩码输入框未初始化")

            ip_str = self.ip_entry.get().strip()
            mask_str = self.mask_entry.get().strip()

            if not ip_str:
                raise ValueError("请输入IP地址")
            if not mask_str:
                raise ValueError("请输入掩码/前缀")

            # 验证IP地址是否适用于计算
            is_valid, error_msg = self._validate_ip_for_calculation(ip_str)
            if not is_valid:
                raise ValueError(error_msg)

            # 使用批量更新机制避免频繁GUI刷新
            self.model.start_batch_update()

            # 通过设置模型的IP和掩码长度属性来触发计算
            self.model.ip_address = ip_str  # 修改：将ip改为ip_address
            self.model.mask_length = int(mask_str)

            logger.debug("Model state after set_ip_and_mask_length: %s", self.model)

            # 结束批量更新，触发一次性通知
            self.model.end_batch_update()

        except ValueError as e:
            error_msg = str(e)
            messagebox.showerror("错误", error_msg)

            # 根据错误类型将焦点设置到相应输入框
            if "请输入IP地址" in error_msg and self.ip_entry:
                self.ip_entry.focus_set()
            elif "请输入掩码/前缀" in error_msg and self.mask_entry:
                self.mask_entry.focus_set()
            elif "invalid literal" in error_msg and self.mask_entry:
                self.mask_entry.focus_set()
            elif self.ip_entry:
                # 其他错误情况，默认聚焦到IP输入框
                self.ip_entry.focus_set()

        except Exception as e:
            messagebox.showerror("错误", f"计算出错: {str(e)}")
            # 发生异常时聚焦到IP输入框
            if self.ip_entry:
                self.ip_entry.focus_set()

    def set_ip_and_available_count(self):
        """根据输入IP和可用IP数量设置模型属性"""
        try:
            # 检查控件是否存在后再获取值
            if self.ip_entry is None:
                raise ValueError("IP地址输入框未初始化")
            if self.available_count_component is None:
                raise ValueError("可用IP数量组件未初始化")

            ip_str = self.ip_entry.get().strip()
            count_str = self.available_count_component.get().strip()

            logger.debug(
                "set_ip_and_available_count input: ip=%r, available_count=%r",
                ip_str,
                count_str,
            )

            if not ip_str:
                raise ValueError("请输入IP地址")

            if not count_str:
                raise ValueError("请输入可用IP数量")

            count = int(count_str)
            if count <= 0:
                raise ValueError("可用IP数量必须大于0")

            # 验证IP地址是否适用于计算
            is_valid, error_msg = self._validate_ip_for_calculation(ip_str)
            if not is_valid:
                raise ValueError(error_msg)

            # 使用批量更新机制避免频繁GUI刷新
            self.model.start_batch_update()

            # 通过设置模型的IP和可用IP数量属性来触发计算
            self.model.ip_address = ip_str  # 修改：将ip改为ip_address
            self.model.available_host_count = count

            # 同步掩码位输入框
            if self.mask_entry is not None:
                self.mask_entry.delete(0, tk.END)
                self.mask_entry.insert(0, str(self.model.mask_length))

            # 结束批量更新，触发一次性通知
            self.model.end_batch_update()

        except ValueError as e:
            error_msg = str(e)
            messagebox.showerror("错误", error_msg)

            # 根据错误类型将焦点设置到相应输入框
            if "请输入IP地址" in error_msg and self.ip_entry:
                self.ip_entry.focus_set()
            elif "请输入可用IP数量" in error_msg and self.available_count_component:
                self.available_count_component.focus_set()
            elif "可用IP数量必须大于0" in error_msg and self.available_count_component:
                self.available_count_component.focus_set()
            elif "invalid literal" in error_msg and self.available_count_component:
                self.available_count_component.focus_set()
            elif self.ip_entry:
                # 其他错误情况，默认聚焦到IP输入框
                self.ip_entry.focus_set()

        except Exception as e:
            messagebox.showerror("错误", f"计算出错: {str(e)}")
            # 发生异常时聚焦到IP输入框
            if self.ip_entry:
                self.ip_entry.focus_set()

    def set_ip_and_subnet_mask(self):
        """根据输入的IP地址和子网掩码设置模型属性"""
        try:
            if self.ip_entry is None:
                raise ValueError("IP地址输入框未初始化")
            if self.mask_entry is None:
                raise ValueError("掩码输入框未初始化")

            ip_str = self.ip_entry.get().strip()
            mask_str = self.mask_entry.get().strip()

            if not ip_str:
                raise ValueError("请输入IP地址")
            if not mask_str:
                raise ValueError("请输入掩码/前缀")

            # 验证IP地址是否适用于计算
            is_valid, error_msg = self._validate_ip_for_calculation(ip_str)
            if not is_valid:
                raise ValueError(error_msg)

            # 验证子网掩码是否有效
            if not self._is_valid_netmask(mask_str):
                raise ValueError("无效的子网掩码")

            # 使用批量更新机制避免频繁GUI刷新
            self.model.start_batch_update()

            # 通过设置模型的IP和子网掩码属性来触发计算
            self.model.ip_address = ip_str  # 修改：将ip改为ip_address
            self.model.subnet_mask = mask_str

            # 同步掩码位输入框，显示计算出的前缀长度
            if self.mask_entry is not None:
                self.mask_entry.delete(0, tk.END)
                self.mask_entry.insert(0, str(self.model.mask_length))

            logger.debug("Model state after set_ip_and_subnet_mask: %s", self.model)

            # 结束批量更新，触发一次性通知
            self.model.end_batch_update()

        except ValueError as e:
            error_msg = str(e)
            messagebox.showerror("错误", error_msg)

            # 根据错误类型将焦点设置到相应输入框
            if "请输入IP地址" in error_msg and self.ip_entry:
                self.ip_entry.focus_set()
            elif "请输入掩码/前缀" in error_msg and self.mask_entry:
                self.mask_entry.focus_set()
            elif "无效的子网掩码" in error_msg and self.mask_entry:
                self.mask_entry.focus_set()
            elif "invalid literal" in error_msg and self.mask_entry:
                self.mask_entry.focus_set()
            elif self.ip_entry:
                # 其他错误情况，默认聚焦到IP输入框
                self.ip_entry.focus_set()

        except Exception as e:
            messagebox.showerror("错误", f"计算出错: {str(e)}")
            # 发生异常时聚焦到IP输入框
            if self.ip_entry:
                self.ip_entry.focus_set()

    def set_ip_and_available_subnet_count(self):
        """根据输入IP和可用子网数量设置模型属性"""
        try:
            # 检查控件是否存在后再获取值
            if self.ip_entry is None:
                raise ValueError("IP地址输入框未初始化")
            if self.available_subnet_component is None:
                raise ValueError("可用子网数量组件未初始化")

            ip_str = self.ip_entry.get().strip()
            subnet_str = self.available_subnet_component.get().strip()

            logger.debug(
                "set_ip_and_available_subnet_count input: ip=%r, subnet_count=%r",
                ip_str,
                subnet_str,
            )

            if not ip_str:
                raise ValueError("请输入IP地址")

            if not subnet_str:
                raise ValueError("请输入可用子网数量")

            subnets = int(subnet_str)
            if subnets <= 0:
                raise ValueError("可用子网数量必须大于0")

            # 验证IP地址是否适用于计算
            is_valid, error_msg = self._validate_ip_for_calculation(ip_str)
            if not is_valid:
                raise ValueError(error_msg)

            # 使用批量更新机制避免频繁GUI刷新
            self.model.start_batch_update()

            # 通过设置模型的IP和可用子网数量属性来触发计算
            self.model.ip_address = ip_str
            self.model.possible_subnet_count = subnets

            # 同步掩码位输入框
            if self.mask_entry is not None:
                self.mask_entry.delete(0, tk.END)
                self.mask_entry.insert(0, str(self.model.mask_length))

            # 结束批量更新，触发一次性通知
            self.model.end_batch_update()

        except ValueError as e:
            error_msg = str(e)
            messagebox.showerror("错误", error_msg)

            # 根据错误类型将焦点设置到相应输入框
            if "请输入IP地址" in error_msg and self.ip_entry:
                self.ip_entry.focus_set()
            elif "请输入可用子网数量" in error_msg and self.available_subnet_component:
                self.available_subnet_component.focus_set()
            elif (
                "可用子网数量必须大于0" in error_msg and self.available_subnet_component
            ):
                self.available_subnet_component.focus_set()
            elif "invalid literal" in error_msg and self.available_subnet_component:
                self.available_subnet_component.focus_set()
            elif self.ip_entry:
                # 其他错误情况，默认聚焦到IP输入框
                self.ip_entry.focus_set()

        except Exception as e:
            messagebox.showerror("错误", f"计算出错: {str(e)}")
            # 发生异常时聚焦到IP输入框
            if self.ip_entry:
                self.ip_entry.focus_set()

        logger.debug("Model state after set_ip_and_available_subnet_count: %s", self.model)

    def _center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = 1100
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ── 后续网段生成功能 ─────────────────────────────────────────

    _subnet_gen_n_entry = None  # N值输入框
    _subnet_gen_btn = None      # 生成按钮

    def _build_subnet_generation_ui(self, toolbar_frame):
        """在工具栏中构建后续网段生成控件"""
        sep = ttk.Separator(toolbar_frame, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=(15, 10))

        ttk.Label(toolbar_frame, text="生成").pack(side=tk.LEFT, padx=(0, 5))

        self._subnet_gen_n_entry = ttk.Entry(toolbar_frame, width=8)
        self._subnet_gen_n_entry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(toolbar_frame, text="个后续网段").pack(side=tk.LEFT, padx=(0, 5))

        self._subnet_gen_btn = ttk.Button(
            toolbar_frame,
            text="生成",
            command=self._on_generate_subnets,
            style="Accent.TButton",
            width=6,
        )
        self._subnet_gen_btn.pack(side=tk.LEFT, padx=(0, 10))

    def _on_generate_subnets(self):
        """处理生成后续网段按钮点击"""
        cidr = self.model.cidr_notation.strip()
        if not cidr or cidr == "N/A":
            messagebox.showwarning("警告", "请先计算一个网段")
            return

        n_str = self._subnet_gen_n_entry.get().strip() if self._subnet_gen_n_entry else ""
        if not n_str:
            messagebox.showwarning("警告", "请输入要生成的网段数量 N")
            return

        try:
            n = int(n_str)
            if n < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("警告", "N 必须是正整数")
            return

        try:
            subnets = _calculate_subsequent_subnets(cidr, n)
        except Exception as e:
            messagebox.showerror("错误", f"网段生成失败: {e}")
            return

        # 存入缓存供子窗口使用
        global _generated_subnets_cache
        _generated_subnets_cache = subnets

        SubnetGenerationWindow(self.root, subnets, cidr)


def _calculate_subsequent_subnets(cidr_str, count):
    """从 cidr_str 开始计算后续 count 个网段

    返回 list[dict]: {
        "index": int,
        "cidr": str,
        "ip_range": "first/last 格式的 IP 范围",
        "gateway": "网关 IP"
    }
    """
    import ipaddress

    # 判断地址族
    if ":" in cidr_str:
        factory = ipaddress.IPv6Network
    else:
        factory = ipaddress.IPv4Network

    base = factory(cidr_str, strict=False)
    prefix = base.prefixlen
    step = base.num_addresses  # 每个网段的大小

    results = []
    for i in range(count):
        net_int = int(base.network_address) + i * step
        net = factory((net_int, prefix), strict=False)

        num = net.num_addresses
        if isinstance(net, ipaddress.IPv4Network):
            if num == 1:  # /32
                first_host = str(net.network_address)
                last_host = str(net.broadcast_address)
            elif num == 2:  # /31
                first_host = str(net.network_address)
                last_host = str(net.broadcast_address)
            else:
                first_host = str(net.network_address + 1)
                last_host = str(net.broadcast_address - 1)
        else:  # IPv6
            if num == 1:
                first_host = str(net.network_address)
                last_host = str(net.network_address)
            else:
                first_host = str(net.network_address + 1)
                last_host = int(net.network_address) + num - 1
                last_host = str(net._version_class(last_host))

        ip_range = f"{first_host}/{prefix}-{last_host}/{prefix}"
        gateway = f"{first_host}/{prefix}"

        results.append({
            "index": i + 1,
            "cidr": str(net),
            "ip_range": ip_range,
            "gateway": gateway,
        })

    return results


class SubnetGenerationWindow:
    """后续网段生成结果弹出窗口"""

    def __init__(self, parent, subnets, base_cidr):
        self.parent = parent
        self.subnets = subnets
        self.base_cidr = base_cidr

        self.win = tk.Toplevel(parent)
        self.win.title(f"后续网段生成结果 — 基于 {base_cidr}")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.minsize(700, 300)

        # 居中
        self.win.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w, h = 750, 420
        self.win.geometry(f"{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self.win)
        top_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Label(
            top_frame,
            text=f"基于 {self.base_cidr}，共 {len(self.subnets)} 个网段",
            font=("", 10, "bold"),
        ).pack(side=tk.LEFT)

        # Treeview + 滚动条
        tree_frame = ttk.Frame(self.win)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        columns = ("序号", "CIDR表示法", "IP地址范围", "网关")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=12,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        col_widths = (50, 170, 320, 170)
        for col, w in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=80, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        for s in self.subnets:
            self.tree.insert(
                "",
                tk.END,
                values=(s["index"], s["cidr"], s["ip_range"], s["gateway"]),
            )

        # 按钮栏
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        export_btn = ttk.Button(
            btn_frame,
            text="导出 Excel",
            command=self._export_excel,
            style="Accent.TButton",
        )
        export_btn.pack(side=tk.LEFT, padx=(0, 10))

        close_btn = ttk.Button(btn_frame, text="关闭", command=self.win.destroy)
        close_btn.pack(side=tk.LEFT)

    def _export_excel(self):
        """将结果导出为 Excel 文件"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        except ImportError:
            messagebox.showerror("导出失败", "未安装 openpyxl，请执行 pip install openpyxl")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self.win,
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
            title="保存网段生成结果",
        )
        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "后续网段"

        # 标题行
        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        headers = ["序号", "CIDR表示法", "IP地址范围", "网关"]
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        for row_idx, s in enumerate(self.subnets, 2):
            vals = [s["index"], s["cidr"], s["ip_range"], s["gateway"]]
            for col_idx, v in enumerate(vals, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=v)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border

        # 列宽
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 42
        ws.column_dimensions["D"].width = 22

        wb.save(path)
        messagebox.showinfo("导出成功", f"结果已保存至:\n{path}")


if __name__ == "__main__":
    logging.info("Starting application")
    """独立运行IP计算器进行调试"""
    print("正在启动独立的IP计算器调试模式...")

    try:
        # 创建根窗口
        root = tk.Tk()
        root.title("IP地址空间计算器 - 独立调试模式")
        root.withdraw()  # 先隐藏窗体

        # 创建IP计算器实例
        calculator = IPSubnetCalculator(root)
        calculator._center_window()  # 居中窗体
        root.update_idletasks()  # 确保所有布局和绘图任务完成
        root.deiconify()

        # 启动主循环
        root.mainloop()

    except Exception as e:
        print(f"调试模式启动失败: {e}")
        import traceback

        traceback.print_exc()
        input("按回车键退出...")
