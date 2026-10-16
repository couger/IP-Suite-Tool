#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from models.model_anonymizer_core import IPAnonymizerCore
from models.model_anonymizer_processor import FileProcessor


IP_CASES = [
    ("ipv4_private", "server=192.168.1.1"),
    ("ipv4_public", "DNS:8.8.8.8, backup:1.1.1.1"),
    ("ipv4_adjacent_text", "prefixA10.0.0.1suffix"),
    ("ipv6_loopback", "loopback::1done"),
    ("ipv6_compressed", "route 2001:db8::1 ok"),
    ("ipv6_full", "addr=2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
    ("ipv6_fc00", "src fc00:0:0:0:0:0:0:1"),
    ("ipv6_fc00_compressed", "dst=fc00::1"),
    ("ipv4_mapped_dotted", "::ffff:192.168.1.1"),
    ("ipv4_mapped_hex", "::ffff:c0a8:0101"),
    ("ipv4_compatible", "::192.168.1.1"),
    ("ipv6_embedded_prefix", "2001:db8::192.168.1.1"),
    ("fc00_embedded_ipv4", "fc00::192.168.1.1"),
    (
        "range_mixed",
        "range fc00:0:0:0:0:0:0:1-fc00:0:0:0:0:0:0:2",
    ),
    ("paragraph", "连接到::ffff:10.0.0.1服务器，再访问2001:db8::2。"),
]


def assert_fully_anonymized(core, text):
    processed, stats = core.process_text(text)
    assert stats.total_count >= 1, text
    assert core.count_ips_in_text(processed).total_count == 0, processed
    return processed


def test_core_maximal_ip_detection_partial_mode():
    core = IPAnonymizerCore(partial_anonymize=True)
    for _name, text in IP_CASES:
        assert_fully_anonymized(core, text)


def test_core_maximal_ip_detection_full_mode():
    core = IPAnonymizerCore(partial_anonymize=False)
    for _name, text in IP_CASES:
        assert_fully_anonymized(core, text)


def test_file_processor_uses_same_core_rules():
    processor = FileProcessor(partial_anonymize=True)
    for _name, text in IP_CASES:
        processed, ip_count = processor.process_text_content(text)
        assert ip_count >= 1, text
        assert processor.ip_core.count_ips_in_text(processed).total_count == 0, processed
