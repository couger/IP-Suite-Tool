#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 IPv4-embedded IPv6 格式地址的脱敏效果

测试地址格式：
  - ::ffff:192.168.1.1        (IPv4-mapped IPv6)
  - ::ffff:c0a8:0101          (纯十六进制形式)
  - 2001:db8::192.168.1.1     (IPv4-embedded with prefix)
  - 0:0:0:0:0:ffff:192.168.1.1 (完整形式)
  - fc00::192.168.1.1         (FC00 + IPv4 embedded)
"""

import sys
import os

# 将 src 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from models.model_anonymizer_core import IPAnonymizerCore
from models.model_anonymizer_processor import FileProcessor


def test_core_module():
    """测试 IPAnonymizerCore 模块"""
    print("=" * 60)
    print("测试 IPAnonymizerCore 模块 (部分脱敏模式)")
    print("=" * 60)

    core = IPAnonymizerCore(partial_anonymize=True)

    test_cases = [
        "::ffff:192.168.1.1",
        "::ffff:c0a8:0101",
        "2001:db8::192.168.1.1",
        "0:0:0:0:0:ffff:192.168.1.1",
        "fc00::192.168.1.1",
        "连接到 ::ffff:10.0.0.1 服务器",
        "地址范围: ::ffff:192.168.1.1-::ffff:192.168.1.10",
    ]

    for text in test_cases:
        print(f"\n原始文本: {text}")

        # 统计
        stats = core.count_ips_in_text(text)
        print(f"  统计 - IPv4: {stats.ipv4_count}, IPv6: {stats.ipv6_count}, FC00: {stats.fc00_count}, 总计: {stats.total_count}")

        # 处理
        result_text, process_stats = core.process_text(text)
        result_stats = core.count_ips_in_text(result_text)
        print(f"  脱敏结果: {result_text}")
        print(f"  已处理统计 - IPv4: {process_stats.ipv4_count}, IPv6: {process_stats.ipv6_count}, FC00: {process_stats.fc00_count}")
        print(f"  处理后统计 - IPv4: {result_stats.ipv4_count}, IPv6: {result_stats.ipv6_count}, FC00: {result_stats.fc00_count}")

        # 验证是否还有残留IP
        if result_stats.total_count > 0:
            print(f"  [WARN] 处理后仍有 {result_stats.total_count} 个IP未被脱敏!")
        else:
            print(f"  [OK] 所有IP已被脱敏")


def test_processor_module():
    """测试 FileProcessor 模块"""
    print("\n\n" + "=" * 60)
    print("测试 FileProcessor 模块 (部分脱敏模式)")
    print("=" * 60)

    processor = FileProcessor(partial_anonymize=True)

    test_cases = [
        "::ffff:192.168.1.1",
        "::ffff:c0a8:0101",
        "2001:db8::192.168.1.1",
        "0:0:0:0:0:ffff:192.168.1.1",
        "fc00::192.168.1.1",
        "连接到 ::ffff:10.0.0.1 服务器",
        "地址范围: ::ffff:192.168.1.1-::ffff:192.168.1.10",
    ]

    for text in test_cases:
        print(f"\n原始文本: {text}")
        result_text, ip_count = processor.process_text_content(text)
        print(f"  脱敏结果: {result_text}")
        print(f"  检测到 {ip_count} 个IP")

        # 简单验证：检查结果中是否还包含明显的IP格式
        import re
        ipv4_left = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', result_text)
        # 过滤掉 x.x.x.x 格式
        real_ipv4_left = [ip for ip in ipv4_left if 'x' not in ip]
        if real_ipv4_left:
            print(f"  [WARN] 处理后仍有残留IPv4: {real_ipv4_left}")
        else:
            print(f"  [OK] 无残留IPv4地址")


def test_full_mode():
    """测试完全脱敏模式"""
    print("\n\n" + "=" * 60)
    print("测试完全脱敏模式 (IPAnonymizerCore)")
    print("=" * 60)

    core = IPAnonymizerCore(partial_anonymize=False)

    test_cases = [
        "::ffff:192.168.1.1",
        "2001:db8::192.168.1.1",
        "fc00::192.168.1.1",
    ]

    for text in test_cases:
        print(f"\n原始文本: {text}")
        result_text, process_stats = core.process_text(text)
        result_stats = core.count_ips_in_text(result_text)
        print(f"  脱敏结果: {result_text}")
        print(f"  已处理统计 - IPv4: {process_stats.ipv4_count}, IPv6: {process_stats.ipv6_count}, FC00: {process_stats.fc00_count}")
        print(f"  处理后统计 - IPv4: {result_stats.ipv4_count}, IPv6: {result_stats.ipv6_count}, FC00: {result_stats.fc00_count}")


if __name__ == "__main__":
    test_core_module()
    test_processor_module()
    test_full_mode()
    print("\n\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
