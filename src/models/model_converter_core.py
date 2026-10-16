"""
IPv4/IPv6 转换器核心逻辑模块

功能：
1. 支持IPv4与IPv6地址相互转换
2. 提供IP地址验证功能
3. 提供IP转换核心算法
"""

# 标准库
# import os  # 未使用，已注释
# import sys  # 未使用，已注释
# import json  # 未使用，已注释
# import threading  # 未使用，已注释
# import time  # 未使用，已注释
from dataclasses import dataclass

# import traceback  # 未使用，已注释
# import logging  # 未使用，已注释

# 第三方库
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
import logging
from utils.logger_config import setup_module_logger

logger = setup_module_logger(__name__)


# 定义转换类型对象
@dataclass
class ConversionConfig:
    conversion_type: str  # 转换类型标识
    src_field: str  # 源文本区域字段名
    dst_field: str  # 目标文本区域字段名
    format_cls: type  # 用于验证的地址类型类


class CoreIPConverter:
    """IP转换核心逻辑类"""

    def validate_ip(self, ip_str, ip_type):
        """验证IP地址格式"""
        try:
            return isinstance(ip_address(ip_str), ip_type)
        except (ValueError, AddressValueError):
            return False

    def ip_converse(self, ip_list, conver_type):
        """IP转换核心逻辑"""
        logger.debug("Processing event")
        converted = []
        for i, ip_str in enumerate(ip_list):
            logger.debug("Processing event")
            if ip_str == "":
                logger.debug("Processing event")
                converted.append(ip_str)
                continue

            # 获取当前IPv6前缀
            prefix = getattr(self, '_current_ipv6_prefix', '')  # 从实例属性获取前缀
            logger.debug("Processing event")

            # 获取格式类型
            format_type = getattr(self, '_current_format_type', 'exploded')
            logger.debug("Processing event")

            if conver_type == "4to6":
                try:
                    logger.debug("Processing event")
                    # 验证是否为有效的IPv4地址
                    if not self.validate_ip(ip_str, IPv4Address):
                        logger.debug("Processing event")
                        converted.append("Invalid IPv4 address")
                        continue

                    logger.debug("Processing event")

                    # 检查前缀是否有效
                    if not prefix:
                        logger.debug("Processing event")
                        converted.append("No IPv6 prefix configured")
                        continue

                    # 验证前缀格式（必须以::结尾才能正确嵌入IPv4）
                    if not prefix.endswith('::'):
                        logger.debug("Processing event")
                        converted.append(
                            f"Invalid IPv6 prefix format: '{prefix}'")
                        continue

                    # 检查前缀的有效性
                    # prefix_base = prefix[:-2]  # 移除最后的::
                    try:
                        # 验证前缀部分是否为有效的IPv6地址片段
                        # test_ipv6 = IPv6Address(f"{prefix_base}0:0:0:0:0:0:1")
                        logger.debug("Processing event")
                    except Exception as prefix_error:
                        logger.debug("Processing event")
                        converted.append(f"Invalid IPv6 prefix: '{prefix}'")
                        continue

                    # 尝试构建嵌入式IPv6地址
                    embedded_ipv6_str = f"{prefix}{ip_str}"
                    logger.debug("Processing event")

                    # 验证构建的字符串格式
                    parts = embedded_ipv6_str.split(':')
                    logger.debug("Processing event")

                    # 检查部分数量（应该至少有3部分：前缀部分 + :: + IPv4）
                    if len(parts) < 3:
                        logger.debug("Processing event")
                        converted.append(
                            f"Invalid IPv6 construction: {embedded_ipv6_str}")
                        continue

                    # 尝试创建IPv6地址对象
                    logger.debug("Processing event")
                    ipv6_addr = IPv6Address(embedded_ipv6_str)
                    logger.debug("Processing event")

                    # 根据格式类型处理输出
                    if format_type == "exploded":
                        result = ipv6_addr.exploded
                        logger.debug("Processing event")
                    elif format_type == "compressed":
                        result = ipv6_addr.compressed
                        logger.debug("Processing event")
                    elif format_type == "embedded":
                        result = str(embedded_ipv6_str)
                        logger.debug("Processing event")
                    elif format_type == "noneleadingzero":
                        result = ":".join(
                            part.lstrip("0") or "0"
                            for part in ipv6_addr.exploded.split(":")
                        )
                        logger.debug("Processing event")
                    else:
                        result = ipv6_addr.compressed  # 默认压缩格式
                        logger.debug("Processing event")

                    converted.append(result)
                    logger.debug("Processing event")

                except ValueError as ve:
                    logger.debug("Processing event")
                    logger.debug("Processing event")
                    import traceback
                    logger.debug("Processing event")
                    converted.append(f"ValueError: {str(ve)}")
                except Exception as e:
                    logger.debug("Processing event")
                    logger.debug("Processing event")
                    import traceback
                    logger.debug("Processing event")
                    converted.append(f"Conversion Error: {str(e)}")

            elif conver_type == "6to4":
                try:
                    logger.debug("Processing event")
                    ipv4_result = self.extract_ipv4_from_ipv6(ip_str)
                    logger.debug("Processing event")
                    converted.append(ipv4_result)
                except Exception as e:
                    logger.debug("Processing event")
                    logger.debug("Processing event")
                    import traceback
                    logger.debug("Processing event")
                    converted.append("Invalid IPv6 to IPv4 extraction")

            elif conver_type == "6to6":
                try:
                    logger.debug("Processing event")
                    ipv6_addr = IPv6Address(ip_str)
                    format_type = getattr(
                        self, '_current_format_type', 'exploded')

                    if format_type == "exploded":
                        result = ipv6_addr.exploded
                    elif format_type == "compressed":
                        result = ipv6_addr.compressed
                    elif format_type == "embedded":
                        # 提取前96位和后32位
                        ipv6_int = int(ipv6_addr)
                        ipv4_int = ipv6_int & 0xFFFFFFFF
                        ipv4_addr = IPv4Address(ipv4_int)
                        # 拼接前96位和IPv4地址
                        ipv6_high_96_str = ipv6_addr.exploded.rsplit(":", 2)[0]
                        result = f"{ipv6_high_96_str}:{ipv4_addr}"
                    elif format_type == "noneleadingzero":
                        result = ":".join(
                            part.lstrip("0") or "0"
                            for part in ipv6_addr.exploded.split(":")
                        )
                    else:
                        result = ipv6_addr.compressed  # 默认压缩格式

                    converted.append(result)
                    logger.debug("Processing event")
                except Exception as e:
                    logger.debug("Processing event")
                    logger.debug("Processing event")
                    import traceback
                    logger.debug("Processing event")
                    converted.append("Invalid IPv6 format conversion")

        logger.debug("Processing event")
        return converted

    def extract_ipv4_from_ipv6(self, ip_str):
        """从IPv6地址中提取IPv4地址"""
        try:
            # 首先验证输入是否为有效的IPv6地址
            if not self.validate_ip(ip_str, IPv6Address):
                return "Invalid IPv6 address"

            ipv6 = IPv6Address(ip_str)
            ipv4_int = int(ipv6) & 0xFFFFFFFF
            ipv4_addr = IPv4Address(ipv4_int)
            return str(ipv4_addr)
        except Exception as e:
            logger.debug("Processing event")
            logger.error("IPv4 extraction failed")
            return "Invalid IPv4 extraction"

    def extract_ip_addresses(self, text):
        """从文本中提取IP地址"""
        import re
        # IPv4地址的正则表达式
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        # IPv6地址的正则表达式（简化版）
        ipv6_pattern = r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'

        ipv4_matches = re.findall(ipv4_pattern, text)
        ipv6_matches = re.findall(ipv6_pattern, text)

        return ipv4_matches + ipv6_matches

    def is_valid_ipv4(self, ip_str):
        """验证IPv4地址有效性"""
        try:
            # ip = IPv4Address(ip_str)
            return True
        except (ValueError, AddressValueError):
            return False

    def is_valid_ipv6(self, ip_str):
        """验证IPv6地址有效性"""
        try:
            # ip = IPv6Address(ip_str)
            return True
        except (ValueError, AddressValueError):
            return False
