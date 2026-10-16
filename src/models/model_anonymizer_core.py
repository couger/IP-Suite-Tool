#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一IP地址脱敏核心模块。

采用最大化识别策略：在任意文本中扫描可能的IP地址子串，再交给
ipaddress 做严格校验，避免手写IPv6正则遗漏压缩、IPv4-mapped、
IPv4-compatible、IPv6内嵌IPv4等合法格式。
"""

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import List, Tuple


@dataclass
class IPStats:
    """IP统计信息。"""

    ipv4_count: int = 0
    ipv6_count: int = 0
    fc00_count: int = 0
    total_count: int = 0


@dataclass(frozen=True)
class IPMatch:
    """文本中的一个IP匹配。"""

    start: int
    end: int
    text: str
    version: int
    is_fc00: bool


class IPAnonymizerCore:
    """统一IP地址脱敏核心处理器。"""

    MAX_IP_TOKEN_LENGTH = 45
    TOKEN_CHARS = set("0123456789abcdefABCDEF:.")

    def __init__(self, partial_anonymize: bool = True):
        self.partial_anonymize = partial_anonymize

    def set_anonymize_mode(self, partial: bool):
        """设置脱敏模式。"""
        self.partial_anonymize = partial

    def _parse_ip(self, value: str):
        """解析IP地址；失败返回None。"""
        if not value or value.endswith(".") or value.endswith(":"):
            return None
        if "." not in value and ":" not in value:
            return None
        try:
            return ip_address(value)
        except ValueError:
            return None

    def _iter_ip_matches(self, text: str) -> List[IPMatch]:
        """扫描文本中的最长、非重叠IP地址。"""
        matches: List[IPMatch] = []
        text_len = len(text)
        index = 0

        while index < text_len:
            if text[index] not in self.TOKEN_CHARS:
                index += 1
                continue

            best = None
            max_end = min(text_len, index + self.MAX_IP_TOKEN_LENGTH)

            for end in range(index + 2, max_end + 1):
                candidate = text[index:end]
                if candidate[-1] not in self.TOKEN_CHARS:
                    break
                parsed = self._parse_ip(candidate)
                if parsed is None:
                    continue

                version = 4 if isinstance(parsed, IPv4Address) else 6
                is_fc00 = (
                    isinstance(parsed, IPv6Address)
                    and parsed.exploded.lower().startswith("fc00:")
                )
                best = IPMatch(index, end, candidate, version, is_fc00)

            if best is not None:
                matches.append(best)
                index = best.end
            else:
                index += 1

        return matches

    def _stats_from_matches(self, matches: List[IPMatch]) -> IPStats:
        stats = IPStats()
        for match in matches:
            if match.version == 4:
                stats.ipv4_count += 1
            elif match.is_fc00:
                stats.fc00_count += 1
            else:
                stats.ipv6_count += 1
        stats.total_count = stats.ipv4_count + stats.ipv6_count + stats.fc00_count
        return stats

    def count_ips_in_text(self, text: str) -> IPStats:
        """统计文本中的IP地址数量。"""
        if not isinstance(text, str):
            return IPStats()
        return self._stats_from_matches(self._iter_ip_matches(text))

    def anonymize_ipv4_text(self, ip_str: str) -> str:
        """IPv4地址脱敏处理。"""
        if not self.partial_anonymize:
            return "IPv4-REDACTED"

        first_octet = ip_str.split(".", 1)[0]
        return f"{first_octet}.x.x.x"

    def anonymize_ipv6_text(self, ip_str: str, is_fc00: bool) -> str:
        """IPv6地址脱敏处理。"""
        if not self.partial_anonymize:
            return "IPv6-REDACTED"

        parsed = ip_address(ip_str)
        if isinstance(parsed, IPv4Address):
            return self.anonymize_ipv4_text(ip_str)

        hex_value = f"{int(parsed):032x}"
        segments = [hex_value[i:i + 4] for i in range(0, 32, 4)]
        prefix = "FC00" if is_fc00 else segments[0].lstrip("0") or "0"
        suffix = segments[-1].lstrip("0") or "0"
        return f"{prefix}:****:****:****:****:****:****:{suffix}"

    def _anonymize_match(self, match: IPMatch) -> str:
        if match.version == 4:
            return self.anonymize_ipv4_text(match.text)
        return self.anonymize_ipv6_text(match.text, match.is_fc00)

    def process_text(self, text: str) -> Tuple[str, IPStats]:
        """处理文本中的所有IP地址。

        Returns:
            tuple: (处理后的文本, 处理前统计信息)
        """
        if not isinstance(text, str):
            return text, IPStats()

        matches = self._iter_ip_matches(text)
        stats = self._stats_from_matches(matches)
        if not matches:
            return text, stats

        pieces = []
        last_end = 0
        for match in matches:
            pieces.append(text[last_end:match.start])
            pieces.append(self._anonymize_match(match))
            last_end = match.end
        pieces.append(text[last_end:])
        return "".join(pieces), stats
