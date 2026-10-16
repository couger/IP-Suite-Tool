"""
网络空间模型模块

描述:
    该模块定义了 NetworkSpace 类，用于存储和管理网络地址空间的相关信息。
    这个类实现了观察者模式，当模型属性发生改变时，会自动通知所有注册的观察者。

用途:
    - 存储IP地址、子网掩码、网络地址、广播地址等相关网络信息
    - 管理IPv4和IPv6的网络空间数据
    - 为IP地址空间计算器提供数据模型支持

功能:
    - 属性封装：所有属性通过getter/setter进行访问控制
    - 观察者模式：当属性值改变时自动通知观察者
    - 调试输出：提供格式化的字符串表示，方便调试
    - 参数重置：提供reset方法清理所有参数
    - 网络计算：根据IP地址和掩码自动计算网络信息

观察者接口:
    观察者需要实现 on_model_change(prop_name, value) 方法来接收模型变更通知

作者: Lingma AI Assistant
日期: 2026-01-22
版本: 1.9
"""

# from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network
from ipaddress import ip_address, IPv4Network, IPv6Network, IPv6Address
import math

# import re


class NetworkSpace:
    """网络空间模型类，用于存储和管理网络信息"""

    def __init__(self):
        # 初始化观察者列表
        self._observers = []
        # 批量更新机制 - 防止计算过程中频繁触发GUI更新
        self._suppress_notifications = False
        self._pending_updates = []
        # 调用reset方法进行初始化
        self.reset()

    # 新增错误处理属性和方法
    @property
    def error_message(self):
        return self._error_message

    @error_message.setter
    def error_message(self, value):
        self._error_message = value
        self.notify_observers("error_message")

    @property
    def has_error(self):
        return self._has_error

    @has_error.setter
    def has_error(self, value):
        self._has_error = bool(value)
        self.notify_observers("has_error")

    def set_error(self, error_msg):
        """统一设置错误的方法"""
        self._has_error = True
        self._error_message = str(error_msg)
        self.notify_observers("has_error")
        self.notify_observers("error_message")

    def clear_error(self):
        """清除错误状态"""
        self._has_error = False
        self._error_message = ""
        self.notify_observers("has_error")
        self.notify_observers("error_message")

    def add_observer(self, observer):
        """添加观察者"""
        self._observers.append(observer)

    def remove_observer(self, observer):
        """移除观察者"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, prop_name):
        """通知所有观察者某个属性发生变化"""
        # 如果正在批量更新中，跳过通知
        if self._suppress_notifications:
            return
        for observer in self._observers:
            observer.on_model_change(prop_name, getattr(self, f"_{prop_name}"))

    def start_batch_update(self):
        """开始批量更新 - 抑制观察者通知"""
        self._suppress_notifications = True
        self._pending_updates = []

    def end_batch_update(self):
        """结束批量更新 - 触发所有待处理的更新通知"""
        if not self._suppress_notifications:
            return
        self._suppress_notifications = False

        # 定义需要检查的属性列表
        tracked_properties = [
            "ip_address",
            "mask_length",
            "network_address",
            "broadcast_address",
            "subnet_mask",
            "wildcard_mask",
            "cidr_notation",
            "ip_type",
            "first_host_ip",
            "last_host_ip",
            "host_count",
            "subnet_position_index",
            "host_index_in_subnet",
            "available_host_count",
            "possible_subnet_count",
            "address_family_bit_length",
            "actual_subnet_count",
        ]

        # 通知所有待处理的属性变化
        for prop_name in self._pending_updates:
            if prop_name in tracked_properties:
                for observer in self._observers:
                    observer.on_model_change(prop_name, getattr(self, f"_{prop_name}"))

        # 如果 pending_updates 为空（说明计算内部直接设置了属性），则通知所有属性
        if not self._pending_updates:
            for prop_name in tracked_properties:
                for observer in self._observers:
                    observer.on_model_change(prop_name, getattr(self, f"_{prop_name}"))

        self._pending_updates.clear()

    def reset(self):
        """重置所有参数为初始值"""
        self._ip_address = ""  # 修改：将ip改为ip_address
        self._mask_length = 0
        self._network_address = ""
        self._broadcast_address = ""
        self._subnet_mask = ""
        self._wildcard_mask = ""
        self._cidr_notation = ""
        self._ip_type = ""
        self._first_host_ip = ""
        self._last_host_ip = ""
        self._host_count = 0
        self._subnet_position_index = 0
        self._host_index_in_subnet = 0
        self._available_host_count = 0
        self._possible_subnet_count = 0
        self._address_family_bit_length = ""
        self._host_info = ""
        self._actual_subnet_count = 0
        # 新增错误处理属性
        self._error_message = ""
        self._has_error = False

    def update_from_dict(self, data_dict):
        """从字典批量更新模型属性，更新前先重置所有参数"""
        self.reset()
        for key, value in data_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def calculate_by_mask_length(self, ip_str, mask_str):
        """根据IP地址和掩码计算所有网络信息"""
        # 重置所有参数
        self.reset()

        # 保存输入参数
        self._ip_address = ip_str  # 修改：将ip改为ip_address
        self._mask_length = int(mask_str)

        # 判断IP类型并创建网络对象
        if "." in ip_str:
            # IPv4
            self._ip_type = "IPv4"
            net = IPv4Network(f"{ip_str}/{mask_str}", strict=False)
            total_bits = 32
        elif ":" in ip_str:
            # IPv6
            self._ip_type = "IPv6"
            net = IPv6Network(f"{ip_str}/{mask_str}", strict=False)
            total_bits = 128
        else:
            raise ValueError("无效的IP地址格式")

        # 通用计算
        self._network_address = str(net.network_address)
        self._cidr_notation = str(net)
        # 修改：将prefix_total_length改为address_family_bit_length
        self._address_family_bit_length = str(total_bits)

        # IPv4特有计算
        if self._ip_type == "IPv4":
            self._broadcast_address = str(net.broadcast_address)
            self._subnet_mask = str(net.netmask)
            self._wildcard_mask = str(net.hostmask)

        # 计算主机数量
        num_addresses = net.num_addresses
        if self._ip_type == "IPv4":
            self._host_count = num_addresses - 2 if num_addresses > 2 else num_addresses
            # 修改：将available_count改为available_host_count
            self._available_host_count = (
                num_addresses - 2 if num_addresses > 2 else num_addresses
            )
        else:
            # IPv6不使用广播地址概念
            self._host_count = num_addresses
            # 修改：将available_count改为available_host_count
            self._available_host_count = num_addresses

        # 计算网络信息
        available_networks = 2**net.prefixlen
        # 修改：将available_subnet_count改为possible_subnet_count
        self._possible_subnet_count = available_networks
        # 修改：将subnet_count改为actual_subnet_count
        self._actual_subnet_count = net.num_addresses

        # 计算当前网络和IP索引
        host_bits = total_bits - net.prefixlen
        network_part = int(net.network_address) >> host_bits
        self._subnet_position_index = (
            network_part + 1
        )  # 修改：将subnet_index改为subnet_position_index

        # 计算当前IP在其子网中的序号
        ip_input = ip_str  # 使用传入的IP地址
        try:
            original_ip = ip_address(ip_input)
        except ValueError:
            original_ip = net.network_address

        host_part = int(original_ip) & ((1 << host_bits) - 1)
        self._host_index_in_subnet = (
            host_part + 1
        )  # 修改：将ip_index改为host_index_in_subnet

        # 计算起始和结束IP
        if self._ip_type == "IPv4":
            if net.num_addresses == 1:  # /32子网
                self._first_host_ip = str(net.network_address)
                self._last_host_ip = str(net.broadcast_address)
            elif net.num_addresses == 2:  # /31子网 (RFC 3021)
                self._first_host_ip = str(net.network_address)
                self._last_host_ip = str(net.broadcast_address)
            else:  # 常规子网
                self._first_host_ip = str(net.network_address + 1)
                self._last_host_ip = str(net.broadcast_address - 1)
        else:  # IPv6
            if net.num_addresses == 1:  # /128子网
                self._first_host_ip = str(net.network_address)
                self._last_host_ip = str(net.network_address)
            else:  # 其他子网
                first_ip_int = int(net.network_address) + 1
                last_ip_int = int(net.network_address) + (num_addresses - 1)

                # 将整数转换回IP地址对象
                first_ip_addr = (
                    type(original_ip)(first_ip_int)
                    if self._ip_type == "IPv4"
                    else type(net.network_address)(first_ip_int)
                )
                last_ip_addr = (
                    type(original_ip)(last_ip_int)
                    if self._ip_type == "IPv4"
                    else type(net.network_address)(last_ip_int)
                )

                self._first_host_ip = str(first_ip_addr)
                self._last_host_ip = str(last_ip_addr)

        # 通知观察者所有属性的变化
        self.notify_all_properties()

    def calculate_by_available_count(self, ip_str, available_count):
        """根据IP地址和可用IP数量计算网络信息"""

        # 重置所有参数
        self.reset()

        # 保存IP地址
        self._ip_address = ip_str  # 修改：将ip改为ip_address

        # 验证可用IP数量
        if available_count <= 0:
            raise ValueError("可用IP数量必须大于0")

        # 验证IP地址类型
        if "." in ip_str:
            # IPv4
            self._ip_type = "IPv4"
            # total_bits = 32
        elif ":" in ip_str:
            # IPv6
            self._ip_type = "IPv6"
            # total_bits = 128
        else:
            raise ValueError("无效的IP地址格式")

        # 计算需要的主机位数
        # 主机位数 = ceil(log2(可用IP数 + 2))，加2是因为网络地址和广播地址
        total_addresses = available_count + 2
        host_bits_needed = math.ceil(math.log2(total_addresses))

        # 计算网络位数
        if self._ip_type == "IPv4":
            prefix_len = 32 - host_bits_needed
            if prefix_len < 0:
                raise ValueError("IP数量太大，无法分配")
        else:  # IPv6
            prefix_len = 128 - host_bits_needed
            if prefix_len < 0:
                raise ValueError("IP数量太大，无法分配")

        # 使用计算出的前缀长度重新计算网络信息
        self.calculate_by_mask_length(ip_str, str(prefix_len))

    def calculate_by_subnet_mask(self, ip_str, subnet_mask_str):
        """根据IP地址和子网掩码计算网络信息"""

        # 验证子网掩码格式
        if not self._is_valid_netmask(subnet_mask_str):
            raise ValueError("无效的子网掩码格式")

        # 将子网掩码转换为CIDR前缀长度
        octets = subnet_mask_str.split(".")
        if len(octets) != 4:
            raise ValueError("子网掩码格式错误")

        # 验证每个八位组的数值范围
        for octet_str in octets:
            octet = int(octet_str)
            if octet < 0 or octet > 255:
                raise ValueError("子网掩码八位组超出有效范围(0-255)")

        # 计算子网掩码的二进制表示中的1的个数
        binary_mask = "".join([bin(int(octet))[2:].zfill(8) for octet in octets])
        prefix_len = binary_mask.count("1")

        # 使用计算出的前缀长度重新计算网络信息
        self.calculate_by_mask_length(ip_str, str(prefix_len))

    def calculate_by_available_subnet(self, ip_str, available_subnet_count):
        """根据IP地址和可用子网数量计算网络信息"""

        # 重置所有参数
        self.reset()

        # 保存IP地址
        self._ip_address = ip_str  # 修改：将ip改为ip_address

        # 验证IP地址类型
        if "." in ip_str:
            # IPv4
            self._ip_type = "IPv4"
            total_bits = 32
            # 不再使用固定的/24基础网络，而是基于整个IPv4地址空间计算
            base_prefix = 0  # 从整个地址空间开始
        elif ":" in ip_str:
            # IPv6
            self._ip_type = "IPv6"
            total_bits = 128
            # IPv6现在也从整个地址空间开始理论计算
            base_prefix = 0  # 从整个地址空间开始
        else:
            raise ValueError("无效的IP地址格式")

        # 验证子网数量参数
        if available_subnet_count <= 0:
            raise ValueError("子网数量必须大于0")

        # 计算需要的网络位数来容纳指定数量的子网
        subnet_bits_needed = math.ceil(math.log2(available_subnet_count))

        # 计算新的前缀长度
        # 对于IPv4: 从0开始计算，即整个32位地址空间
        # 对于IPv6: 现在也从0开始计算（整个128位地址空间）
        if self._ip_type == "IPv4":
            new_prefix = subnet_bits_needed
        else:  # IPv6
            new_prefix = base_prefix + subnet_bits_needed

        # 检查是否超出地址空间限制
        if (self._ip_type == "IPv4" and new_prefix > 32) or (
            self._ip_type == "IPv6" and new_prefix > 128
        ):
            raise ValueError("子网数量过多，超出地址空间限制")

        # 特殊处理：当只需要1个子网时，使用整个地址空间
        if available_subnet_count == 1:
            new_prefix = 0  # 对于IPv4和IPv6都是0

        # 创建网络对象 - 关键修改：确保使用正确的IP地址和前缀
        try:
            if self._ip_type == "IPv4":
                network_obj = IPv4Network(f"{ip_str}/{new_prefix}", strict=False)
                base_network = IPv4Network("0.0.0.0/0", strict=False)
            else:  # IPv6
                network_obj = IPv6Network(f"{ip_str}/{new_prefix}", strict=False)
                base_network = IPv6Network("::/0", strict=False)
        except Exception as e:
            # 如果创建网络对象失败，可能是地址格式问题，使用默认地址
            print(f"DEBUG: 网络对象创建失败: {e}, 使用默认地址")
            if self._ip_type == "IPv4":
                network_obj = IPv4Network(f"0.0.0.0/{new_prefix}", strict=False)
                base_network = IPv4Network("0.0.0.0/0", strict=False)
            else:  # IPv6
                network_obj = IPv6Network(f"::/{new_prefix}", strict=False)
                base_network = IPv6Network("::/0", strict=False)

        # 更新模型属性
        ip_obj = ip_address(ip_str)
        network_addr = network_obj.network_address
        broadcast_addr = (
            network_obj.broadcast_address if self._ip_type == "IPv4" else ""
        )

        self._ip_address = str(ip_obj)  # 修改：将ip改为ip_address
        self._network_address = str(network_addr)
        self._broadcast_address = str(broadcast_addr) if self._ip_type == "IPv4" else ""
        self._subnet_mask = str(network_obj.netmask) if self._ip_type == "IPv4" else ""
        self._wildcard_mask = (
            str(network_obj.hostmask) if self._ip_type == "IPv4" else ""
        )
        self._cidr_notation = str(network_obj)
        self._mask_length = network_obj.prefixlen
        self._first_host_ip = (
            str(network_addr + 1)
            if (
                network_obj.num_addresses >
                # 修改：将first_ip改为first_host_ip
                2
                and self._ip_type == "IPv4"
            )
            else str(network_addr)
        )
        if self._ip_type == "IPv4":
            # 对于IPv4，broadcast_addr是IPv4Address对象，可以执行减法
            if network_obj.num_addresses > 2:
                # 修改：将last_ip改为last_host_ip
                self._last_host_ip = str(network_obj.broadcast_address - 1)
            else:
                # 修改：将last_ip改为last_host_ip
                self._last_host_ip = str(network_obj.broadcast_address)
        else:  # IPv6
            # 修改：将last_ip改为last_host_ip
            # 特殊处理：对于/0网络，最后一个地址就是最大IPv6地址
            if new_prefix == 0:
                self._last_host_ip = "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
            else:
                last_addr_int = int(network_addr) + network_obj.num_addresses - 1
                # 确保不超过IPv6地址范围
                if last_addr_int >= 2**128:
                    last_addr_int = 2**128 - 1
                self._last_host_ip = str(IPv6Address(last_addr_int))

        self._available_host_count = (
            max(0, network_obj.num_addresses - 2)
            if self._ip_type == "IPv4"
            else network_obj.num_addresses
        )  # 减去网络地址和广播地址
        if network_obj.num_addresses > 2 and self._ip_type == "IPv4":
            self._host_count = network_obj.num_addresses - 2  # 主机数量
        else:
            self._host_count = (
                1 if self._ip_type == "IPv4" else network_obj.num_addresses
            )  # 对于/31和/32网络

        # 计算IP索引
        ip_index = int(ip_obj) - int(network_addr)
        if 0 <= ip_index < network_obj.num_addresses:
            self._host_index_in_subnet = (
                ip_index + 1
            )  # 修改：将ip_index改为host_index_in_subnet
        else:
            self._host_index_in_subnet = 0  # 修改：将ip_index改为host_index_in_subnet

        # 计算子网索引
        if self._ip_type == "IPv4":
            # 对于IPv4，基于整个地址空间计算
            network_offset = int(ip_obj)
            subnet_size = 2 ** (32 - new_prefix)
        else:
            # 对于IPv6，基于基础网络计算
            network_offset = int(ip_obj) - int(base_network.network_address)
            subnet_size = 2 ** (128 - new_prefix)

        subnet_index = (network_offset // subnet_size) + 1  # 从1开始编号
        # 修改：将subnet_index改为subnet_position_index
        self._subnet_position_index = subnet_index

        # 设置子网总数 - 修改为设置possible_subnet_count而不是actual_subnet_count
        self._possible_subnet_count = 2**subnet_bits_needed
        # 同时设置actual_subnet_count以保持一致性
        self._actual_subnet_count = 2**subnet_bits_needed

        # 设置地址族位长度
        self._address_family_bit_length = str(total_bits)  # 添加缺失的设置

        # 通知观察者所有属性的变化
        self.notify_all_properties()

    def notify_all_properties(self):
        """通知所有属性的变化"""
        properties = [
            "ip_address",
            "mask_length",
            "network_address",
            "broadcast_address",  # 修改：将ip改为ip_address
            "subnet_mask",
            "wildcard_mask",
            "cidr_notation",
            "ip_type",
            "first_host_ip",
            "last_host_ip",
            "host_count",
            "subnet_position_index",
            "host_index_in_subnet",
            "available_host_count",
            "possible_subnet_count",
            "address_family_bit_length",
            "actual_subnet_count",
        ]

        for prop in properties:
            self.notify_observers(prop)

    def __str__(self):
        """返回模型所有参数的字符串表示，用于调试"""
        return f"""NetworkSpace[
  ip_address='{self._ip_address}',  # 修改：将ip改为ip_address
  mask_length={self._mask_length},
  network_address='{self._network_address}',
  broadcast_address='{self._broadcast_address}',
  subnet_mask='{self._subnet_mask}',
  wildcard_mask='{self._wildcard_mask}',
  cidr_notation='{self._cidr_notation}',
  ip_type='{self._ip_type}',
  first_host_ip='{self._first_host_ip}',
  last_host_ip='{self._last_host_ip}',
  host_count={self._host_count},
  subnet_position_index={self._subnet_position_index},
  host_index_in_subnet={self._host_index_in_subnet},
  available_host_count={self._available_host_count},
  possible_subnet_count={self._possible_subnet_count},
  address_family_bit_length='{self._address_family_bit_length}',
  actual_subnet_count={self._actual_subnet_count}
]"""

    # IP地址属性
    @property
    def ip_address(self):  # 修改：将ip改为ip_address
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value):  # 修改：将ip改为ip_address
        # 仅在值真正改变时才更新和通知
        if self._ip_address != value:
            # old_value = self._ip_address
            self._ip_address = value
            # 如果同时设置了IP地址和掩码长度，则自动计算网络信息
            if self._ip_address and self._mask_length > 0:
                try:
                    self.calculate_by_mask_length(
                        self._ip_address, str(self._mask_length)
                    )
                    self.clear_error()  # 清除之前的错误
                except Exception as e:
                    error_msg = f"自动计算失败: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    self.set_error(error_msg)  # 设置错误信息
            else:
                self.notify_observers("ip_address")  # 修改：将ip改为ip_address

    # 掩码长度属性
    @property
    def mask_length(self):
        return self._mask_length

    @mask_length.setter
    def mask_length(self, value):
        new_value = int(value)
        # 仅在值真正改变时才更新和通知
        if self._mask_length != new_value:
            # old_value = self._mask_length
            self._mask_length = new_value
            # 如果同时设置了IP地址和掩码长度，则自动计算网络信息
            if self._ip_address and self._mask_length > 0:
                try:
                    self.calculate_by_mask_length(
                        self._ip_address, str(self._mask_length)
                    )
                    self.clear_error()
                except Exception as e:
                    error_msg = f"自动计算失败: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    self.set_error(error_msg)
            else:
                self.notify_observers("mask_length")

    # 网络地址属性
    @property
    def network_address(self):
        return self._network_address

    @network_address.setter
    def network_address(self, value):
        # 仅在值真正改变时才更新和通知
        if self._network_address != value:
            # old_value = self._network_address
            self._network_address = value
            self.notify_observers("network_address")

    # 广播地址属性
    @property
    def broadcast_address(self):
        return self._broadcast_address

    @broadcast_address.setter
    def broadcast_address(self, value):
        # 仅在值真正改变时才更新和通知
        if self._broadcast_address != value:
            # old_value = self._broadcast_address
            self._broadcast_address = value
            self.notify_observers("broadcast_address")

    # 子网掩码属性
    @property
    def subnet_mask(self):
        return self._subnet_mask

    @subnet_mask.setter
    def subnet_mask(self, value):
        # 仅在值真正改变时才更新和通知
        if self._subnet_mask != value:
            # old_value = self._subnet_mask
            self._subnet_mask = value
            # 如果同时设置了IP地址和子网掩码，则自动计算网络信息
            if self._ip_address and self._subnet_mask:
                try:
                    self.calculate_by_subnet_mask(self._ip_address, self._subnet_mask)
                    self.clear_error()
                except Exception as e:
                    error_msg = f"自动计算失败: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    self.set_error(error_msg)
            else:
                self.notify_observers("subnet_mask")

    # 反向子网掩码属性
    @property
    def wildcard_mask(self):
        return self._wildcard_mask

    @wildcard_mask.setter
    def wildcard_mask(self, value):
        self._wildcard_mask = value
        self.notify_observers("wildcard_mask")

    # CIDR表示法属性
    @property
    def cidr_notation(self):
        return self._cidr_notation

    @cidr_notation.setter
    def cidr_notation(self, value):
        # 仅在值真正改变时才更新和通知
        if self._cidr_notation != value:
            # old_value = self._cidr_notation
            self._cidr_notation = value
            self.notify_observers("cidr_notation")

    # IP类型属性
    @property
    def ip_type(self):
        return self._ip_type

    @ip_type.setter
    def ip_type(self, value):
        self._ip_type = value
        self.notify_observers("ip_type")

    # 起始主机IP属性
    @property
    def first_host_ip(self):  # 修改：将first_ip改为first_host_ip
        return self._first_host_ip

    @first_host_ip.setter
    def first_host_ip(self, value):  # 修改：将first_ip改为first_host_ip
        self._first_host_ip = value
        self.notify_observers("first_host_ip")  # 修改：将first_ip改为first_host_ip

    # 末尾主机IP属性
    @property
    def last_host_ip(self):  # 修改：将last_ip改为last_host_ip
        return self._last_host_ip

    @last_host_ip.setter
    def last_host_ip(self, value):  # 修改：将last_ip改为last_host_ip
        self._last_host_ip = value
        self.notify_observers("last_host_ip")  # 修改：将last_ip改为last_host_ip

    # 主机数量属性
    @property
    def host_count(self):
        return self._host_count

    @host_count.setter
    def host_count(self, value):
        self._host_count = value
        self.notify_observers("host_count")

    # 子网位置索引属性
    @property
    def subnet_position_index(self):  # 修改：将subnet_index改为subnet_position_index
        return self._subnet_position_index

    @subnet_position_index.setter
    # 修改：将subnet_index改为subnet_position_index
    def subnet_position_index(self, value):
        self._subnet_position_index = value
        # 修改：将subnet_index改为subnet_position_index
        self.notify_observers("subnet_position_index")

    # 主机在子网中的索引属性
    @property
    def host_index_in_subnet(self):  # 修改：将ip_index改为host_index_in_subnet
        return self._host_index_in_subnet

    @host_index_in_subnet.setter
    def host_index_in_subnet(self, value):  # 修改：将ip_index改为host_index_in_subnet
        self._host_index_in_subnet = value
        # 修改：将ip_index改为host_index_in_subnet
        self.notify_observers("host_index_in_subnet")

    # 可用主机数量属性
    @property
    def available_host_count(self):  # 修改：将available_count改为available_host_count
        return self._available_host_count

    @available_host_count.setter
    def available_host_count(self, value):
        new_value = int(value)
        # 仅在值真正改变时才更新和通知
        if self._available_host_count != new_value:
            # old_value = self._available_host_count
            self._available_host_count = new_value
            # 如果同时设置了IP地址，则自动计算网络信息
            if self._ip_address:
                try:
                    self.calculate_by_available_count(
                        self._ip_address, self._available_host_count
                    )
                    self.clear_error()
                except Exception as e:
                    error_msg = f"自动计算失败: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    self.set_error(error_msg)
            else:
                # 修改：将available_count改为available_host_count
                self.notify_observers("available_host_count")

    # 可用子网数量属性
    @property
    # 修改：将available_subnet_count改为possible_subnet_count
    def possible_subnet_count(self):
        return self._possible_subnet_count

    @possible_subnet_count.setter
    # 修改：将available_subnet_count改为possible_subnet_count
    def possible_subnet_count(self, value):
        new_value = int(value)
        # 仅在值真正改变时才更新和通知
        if self._possible_subnet_count != new_value:
            # old_value = self._possible_subnet_count
            self._possible_subnet_count = new_value
            # 如果同时设置了IP地址，则自动计算网络信息
            if self._ip_address:
                try:
                    self.calculate_by_available_subnet(
                        self._ip_address, self._possible_subnet_count
                    )
                    self.clear_error()
                except Exception as e:
                    error_msg = f"自动计算失败: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    self.set_error(error_msg)
            else:
                # 修改：将available_subnet_count改为possible_subnet_count
                self.notify_observers("possible_subnet_count")

    # 地址族位长度属性
    @property
    # 修改：将prefix_total_length改为address_family_bit_length
    def address_family_bit_length(self):
        return self._address_family_bit_length

    @address_family_bit_length.setter
    # 修改：将prefix_total_length改为address_family_bit_length
    def address_family_bit_length(self, value):
        self._address_family_bit_length = value
        # 修改：将prefix_total_length改为address_family_bit_length
        self.notify_observers("address_family_bit_length")

    # 实际子网数量属性
    @property
    def actual_subnet_count(self):  # 修改：将subnet_count改为actual_subnet_count
        return self._actual_subnet_count

    @actual_subnet_count.setter
    def actual_subnet_count(self, value):  # 修改：将subnet_count改为actual_subnet_count
        self._actual_subnet_count = value
        # 修改：将subnet_count改为actual_subnet_count
        self.notify_observers("actual_subnet_count")

    # 主机信息属性（已废弃，保留以备将来使用）
    @property
    def host_info(self):
        return self._host_info

    @host_info.setter
    def host_info(self, value):
        self._host_info = value
        self.notify_observers("host_info")

    def _is_valid_netmask(self, netmask_str):
        """
        验证子网掩码格式是否有效

        Args:
            netmask_str (str): 子网掩码字符串

        Returns:
            bool: 如果子网掩码格式有效返回True，否则返回False
        """
        if not netmask_str:
            return False

        # 分割为八位组
        octets = netmask_str.split(".")
        if len(octets) != 4:
            return False

        try:
            # 验证每个八位组是否为有效数字
            octet_values = []
            for octet_str in octets:
                octet = int(octet_str)
                if octet < 0 or octet > 255:
                    return False
                octet_values.append(octet)

            # 验证是否为有效的子网掩码格式
            # 将所有八位组转换为32位二进制字符串
            binary_mask = "".join([bin(octet)[2:].zfill(8) for octet in octet_values])

            # 有效的子网掩码应该是连续的1后面跟连续的0
            # 找到第一个0的位置
            first_zero_pos = binary_mask.find("0")
            if first_zero_pos == -1:
                # 全1的情况，也是有效的(/32)
                return True

            # 检查第一个0之后是否还有1
            if "1" in binary_mask[first_zero_pos:]:
                return False

            return True

        except ValueError:
            # 转换为整数失败
            return False
