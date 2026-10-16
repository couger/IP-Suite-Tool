#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件处理器模块 - IP地址脱敏功能

该模块提供了对Excel、Word、TXT文件中IP地址进行脱敏处理的功能，
支持GUI界面集成和批量处理操作。
"""

import docx
import os
import re
import sys
# import ipaddress
from datetime import datetime
from pathlib import Path
# from typing import List, Dict, Tuple, Optional
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
import logging

# GUI相关导入

# 导入IP核心处理模块
# from .model_anonymizer_core import IPAnonymizerCore, IPStats
from .model_anonymizer_core import IPAnonymizerCore

# 文件处理相关导入 - 添加详细错误信息
EXCEL_SUPPORT = False
WORD_SUPPORT = False
IMPORT_ERRORS = []

# 统一的导入处理
load_workbook = None  # 初始化为None,避免Pylance警告


def _safe_print(message):
    """避免Windows GBK控制台无法输出emoji时中断处理流程。"""
    try:
        logging.getLogger(__name__).debug("Processing event")
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_message = str(message).encode(encoding, errors="replace").decode(encoding)
        logging.getLogger(__name__).debug("Processing event")

try:
    from openpyxl import load_workbook
    # import pandas as pd
    # import xlrd
    # from xlwt import Workbook as XlwtWorkbook
    # import zipfile
    # import msoffcrypto
    # import io
    # print("✓ 所有依赖库导入成功")
    EXCEL_SUPPORT = True
    WORD_SUPPORT = True
except ImportError as e:
    error_msg = f"✗ 依赖库导入失败: {e}"
    # print(error_msg)
    IMPORT_ERRORS.append(error_msg)

    # 逐个检查具体哪个库导入失败
    individual_imports = [
        ('openpyxl', 'load_workbook'),
        ('pandas', 'pd'),
        ('xlrd', 'xlrd'),
        ('xlwt', 'XlwtWorkbook'),
        ('zipfile', 'zipfile'),
        ('msoffcrypto', 'msoffcrypto'),
        ('io', 'io'),
        ('docx', 'docx')
    ]

    for module_name, import_name in individual_imports:
        try:
            __import__(module_name)
        except ImportError as individual_error:
            IMPORT_ERRORS.append(f"✗ {module_name} 导入失败: {individual_error}")


# 打印最终状态
'''
print(f"\n=== 导入状态摘要 ===")
print(f"EXCEL_SUPPORT: {EXCEL_SUPPORT}")
print(f"WORD_SUPPORT: {WORD_SUPPORT}")
if IMPORT_ERRORS:
    print("导入错误详情:")
    for error in IMPORT_ERRORS:
        print(f"  {error}")
print("==================\n")

'''

# 支持的文件类型
SUPPORTED_EXTENSIONS = {
    '.xlsx': 'Excel文件',
    '.xls': 'Excel文件',
    '.txt': '文本文件',
    '.docx': 'Word文件'
}


@dataclass
class ProcessingResult:
    """处理结果数据类"""
    file_path: str
    status: str  # 'success', 'error', 'skipped'
    original_size: int
    processed_size: int
    ip_count: int
    error_message: str = ""
    output_path: str = ""


@dataclass
class ProcessingStats:
    """处理统计信息"""
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_ips_found: int = 0
    processing_time: float = 0.0
    unprocessed_files: List[str] = field(default_factory=list)


class FileProcessor:
    """文件处理器主类"""

    def __init__(self, partial_anonymize: bool = True):
        """初始化文件处理器

        Args:
            partial_anonymize: 是否使用部分脱敏模式
        """
        self.partial_anonymize = partial_anonymize
        self.error_records = []
        self.stats = ProcessingStats()
        self._stop_requested = False
        self.ip_core = IPAnonymizerCore(
            partial_anonymize=partial_anonymize)  # 添加IP核心处理器

    def set_anonymize_mode(self, partial: bool):
        """设置脱敏模式"""
        self.partial_anonymize = partial
        self.ip_core.set_anonymize_mode(partial)

    def anonymize_ipv4(self, match):
        """将IPv4地址脱敏"""
        ip_str = match.group(0)

        if not self.partial_anonymize:
            return "172.x.x.x"

        # 部分保留格式：只对第2、3部分进行脱敏
        try:
            ip_parts = ip_str.split('.')
            if len(ip_parts) == 4:
                # 保留第1和第4部分，将第2、3部分替换为x
                return f"{ip_parts[0]}.x.x.{ip_parts[3]}"
            else:
                return "x.x.x.x"
        except Exception:
            return "x.x.x.x"

    def anonymize_ipv6(self, match):
        """将IPv6地址脱敏 - 修复为正确的8部分格式"""
        ip_str = match.group(0)

        if not self.partial_anonymize:
            return "FC00:****:****:****:****:****:****:****"

        try:
            # 将IPv6地址标准化为8段格式
            full_parts = self._normalize_ipv6_to_eight_segments(ip_str)

            # 对指定段进行脱敏（第2、3、4段，索引1,2,3）
            full_parts[1] = "****"  # 第2部分
            full_parts[2] = "****"  # 第3部分
            full_parts[3] = "****"  # 第4部分

            return ":".join(full_parts)

        except Exception as e:
            logging.getLogger(__name__).debug("Processing event")
            return "FC00:****:****:****:****:****:****:****"

    def _normalize_ipv6_to_eight_segments(self, ip_str):
        """将IPv6地址标准化为8段格式"""
        # 处理特殊情况
        if ip_str == "::1":
            return ["0", "0", "0", "0", "0", "0", "0", "1"]
        elif ip_str == "::":
            return ["0", "0", "0", "0", "0", "0", "0", "0"]
        elif ip_str.startswith("::"):
            # ::开头的情况
            right_part = ip_str[2:]  # 去掉::
            right_segments = right_part.split(":") if right_part else []
            # 在前面补足0段
            missing_count = 8 - len(right_segments)
            return ["0"] * missing_count + right_segments
        elif ip_str.endswith("::"):
            # ::结尾的情况
            left_part = ip_str[:-2]  # 去掉::
            left_segments = left_part.split(":") if left_part else []
            # 在后面补足0段
            missing_count = 8 - len(left_segments)
            return left_segments + ["0"] * missing_count
        elif "::" in ip_str:
            # 中间有::的情况
            parts = ip_str.split("::")
            left_segments = parts[0].split(":") if parts[0] else []
            right_segments = parts[1].split(":") if parts[1] else []

            # 计算中间需要补多少个0段
            middle_zeros = 8 - len(left_segments) - len(right_segments)
            if middle_zeros < 0:
                middle_zeros = 0

            return left_segments + ["0"] * middle_zeros + right_segments
        else:
            # 标准格式，直接分割
            segments = ip_str.split(":")
            # 补足到8段
            while len(segments) < 8:
                segments.append("0")
            return segments[:8]  # 最多取8段

    def process_text_content(self, content: str) -> tuple:
        """处理文本内容中的IP地址"""
        if not isinstance(content, str):
            return content, 0

        processed_content, stats = self.ip_core.process_text(content)
        return processed_content, stats.total_count

    def _process_docx_paragraph(self, paragraph) -> int:
        """按run替换Word段落文本，尽量保留原有字符格式。"""
        runs = list(paragraph.runs)
        if not runs:
            return 0

        original_text = "".join(run.text for run in runs)
        if not original_text:
            return 0

        matches = self.ip_core._iter_ip_matches(original_text)
        if not matches:
            return 0

        run_spans = []
        cursor = 0
        for index, run in enumerate(runs):
            start = cursor
            cursor += len(run.text)
            run_spans.append((index, start, cursor))

        new_run_texts = [""] * len(runs)

        def run_index_at(position: int) -> int:
            for index, start, end in run_spans:
                if start <= position < end:
                    return index
            return max(0, len(runs) - 1)

        def append_original_segment(start: int, end: int) -> None:
            if start >= end:
                return
            for index, run_start, run_end in run_spans:
                overlap_start = max(start, run_start)
                overlap_end = min(end, run_end)
                if overlap_start < overlap_end:
                    new_run_texts[index] += original_text[overlap_start:overlap_end]

        cursor = 0
        for match in matches:
            append_original_segment(cursor, match.start)
            new_run_texts[run_index_at(match.start)] += self.ip_core._anonymize_match(match)
            cursor = match.end
        append_original_segment(cursor, len(original_text))

        for run, text in zip(runs, new_run_texts):
            run.text = text

        return len(matches)

    def process_txt_file(self, file_path: str, output_path: str) -> ProcessingResult:
        """处理TXT文件"""
        try:
            # 获取文件大小
            original_size = os.path.getsize(file_path)

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()

            # 处理内容中的IP地址
            anonymized_content, ip_count = self.process_text_content(content)

            # 将处理后的内容写入新文件
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(anonymized_content)

            processed_size = os.path.getsize(output_path)

            return ProcessingResult(
                file_path=file_path,
                status='success',
                original_size=original_size,
                processed_size=processed_size,
                ip_count=ip_count,
                output_path=output_path
            )

        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=str(e)
            )

    def process_large_xlsx_file(self, file_path: str, output_path: str) -> ProcessingResult:
        """优化处理大型Excel文件，使用流式处理避免内存问题

        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径

        Returns:
            ProcessingResult: 处理结果
        """
        if not EXCEL_SUPPORT:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="缺少Excel处理库(openpyxl)"
            )

        try:
            original_size = os.path.getsize(file_path)
            logging.getLogger(__name__).debug("Processing event")

            # 使用openpyxl的read_only模式处理大文件
            assert load_workbook is not None, "load_workbook未正确导入"
            wb = load_workbook(filename=file_path, read_only=True)
            _safe_print(f"✅ 成功加载工作簿，工作表数量: {len(wb.sheetnames)}")

            # 创建一个新的工作簿用于写入
            from openpyxl import Workbook
            output_wb = Workbook(write_only=True)

            total_ip_count = 0

            for sheet_name in wb.sheetnames:
                if self._stop_requested:
                    break
                logging.getLogger(__name__).debug("Processing event")

                # 获取原始工作表
                ws = wb[sheet_name]

                # 创建新的工作表
                output_ws = output_wb.create_sheet(title=sheet_name)

                # 遍历所有行
                total_rows = ws.max_row if ws.max_row else 0
                processed_rows = 0

                for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                    if self._stop_requested:
                        break

                    new_row = []

                    for col_idx, cell_value in enumerate(row, 1):
                        if self._stop_requested:
                            break

                        if cell_value is not None and isinstance(cell_value, str):
                            try:
                                # 处理单元格中的文本内容
                                processed_value, ip_count = self.process_text_content(
                                    str(cell_value))
                                new_row.append(processed_value)
                                total_ip_count += ip_count
                            except Exception as e:
                                error_msg = f"处理单元格内容时出错: {str(e)}"
                                _safe_print(
                                    f"❌ {error_msg} - 工作表: {sheet_name}, 单元格: {row_idx}:{col_idx}")

                                # 记录错误信息
                                self.error_records.append({
                                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "文件路径": file_path,
                                    "工作表名": sheet_name,
                                    "行号": row_idx,
                                    "列号": col_idx,
                                    "原始内容": str(cell_value),
                                    "错误信息": error_msg
                                })

                                new_row.append(cell_value)  # 出错时保留原始值
                        else:
                            new_row.append(cell_value)

                    # 写入新行
                    if new_row:  # 只有非空行才写入
                        output_ws.append(new_row)

                    # 显示进度
                    processed_rows += 1
                    if processed_rows % 5000 == 0:
                        logging.getLogger(__name__).debug("Processing event")

                if self._stop_requested:
                    break

            # 保存处理后的文件
            output_wb.save(output_path)
            processed_size = os.path.getsize(output_path)
            _safe_print(f"✅ 已创建脱敏后的Excel文件: {output_path}")

            wb.close()  # 关闭只读工作簿

            return ProcessingResult(
                file_path=file_path,
                status='success',
                original_size=original_size,
                processed_size=processed_size,
                ip_count=total_ip_count,
                output_path=output_path
            )

        except Exception as e:
            error_msg = f"处理大型Excel文件时出错: {str(e)}"
            _safe_print(f"❌ {error_msg}")

            # 记录错误信息
            self.error_records.append({
                "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "文件路径": file_path,
                "工作表名": "",
                "行号": "",
                "列号": "",
                "原始内容": "",
                "错误信息": error_msg
            })

            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=error_msg
            )

    def _is_large_file(self, file_path: str) -> bool:
        """判断是否为大文件

        Args:
            file_path: 文件路径

        Returns:
            bool: True表示大文件，False表示小文件
        """
        try:
            # 获取文件大小（MB）
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            # 检查文件大小是否超过2MB（降低阈值以便测试）
            if file_size_mb > 2:
                logging.getLogger(__name__).debug("Processing event")
                return True

            # 对于较小的文件，检查单元格数量
            if EXCEL_SUPPORT:
                try:
                    assert load_workbook is not None, "load_workbook未正确导入"
                    temp_wb = load_workbook(file_path, read_only=True)
                    # 检查active工作表是否存在
                    if temp_wb.active is not None:
                        max_cells = temp_wb.active.max_row * temp_wb.active.max_column
                    else:
                        # 如果没有活动工作表，则使用第一个工作表
                        if temp_wb.worksheets:
                            first_sheet = temp_wb.worksheets[0]
                            max_cells = first_sheet.max_row * first_sheet.max_column
                        else:
                            # 如果没有任何工作表，设置为一个小的数值
                            max_cells = 0
                    temp_wb.close()

                    # 检查是否超过50万单元格（降低阈值以便测试）
                    if max_cells > 500000:
                        logging.getLogger(__name__).debug("Processing event")
                        return True
                except Exception:
                    # 如果无法准确计算单元格数，默认使用普通处理
                    logging.warning("无法准确计算Excel文件单元格数，使用默认处理方式")

            return False

        except Exception:
            # 出错时默认使用普通处理方式
            return False

    def process_xlsx_file(self, file_path: str, output_path: str) -> ProcessingResult:
        """处理XLSX文件 - 自动选择处理策略

        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径

        Returns:
            ProcessingResult: 处理结果
        """
        if not EXCEL_SUPPORT:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="缺少Excel处理库(openpyxl, pandas等)"
            )

        # 检查是否为大文件，自动选择处理策略
        if self._is_large_file(file_path):
            return self.process_large_xlsx_file(file_path, output_path)

        # 使用原有方法处理小文件
        try:
            original_size = os.path.getsize(file_path)
            assert load_workbook is not None, "load_workbook未正确导入"
            wb = load_workbook(file_path)
            total_ip_count = 0

            # 遍历所有工作表
            for sheet_name in wb.sheetnames:
                if self._stop_requested:
                    break
                ws = wb[sheet_name]

                # 遍历所有单元格
                for row_idx, row in enumerate(ws.iter_rows(), 1):
                    if self._stop_requested:
                        break
                    for col_idx, cell in enumerate(row, 1):
                        if self._stop_requested:
                            break
                        if cell.value is not None and isinstance(cell.value, str):
                            try:
                                original_content = cell.value
                                anonymized_content, ip_count = self.process_text_content(
                                    original_content)

                                if original_content != anonymized_content:
                                    cell.value = anonymized_content
                                    total_ip_count += ip_count

                            except Exception:
                                continue

            # 保存处理后的文件
            wb.save(output_path)
            processed_size = os.path.getsize(output_path)

            return ProcessingResult(
                file_path=file_path,
                status='success',
                original_size=original_size,
                processed_size=processed_size,
                ip_count=total_ip_count,
                output_path=output_path
            )

        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=str(e)
            )

    def process_docx_file(self, file_path: str, output_path: str) -> ProcessingResult:
        """处理DOCX文件"""
        if not WORD_SUPPORT:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="缺少Word处理库(python-docx)"
            )

        try:
            original_size = os.path.getsize(file_path)
            doc = docx.Document(file_path)
            total_ip_count = 0

            # 处理段落
            for paragraph in doc.paragraphs:
                if self._stop_requested:
                    break
                total_ip_count += self._process_docx_paragraph(paragraph)

            # 处理表格
            for table in doc.tables:
                if self._stop_requested:
                    break
                for row in table.rows:
                    if self._stop_requested:
                        break
                    for cell in row.cells:
                        if self._stop_requested:
                            break
                        for paragraph in cell.paragraphs:
                            if self._stop_requested:
                                break
                            total_ip_count += self._process_docx_paragraph(paragraph)

            # 保存处理后的文件
            doc.save(output_path)
            processed_size = os.path.getsize(output_path)

            return ProcessingResult(
                file_path=file_path,
                status='success',
                original_size=original_size,
                processed_size=processed_size,
                ip_count=total_ip_count,
                output_path=output_path
            )

        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=str(e)
            )

    def generate_output_filename(self, original_path: str) -> str:
        """生成带时间戳的输出文件名"""
        path_obj = Path(original_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_without_ext = path_obj.stem
        extension = path_obj.suffix
        return f"{name_without_ext}_anonymized_{timestamp}{extension}"

    def process_single_file(self, file_path: str, output_dir: str) -> ProcessingResult:
        """处理单个文件 - 使用时间戳文件名"""
        if self._stop_requested:
            return ProcessingResult(
                file_path=file_path,
                status='skipped',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="处理被用户中断"
            )

        # 首先检测文件是否包含IP地址
        if not self.detect_ip_in_file(file_path):
            return ProcessingResult(
                file_path=file_path,
                status='skipped',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="文件不包含IP地址，已跳过处理"
            )

        file_extension = os.path.splitext(file_path)[1].lower()
        output_file_name = self.generate_output_filename(file_path)
        # 使用os.path.join正确处理路径分隔符
        output_path = os.path.join(output_dir, output_file_name)

        # 确保输出目录存在，使用exist_ok=True避免重复创建
        try:
            os.makedirs(output_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=f"无法创建输出目录: {str(e)}"
            )

        # 根据文件类型调用相应的处理方法
        if file_extension in ['.xlsx', '.xls']:
            return self.process_xlsx_file(file_path, output_path)
        elif file_extension == '.txt':
            return self.process_txt_file(file_path, output_path)
        elif file_extension == '.docx':
            return self.process_docx_file(file_path, output_path)
        else:
            return ProcessingResult(
                file_path=file_path,
                status='skipped',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=f"不支持的文件类型: {file_extension}"
            )

    def process_files_batch(self, file_paths: List[str], output_dir: str,
                            progress_callback=None) -> Tuple[List[ProcessingResult], ProcessingStats]:
        """批量处理文件"""
        # 重置停止标志
        self._stop_requested = False

        results = []
        stats = ProcessingStats()
        stats.total_files = len(file_paths)

        start_time = datetime.now()

        for i, file_path in enumerate(file_paths):
            if self._stop_requested:
                # 处理剩余未处理的文件为跳过状态
                for remaining_file in file_paths[i:]:
                    skipped_result = ProcessingResult(
                        file_path=remaining_file,
                        status='skipped',
                        original_size=0,
                        processed_size=0,
                        ip_count=0,
                        error_message="处理被用户中断"
                    )
                    results.append(skipped_result)
                    stats.skipped_files += 1
                break

            try:
                result = self.process_single_file(file_path, output_dir)
                results.append(result)

                # 更新统计信息
                if result.status == 'success':
                    stats.successful_files += 1
                    stats.total_ips_found += result.ip_count
                elif result.status == 'error':
                    stats.failed_files += 1
                else:
                    stats.skipped_files += 1

                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, len(file_paths), result)

            except Exception as e:
                error_result = ProcessingResult(
                    file_path=file_path,
                    status='error',
                    original_size=0,
                    processed_size=0,
                    ip_count=0,
                    error_message=str(e)
                )
                results.append(error_result)
                stats.failed_files += 1

                # 记录错误信息
                self.error_records.append({
                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "文件路径": file_path,
                    "错误类型": type(e).__name__,
                    "错误信息": str(e)
                })

                if progress_callback:
                    progress_callback(i + 1, len(file_paths), error_result)

        # 计算处理时间
        end_time = datetime.now()
        stats.processing_time = (end_time - start_time).total_seconds()

        return results, stats

    def process_directory(self, source_dir: str, output_dir: str,
                          progress_callback=None) -> Tuple[List[ProcessingResult], ProcessingStats]:
        """处理整个目录"""
        file_paths = []

        # 递归收集所有支持的文件
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if self._stop_requested:
                    break
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension in SUPPORTED_EXTENSIONS:
                    file_paths.append(file_path)

        return self.process_files_batch(file_paths, output_dir, progress_callback)

    def get_supported_extensions(self) -> Dict[str, str]:
        """获取支持的文件扩展名"""
        extensions = {}
        if EXCEL_SUPPORT:
            extensions.update({'.xlsx': 'Excel文件', '.xls': 'Excel文件'})
        if WORD_SUPPORT:
            extensions['.docx'] = 'Word文件'
        extensions['.txt'] = '文本文件'
        return extensions

    def validate_file_access(self, file_path: str) -> bool:
        """验证文件访问权限"""
        try:
            if not os.path.isfile(file_path):
                return False

            if not os.access(file_path, os.R_OK):
                return False

            with open(file_path, 'rb') as f:
                f.read(1)

            return True
        except (OSError, IOError):
            return False

    def estimate_processing_time(self, file_paths: List[str]) -> float:
        """估算处理时间（简单估算）"""
        total_size = 0
        for file_path in file_paths:
            try:
                total_size += os.path.getsize(file_path)
            except FileNotFoundError:
                # 文件不存在，跳过该文件
                continue

        # 简单估算：每MB大约需要0.1秒
        return (total_size / (1024 * 1024)) * 0.1

    def detect_ip_in_file(self, file_path: str) -> bool:
        """检测文件是否包含IP地址"""
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension in ['.xlsx', '.xls']:
                return self._detect_ip_in_excel(file_path)
            elif file_extension == '.txt':
                return self._detect_ip_in_txt(file_path)
            elif file_extension == '.docx':
                return self._detect_ip_in_docx(file_path)
            else:
                return False
        except Exception:
            return False

    def _detect_ip_in_excel(self, file_path: str) -> bool:
        """检测Excel文件是否包含IP地址"""
        if not EXCEL_SUPPORT:
            return False

        try:
            assert load_workbook is not None, "load_workbook未正确导入"
            wb = load_workbook(file_path, read_only=True)

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for row in ws.iter_rows(values_only=True):
                    for cell_value in row:
                        if cell_value is not None and isinstance(cell_value, str):
                            if self.ip_core.count_ips_in_text(cell_value).total_count:
                                wb.close()
                                return True
            wb.close()
            return False
        except Exception:
            return False

    def _detect_ip_in_txt(self, file_path: str) -> bool:
        """检测TXT文件是否包含IP地址"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()

            return bool(self.ip_core.count_ips_in_text(content).total_count)
        except Exception:
            return False

    def _detect_ip_in_docx(self, file_path: str) -> bool:
        """检测Word文件是否包含IP地址"""
        if not WORD_SUPPORT:
            return False

        try:
            doc = docx.Document(file_path)

            # 检查段落
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    if self.ip_core.count_ips_in_text(paragraph.text).total_count:
                        return True

            # 检查表格
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text:
                            if self.ip_core.count_ips_in_text(cell.text).total_count:
                                return True

            return False
        except Exception:
            return False

    def stop_processing(self):
        """停止当前处理过程"""
        self._stop_requested = True

    def process_single_file_with_structure(self, file_path: str, base_output_dir: str, source_base_dir: str) -> ProcessingResult:
        """处理单个文件并保持目录结构"""
        if self._stop_requested:
            return ProcessingResult(
                file_path=file_path,
                status='skipped',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="处理被用户中断"
            )

        # 首先检测文件是否包含IP地址
        if not self.detect_ip_in_file(file_path):
            return ProcessingResult(
                file_path=file_path,
                status='skipped',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message="文件不包含IP地址，已跳过处理"
            )

        # 计算相对于源目录的路径
        try:
            relative_path = os.path.relpath(file_path, source_base_dir)
        except ValueError:
            # 如果无法计算相对路径，使用文件名
            relative_path = os.path.basename(file_path)

        # 构建输出路径，保持目录结构
        # 只使用相对路径的目录部分，不包括文件名
        relative_dir = os.path.dirname(relative_path)  # 获取相对路径中的目录部分
        output_file_name = self.generate_output_filename(file_path)
        # 使用os.path.join正确处理路径分隔符
        output_path = os.path.join(
            base_output_dir, relative_dir, output_file_name)

        # 确保输出目录存在，使用更安全的方式创建目录
        try:
            output_dir = os.path.dirname(output_path)
            # 验证输出路径安全性
            normalized_output = os.path.normpath(output_path)
            normalized_base = os.path.normpath(base_output_dir)
            if not normalized_output.startswith(normalized_base):
                raise ValueError("Output path outside of base directory")

            os.makedirs(output_dir, exist_ok=True)
        except (OSError, PermissionError, ValueError) as e:
            return ProcessingResult(
                file_path=file_path,
                status='error',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=f"无法创建输出目录结构: {str(e)}"
            )

        # 根据文件类型调用相应的处理方法
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in ['.xlsx', '.xls']:
            return self.process_xlsx_file(file_path, output_path)
        elif file_extension == '.txt':
            return self.process_txt_file(file_path, output_path)
        elif file_extension == '.docx':
            return self.process_docx_file(file_path, output_path)
        else:
            return ProcessingResult(
                file_path=file_path,
                status='skipped',
                original_size=0,
                processed_size=0,
                ip_count=0,
                error_message=f"不支持的文件类型: {file_extension}"
            )

    def process_files_batch_with_structure(self, file_paths: List[str], output_dir: str,
                                           progress_callback=None) -> Tuple[List, ProcessingStats]:
        """批量处理文件并保持目录结构

        Args:
            file_paths: 要处理的文件路径列表
            output_dir: 输出目录
            progress_callback: 进度回调函数

        Returns:
            tuple: (处理结果列表, 处理统计信息)
        """
        # 重置停止标志
        self._stop_requested = False

        # 清空之前的错误记录
        self.error_records = []

        results = []
        stats = ProcessingStats()
        stats.total_files = len(file_paths)

        # 确定源文件的共同基目录
        if not file_paths:
            return results, stats

        input_dirs = [os.path.dirname(path) for path in file_paths]
        try:
            source_base_dir = os.path.commonpath(input_dirs)
        except ValueError:
            source_base_dir = os.path.dirname(file_paths[0])

        start_time = datetime.now()

        for i, file_path in enumerate(file_paths):
            if self._stop_requested:
                # 处理剩余未处理的文件为跳过状态
                for remaining_file in file_paths[i:]:
                    skipped_result = ProcessingResult(
                        file_path=remaining_file,
                        status='skipped',
                        original_size=0,
                        processed_size=0,
                        ip_count=0,
                        error_message="处理被用户中断"
                    )
                    results.append(skipped_result)
                    stats.skipped_files += 1
                break

            try:
                result = self.process_single_file_with_structure(
                    file_path, output_dir, source_base_dir)
                results.append(result)

                # 更新统计信息
                if result.status == 'success':
                    stats.successful_files += 1
                    stats.total_ips_found += result.ip_count
                elif result.status == 'error':
                    stats.failed_files += 1
                    # 记录文件处理错误
                    self.error_records.append({
                        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "文件路径": file_path,
                        "错误类型": "文件处理错误",
                        "错误信息": result.error_message
                    })
                else:
                    stats.skipped_files += 1

                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, len(file_paths), result)

            except Exception as e:
                error_result = ProcessingResult(
                    file_path=file_path,
                    status='error',
                    original_size=0,
                    processed_size=0,
                    ip_count=0,
                    error_message=str(e)
                )
                results.append(error_result)
                stats.failed_files += 1

                # 记录错误信息
                self.error_records.append({
                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "文件路径": file_path,
                    "错误类型": type(e).__name__,
                    "错误信息": str(e)
                })

                if progress_callback:
                    progress_callback(i + 1, len(file_paths), error_result)

        # 计算处理时间
        end_time = datetime.now()
        stats.processing_time = (end_time - start_time).total_seconds()

        # 保存统一的结果记录文件（包含所有信息）
        try:
            self.save_unified_result_report(
                output_dir, stats, getattr(stats, 'unprocessed_files', None))
        except Exception as e:
            _safe_print(f"❌ 保存统一结果记录时出错: {str(e)}")

        return results, stats

    def verify_results(self, results: List[ProcessingResult], output_base_dir: str = "") -> List[str]:
        """验证处理结果，检查是否仍有未处理的IP地址

        Args:
            results: 处理结果列表
            output_base_dir: 输出基础目录（可选）

        Returns:
            list: 包含未处理干净文件路径的列表
        """
        unprocessed_files = []

        for result in results:
            if result.status == 'success':
                try:
                    # 构造对应的输出文件路径
                    if output_base_dir:
                        # 使用传入的输出目录构建路径
                        output_file_path = self._get_output_file_path(
                            result.file_path, output_base_dir)
                    else:
                        # 尝试从结果中推断输出路径
                        output_file_path = self._infer_output_path(
                            result.file_path)

                    # 检查输出文件是否仍然包含原始IP地址
                    if output_file_path and os.path.exists(output_file_path):
                        if self._file_still_contains_ips(output_file_path):
                            unprocessed_files.append(result.file_path)
                    else:
                        # 如果找不到输出文件，也将原文件标记为未处理
                        unprocessed_files.append(result.file_path)

                except Exception as e:
                    logging.getLogger(__name__).debug("Processing event")
                    # 如果验证过程中出错，也将文件标记为未处理
                    unprocessed_files.append(result.file_path)

        return unprocessed_files

    def _get_output_file_path(self, original_file_path: str, output_base_dir: str) -> str:
        """根据原始文件路径和输出基础目录构造输出文件路径"""
        try:
            # 生成带时间戳的输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path_obj = Path(original_file_path)
            name_without_ext = path_obj.stem
            extension = path_obj.suffix
            output_file_name = f"{name_without_ext}_anonymized_{timestamp}{extension}"

            # 构造完整输出路径
            output_path = os.path.join(output_base_dir, output_file_name)
            return output_path
        except Exception:
            return ""

    def _infer_output_path(self, original_file_path: str) -> str:
        """尝试推断输出文件路径"""
        # 这是一个简化实现，实际应用中可能需要更复杂的逻辑
        # 暂时返回None，表示无法推断
        return ""

    def _file_still_contains_ips(self, file_path: str) -> bool:
        """检查文件是否仍然包含IP地址

        Args:
            file_path: 文件路径

        Returns:
            bool: 如果文件包含IP地址返回True，否则返回False
        """
        return self.detect_ip_in_file(file_path)

    def save_unified_result_report(self, output_folder, stats, unprocessed_files=None):
        """保存统一的结果记录文件（包含所有信息）"""
        try:
            import pandas as pd

            # 使用os.path.join正确处理路径分隔符
            report_path = os.path.join(output_folder, "结果记录.xlsx")

            # 验证路径安全性
            normalized_path = os.path.normpath(report_path)
            normalized_folder = os.path.normpath(output_folder)
            if not normalized_path.startswith(normalized_folder):
                raise ValueError("Report path outside of output folder")

            # 确保输出目录存在
            try:
                os.makedirs(output_folder, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise IOError(f"无法创建输出目录: {str(e)}")

            # 准备统计摘要数据
            summary_data = [{
                "项目": "总文件数",
                "数值": stats.total_files
            }, {
                "项目": "成功处理文件数",
                "数值": stats.successful_files
            }, {
                "项目": "处理失败文件数",
                "数值": stats.failed_files
            }, {
                "项目": "跳过文件数",
                "数值": stats.skipped_files
            }, {
                "项目": "发现IP地址总数",
                "数值": stats.total_ips_found
            }, {
                "项目": "处理耗时(秒)",
                "数值": round(stats.processing_time, 2)
            }]

            summary_df = pd.DataFrame(summary_data)

            # 准备错误记录数据
            error_df = None
            if self.error_records:
                error_df = pd.DataFrame(self.error_records)

            # 准备未处理文件数据
            unprocessed_df = None
            if unprocessed_files:
                unprocessed_data = []
                for file_path in unprocessed_files:
                    unprocessed_data.append({
                        "文件路径": file_path,
                        "问题描述": "文件中仍存在未脱敏的IP地址"
                    })
                unprocessed_df = pd.DataFrame(unprocessed_data)

            # 保存到Excel文件（多个工作表）
            with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                # 保存统计摘要
                summary_df.to_excel(writer, index=False, sheet_name='处理统计')
                summary_worksheet = writer.sheets['处理统计']

                # 调整统计表列宽
                for column in summary_worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except (AttributeError, TypeError):
                            # 忽略无法处理的单元格值类型
                            continue
                    adjusted_width = min(max_length + 2, 30)
                    summary_worksheet.column_dimensions[column_letter].width = adjusted_width

                # 保存错误记录（如果存在）
                if error_df is not None and not error_df.empty:
                    error_df.to_excel(writer, index=False, sheet_name='错误记录')
                    error_worksheet = writer.sheets['错误记录']

                    # 调整错误记录表列宽
                    for column in error_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                # 忽略无法处理的单元格值类型
                                continue
                        adjusted_width = min(max_length + 2, 50)
                        error_worksheet.column_dimensions[column_letter].width = adjusted_width
                else:
                    # 即使没有错误也创建空的错误记录表
                    empty_error_df = pd.DataFrame([{
                        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "文件路径": "N/A",
                        "工作表名": "N/A",
                        "行号": "N/A",
                        "列号": "N/A",
                        "原始内容": "N/A",
                        "错误信息": "处理完成，无错误发生"
                    }])
                    empty_error_df.to_excel(
                        writer, index=False, sheet_name='错误记录')
                    error_worksheet = writer.sheets['错误记录']
                    # 调整列宽
                    for column in error_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                # 忽略无法处理的单元格值类型
                                continue
                        adjusted_width = min(max_length + 2, 50)
                        error_worksheet.column_dimensions[column_letter].width = adjusted_width

                # 保存未处理文件列表（如果有）
                if unprocessed_df is not None and not unprocessed_df.empty:
                    unprocessed_df.to_excel(
                        writer, index=False, sheet_name='验证结果')
                    unprocessed_worksheet = writer.sheets['验证结果']

                    # 调整验证结果表列宽
                    for column in unprocessed_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except (AttributeError, TypeError):
                                # 忽略无法处理的单元格值类型
                                continue
                        adjusted_width = min(max_length + 2, 50)
                        unprocessed_worksheet.column_dimensions[column_letter].width = adjusted_width

            _safe_print(f"✅ 统一结果记录已保存到: {report_path}")
            return True

        except ImportError as e:
            _safe_print(f"❌ 缺少必要的库: {str(e)}")
            return False
        except (IOError, OSError) as e:
            _safe_print(f"❌ 文件操作错误: {str(e)}")
            return False
        except ValueError as e:
            _safe_print(f"❌ 路径验证错误: {str(e)}")
            return False
        except Exception as e:
            _safe_print(f"❌ 保存统一结果记录时出错: {str(e)}")
            return False

    def save_error_log(self, output_folder):
        """保存错误日志到Excel文件（已废弃，保持向后兼容）"""
        # 此方法已废弃，统一使用save_unified_result_report
        _safe_print("⚠️  save_error_log方法已废弃，请使用save_unified_result_report")
        return False

    def save_comprehensive_report(self, output_folder, stats, unprocessed_files=None):
        """保存综合处理报告（已废弃，保持向后兼容）"""
        # 此方法已废弃，统一使用save_unified_result_report
        _safe_print("⚠️  save_comprehensive_report方法已废弃，请使用save_unified_result_report")
        return False
