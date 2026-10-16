"""
IP地址分配核心逻辑模块

该模块负责处理IP地址的自动分配逻辑，包括：
1. 读取和解析IP申请表
2. 检查设备是否已分配（防重复分配）
3. 根据站点和业务类型获取网段（当前使用静态占位）
4. 自动分配IPv6和IPv4地址（当前使用简单逻辑）
5. 更新申请表和总表

作者：IP-Suite-Tool
创建时间：2026-02-27
版本：1.0.0
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import pandas as pd

from utils.logger_config import setup_module_logger
from utils.table_schema import canonical_column

logger = setup_module_logger(__name__)


class IPAllocationCore:
    """Experimental generic allocation core.

    Uses common location/resource fields and static documentation addresses.
    It does not implement a production pool or collision-safe allocation.
    Common input aliases are normalized, and original input labels are
    restored on export. No full customer template is defined here.
    """

    # Excel表格中的关键列名
    COLUMN_APPLICATION_ID = "记录编号"
    COLUMN_SITE = "位置"
    COLUMN_DEVICE_POINT = "资源标识"
    COLUMN_IPV6_ADDRESS = "IPv6地址"
    COLUMN_IPV4_ADDRESS = "IPv4地址"
    COLUMN_GATEWAY = "网关"
    COLUMN_MASK = "掩码"
    COLUMN_BUSINESS = "业务类别"

    # 固定的掩码值
    IPV6_MASK = "/112"
    IPV4_MASK = "/24"

    # 静态占位IP地址（临时方案）
    PLACEHOLDER_IPV6_PREFIX = "2001:db8:1::"  # IPv6地址前缀
    PLACEHOLDER_IPV4_PREFIX = "192.0.2."    # IPv4地址前缀
    PLACEHOLDER_IPV6_GATEWAY = "2001:db8:1::1"
    PLACEHOLDER_IPV4_GATEWAY = "192.0.2.1"

    def __init__(self):
        """初始化IP地址分配核心类"""
        self.application_df: Optional[pd.DataFrame] = None  # 申请表数据
        self.master_df: Optional[pd.DataFrame] = None       # 总表数据
        self.plan_df: Optional[pd.DataFrame] = None         # 规划表数据
        self._application_labels = {}
        self._master_labels = {}
        self.allocation_results: List[Dict] = []            # 分配结果列表

        logger.info("IP地址分配核心模块初始化完成")

    def load_application_table(self, file_path: str) -> bool:
        """
        加载IP申请表

        Args:
            file_path: 申请表文件路径

        Returns:
            bool: 加载是否成功

        流程：
        1. 检查文件是否存在
        2. 读取Excel文件
        3. 验证必要列是否存在
        4. 存储到内存中
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"申请表文件不存在: {file_path}")
                return False

            frame = pd.read_excel(file_path, dtype=object)
            self._application_labels = {canonical_column(col): col for col in frame.columns}
            self.application_df = frame.rename(columns=canonical_column)
            if self.application_df.columns.duplicated().any():
                raise ValueError("申请表列名规范化后重复")
            logger.info(f"成功加载申请表，共 {len(self.application_df)} 条记录")

            # 验证必要列
            required_columns = [
                self.COLUMN_SITE,
                self.COLUMN_DEVICE_POINT,
                self.COLUMN_BUSINESS
            ]

            missing_columns = [col for col in required_columns if col not in self.application_df.columns]
            if missing_columns:
                logger.error(f"申请表缺少必要列: {missing_columns}")
                return False

            return True

        except Exception as e:
            logger.error(f"加载申请表失败: {e}", exc_info=True)
            return False

    def load_master_table(self, file_path: str) -> bool:
        """
        加载IP申请表总表

        Args:
            file_path: 总表文件路径

        Returns:
            bool: 加载是否成功

        流程：
        1. 检查文件是否存在
        2. 读取Excel文件（如果不存在则创建空表）
        3. 验证必要列是否存在
        4. 存储到内存中
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"总表文件不存在，将创建新文件: {file_path}")
                # 创建空的总表DataFrame
                self.master_df = pd.DataFrame(columns=[
                    self.COLUMN_APPLICATION_ID,
                    self.COLUMN_SITE,
                    self.COLUMN_DEVICE_POINT,
                    self.COLUMN_IPV6_ADDRESS,
                    self.COLUMN_IPV4_ADDRESS,
                    self.COLUMN_GATEWAY,
                    self.COLUMN_MASK,
                    self.COLUMN_BUSINESS
                ])
                logger.info("已创建空的总表")
                return True

            frame = pd.read_excel(file_path, dtype=object)
            self._master_labels = {canonical_column(col): col for col in frame.columns}
            self.master_df = frame.rename(columns=canonical_column)
            if self.master_df.columns.duplicated().any():
                raise ValueError("总表列名规范化后重复")
            logger.info(f"成功加载总表，共 {len(self.master_df)} 条记录")

            return True

        except Exception as e:
            logger.error(f"加载总表失败: {e}", exc_info=True)
            return False

    def load_plan_table(self, file_path: str) -> bool:
        """
        加载IP地址规划表

        Args:
            file_path: 规划表文件路径

        Returns:
            bool: 加载是否成功

        注意：
        当前版本暂不使用规划表，使用静态占位IP地址
        TODO: 后续实现从规划表获取网段的逻辑
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"规划表文件不存在: {file_path}")
                logger.warning("将使用静态占位IP地址")
                return True

            self.plan_df = pd.read_excel(file_path)
            logger.info(f"成功加载规划表，共 {len(self.plan_df)} 条记录")

            return True

        except Exception as e:
            logger.error(f"加载规划表失败: {e}", exc_info=True)
            return False

    def check_device_exists(self, site: str, device_point: str) -> bool:
        """
        检查设备是否已在总表中分配

        Args:
            site: 站点名称
            device_point: 设备点位

        Returns:
            bool: True表示已存在（已分配），False表示不存在（未分配）

        流程：
        1. 检查总表是否已加载
        2. 在总表中查找匹配的站点和设备点位
        3. 返回是否存在
        """
        if self.master_df is None or len(self.master_df) == 0:
            return False

        # 查找匹配记录
        mask = (
            (self.master_df[self.COLUMN_SITE] == site) &
            (self.master_df[self.COLUMN_DEVICE_POINT] == device_point)
        )

        exists = mask.any()

        if exists:
            logger.info(f"设备已分配 - 站点: {site}, 设备点位: {device_point}")

        return exists

    def get_network_segment(self, site: str, business: str) -> Tuple[str, str]:
        """
        根据站点和业务类型获取网段

        Args:
            site: 站点名称
            business: 业务类型

        Returns:
            Tuple[str, str]: (IPv6网段前缀, IPv4网段前缀)

        注意：
        当前版本使用静态占位IP地址
        TODO: 实现从规划表动态获取网段的逻辑

        实现思路（后续开发）：
        1. 在规划表中查找匹配的站点和业务类型
        2. 提取对应的IPv6和IPv4网段
        3. 返回网段前缀供地址分配使用
        """
        # TODO: 实现从规划表获取网段的逻辑
        # 当前使用静态占位值
        logger.debug(f"获取网段 - 站点: {site}, 业务: {business} (使用静态占位)")

        return self.PLACEHOLDER_IPV6_PREFIX, self.PLACEHOLDER_IPV4_PREFIX

    def allocate_ip_address(self, ipv6_prefix: str, ipv4_prefix: str, index: int) -> Tuple[str, str]:
        """
        分配IP地址

        Args:
            ipv6_prefix: IPv6网段前缀
            ipv4_prefix: IPv4网段前缀
            index: 地址索引（用于生成唯一地址）

        Returns:
            Tuple[str, str]: (IPv6地址, IPv4地址)

        注意：
        当前版本使用简单的递增逻辑
        TODO: 实现智能地址分配算法

        实现思路（后续开发）：
        1. 从网段中查找已使用的地址
        2. 找到下一个可用的地址
        3. 确保地址不冲突
        4. 支持地址池管理
        """
        # TODO: 实现智能地址分配算法
        # 当前使用简单的递增逻辑

        # IPv6地址：前缀 + 十六进制索引
        ipv6_address = f"{ipv6_prefix}{index + 2:x}"  # +2 跳过网关地址

        # IPv4地址：前缀 + 十进制索引
        ipv4_address = f"{ipv4_prefix}{index + 2}"  # +2 跳过网关地址

        logger.debug(f"分配IP地址 - IPv6: {ipv6_address}, IPv4: {ipv4_address}")

        return ipv6_address, ipv4_address

    def calculate_gateway_and_mask(self, ipv6_prefix: str, ipv4_prefix: str) -> Tuple[str, str]:
        """
        计算网关和掩码

        Args:
            ipv6_prefix: IPv6网段前缀
            ipv4_prefix: IPv4网段前缀

        Returns:
            Tuple[str, str]: (网关, 掩码)

        规则：
        - 网关：取网段的首地址（例如：2001:db8::1）
        - 掩码：固定值（IPv6: /112, IPv4: /24）
        """
        # 网关取首地址
        ipv6_gateway = f"{ipv6_prefix}1"
        ipv4_gateway = f"{ipv4_prefix}1"

        # 组合网关和掩码（使用逗号分隔，更清晰）
        gateway = f"{ipv6_gateway}, {ipv4_gateway}"
        mask = f"{self.IPV6_MASK}, {self.IPV4_MASK}"

        return gateway, mask

    def process_allocation(self, application_id: str) -> Dict:
        """
        处理IP地址分配

        Args:
            application_id: 申请单号

        Returns:
            Dict: 分配结果统计

        完整分配流程：
        ====================

        1. 遍历申请表中的每条记录
        2. 对每条记录执行以下步骤：
           a. 检查设备是否已分配
           b. 如果已分配，跳过并记录
           c. 如果未分配，继续处理
           d. 获取网段信息
           e. 分配IP地址
           f. 计算网关和掩码
           g. 填写申请单号
           h. 更新申请表
           i. 追加到总表
        3. 返回分配统计结果
        """
        if self.application_df is None:
            logger.error("申请表未加载")
            return {"success": False, "message": "申请表未加载"}

        # 统计信息
        total_count = len(self.application_df)
        allocated_count = 0
        skipped_count = 0
        error_count = 0

        logger.info(f"开始处理IP地址分配，共 {total_count} 条申请")
        logger.info(f"申请单号: {application_id}")

        # 遍历申请表
        for index, row in self.application_df.iterrows():
            try:
                site = row.get(self.COLUMN_SITE, "")
                device_point = row.get(self.COLUMN_DEVICE_POINT, "")
                business = row.get(self.COLUMN_BUSINESS, "")

                logger.info(f"处理第 {index + 1} 条 - 站点: {site}, 设备点位: {device_point}, 业务: {business}")

                # 步骤1: 检查设备是否已分配
                if self.check_device_exists(site, device_point):
                    logger.info(f"跳过 - 设备已分配: {site} - {device_point}")
                    skipped_count += 1
                    continue

                # 步骤2: 获取网段
                ipv6_prefix, ipv4_prefix = self.get_network_segment(site, business)

                # 步骤3: 分配IP地址
                ipv6_address, ipv4_address = self.allocate_ip_address(
                    ipv6_prefix, ipv4_prefix, allocated_count
                )

                # 步骤4: 计算网关和掩码
                gateway, mask = self.calculate_gateway_and_mask(ipv6_prefix, ipv4_prefix)

                # 步骤5: 更新申请表
                self.application_df.at[index, self.COLUMN_APPLICATION_ID] = application_id
                self.application_df.at[index, self.COLUMN_IPV6_ADDRESS] = ipv6_address
                self.application_df.at[index, self.COLUMN_IPV4_ADDRESS] = ipv4_address
                self.application_df.at[index, self.COLUMN_GATEWAY] = gateway
                self.application_df.at[index, self.COLUMN_MASK] = mask

                # 步骤6: 追加到总表
                new_record = {
                    self.COLUMN_APPLICATION_ID: application_id,
                    self.COLUMN_SITE: site,
                    self.COLUMN_DEVICE_POINT: device_point,
                    self.COLUMN_IPV6_ADDRESS: ipv6_address,
                    self.COLUMN_IPV4_ADDRESS: ipv4_address,
                    self.COLUMN_GATEWAY: gateway,
                    self.COLUMN_MASK: mask,
                    self.COLUMN_BUSINESS: business
                }

                if self.master_df is None:
                    self.master_df = pd.DataFrame([new_record])
                else:
                    self.master_df = pd.concat([self.master_df, pd.DataFrame([new_record])], ignore_index=True)

                # 记录分配结果
                self.allocation_results.append(new_record)

                allocated_count += 1
                logger.info(f"分配成功 - IPv6: {ipv6_address}, IPv4: {ipv4_address}")

            except Exception as e:
                logger.error(f"处理第 {index + 1} 条记录时出错: {e}", exc_info=True)
                error_count += 1

        # 返回统计结果
        result = {
            "success": True,
            "total": total_count,
            "allocated": allocated_count,
            "skipped": skipped_count,
            "error": error_count,
            "message": f"分配完成：成功 {allocated_count} 条，跳过 {skipped_count} 条，错误 {error_count} 条"
        }

        logger.info(result["message"])

        return result

    def save_application_table(self, file_path: str) -> bool:
        """
        保存申请表

        Args:
            file_path: 保存路径

        Returns:
            bool: 保存是否成功
        """
        try:
            if self.application_df is None:
                logger.error("申请表数据为空")
                return False

            self.application_df.rename(columns=self._application_labels).to_excel(file_path, index=False)
            logger.info(f"申请表已保存: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存申请表失败: {e}", exc_info=True)
            return False

    def save_master_table(self, file_path: str) -> bool:
        """
        保存总表

        Args:
            file_path: 保存路径

        Returns:
            bool: 保存是否成功
        """
        try:
            if self.master_df is None:
                logger.error("总表数据为空")
                return False

            self.master_df.rename(columns=self._master_labels).to_excel(file_path, index=False)
            logger.info(f"总表已保存: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存总表失败: {e}", exc_info=True)
            return False

    def get_allocation_summary(self) -> str:
        """
        获取分配结果摘要

        Returns:
            str: 分配结果摘要文本
        """
        if not self.allocation_results:
            return "无分配记录"

        summary_lines = [
            "=" * 60,
            "IP地址分配结果摘要",
            "=" * 60,
            f"总分配数量: {len(self.allocation_results)}",
            "",
            "详细分配记录："
        ]

        for i, record in enumerate(self.allocation_results, 1):
            summary_lines.extend([
                f"\n{i}. 申请单号: {record.get(self.COLUMN_APPLICATION_ID, 'N/A')}",
                f"   站点: {record.get(self.COLUMN_SITE, 'N/A')}",
                f"   设备点位: {record.get(self.COLUMN_DEVICE_POINT, 'N/A')}",
                f"   业务: {record.get(self.COLUMN_BUSINESS, 'N/A')}",
                f"   IPv6地址: {record.get(self.COLUMN_IPV6_ADDRESS, 'N/A')}",
                f"   IPv4地址: {record.get(self.COLUMN_IPV4_ADDRESS, 'N/A')}",
                f"   网关: {record.get(self.COLUMN_GATEWAY, 'N/A')}",
                f"   掩码: {record.get(self.COLUMN_MASK, 'N/A')}"
            ])

        summary_lines.append("\n" + "=" * 60)

        return "\n".join(summary_lines)
