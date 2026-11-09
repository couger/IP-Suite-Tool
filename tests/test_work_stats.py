#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime

import pytest
from openpyxl import Workbook, load_workbook

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from ip_work_stats import ExcelShutdownError, WorkStats
from ip_anonymizer import IPAnonymizer
from models.model_anonymizer_processor import FileProcessor, ProcessingResult, ProcessingStats


def _make_workbook(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["其他列", "申请单位名称", "申请人信息"])
    sheet.append(["a", "第一单位", "第一人"])
    sheet.append(["b", "", ""])
    sheet.append(["c", "最终单位", "最终申请人"])
    workbook.save(path)


def _make_workbook_with_offset_header(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["说明", "本行不是标题", ""])
    sheet.append(["其他列", "申请单位名称", "申请人信息"])
    sheet.append(["a", "第一单位", "第一人"])
    sheet.append(["b", "最终单位", "最终申请人"])
    workbook.save(path)


def test_work_stats_extracts_prefix_title_and_last_non_empty_values(tmp_path):
    file_path = tmp_path / "pl202601063001-测试申请表.xlsx"
    _make_workbook(file_path)

    work_stats = object.__new__(WorkStats)
    record = WorkStats._read_record(work_stats, 1, str(file_path))

    assert record.sequence == 1
    assert record.prefix == "pl202601063001"
    assert record.title == "测试申请表"
    assert record.applicant_unit == "最终单位"
    assert record.applicant == "最终申请人"
    assert record.status == "成功"


def test_work_stats_finds_applicant_header_below_first_row(tmp_path):
    file_path = tmp_path / "pl202601063001-多行标题申请表.xlsx"
    _make_workbook_with_offset_header(file_path)

    work_stats = object.__new__(WorkStats)
    record = WorkStats._read_record(work_stats, 1, str(file_path))

    assert record.status == "成功"
    assert record.applicant_unit == "最终单位"
    assert record.applicant == "最终申请人"


def test_work_stats_keeps_add_number_and_exports_columns(tmp_path):
    file_path = tmp_path / "add202604013002.xlsx"
    output_path = tmp_path / "工作统计.xlsx"
    _make_workbook(file_path)

    work_stats = object.__new__(WorkStats)
    records = work_stats._collect_records([str(file_path)])
    WorkStats._save_records(
        work_stats, records, str(output_path), embed_attachments=False
    )

    workbook = load_workbook(output_path, data_only=True)
    sheet = workbook.active

    assert [sheet.cell(1, col).value for col in range(1, 6)] == [
        "序号",
        "前缀",
        "文件名剩余部分",
        "组织",
        "联系人",
    ]
    assert sheet.cell(1, 6).value == "附件"
    assert sheet.cell(2, 2).value == "add202604013002"
    assert sheet.cell(2, 3).value is None
    assert sheet.cell(2, 6).value is None
    assert sheet.cell(2, 7).value == str(file_path)

    workbook.close()


def test_work_stats_generates_daily_numbers_without_colliding_with_later_files(tmp_path, monkeypatch):
    names = [
        "普通文件.txt", "PL202604020001-已有编号.txt", "pl2026040200023-超长.txt",
        "pl202602300001-无效日期.txt", "次日文件.docx",
    ]
    paths = [str(tmp_path / name) for name in names]
    dates = {paths[0]: "20260402", paths[2]: "20260402", paths[3]: "20260402", paths[4]: "20260403"}
    monkeypatch.setattr("ip_work_stats._file_creation_date", dates.__getitem__)

    records = object.__new__(WorkStats)._collect_records(paths)

    assert [record.prefix for record in records] == [
        "pl202604020002", "PL202604020001", "pl202604020003", "pl202604020004", "pl202604030001",
    ]
    assert records[0].title == "普通文件"
    assert records[2].title == "pl2026040200023-超长"
    assert records[3].title == "pl202602300001-无效日期"


@pytest.mark.skipif(os.name != "nt", reason="验证 Windows 文件创建时间")
def test_work_stats_uses_creation_date_even_when_modified_date_differs(tmp_path):
    path = tmp_path / "普通文件.txt"
    path.write_text("测试", encoding="utf-8")
    old_modified = datetime(2000, 1, 1).timestamp()
    os.utime(path, (old_modified, old_modified))
    stat = path.stat()
    created = getattr(stat, "st_birthtime", stat.st_ctime)
    date = datetime.fromtimestamp(created).strftime("%Y%m%d")

    record, = object.__new__(WorkStats)._collect_records([str(path)])

    assert date != "20000101"
    assert record.prefix == f"pl{date}0001"
    assert path.name == "普通文件.txt"


def test_work_stats_reports_missing_creation_date_without_aborting_batch(tmp_path):
    missing = tmp_path / "已移除.txt"
    numbered = tmp_path / "pl202604020001-已有编号.txt"
    numbered.write_text("测试", encoding="utf-8")

    failed, existing = object.__new__(WorkStats)._collect_records([str(missing), str(numbered)])

    assert failed.status == "失败"
    assert not failed.prefix
    assert "无法读取文件创建日期" in failed.message
    assert existing.prefix == "pl202604020001"


def test_work_stats_folder_import_and_two_sheet_export(tmp_path, monkeypatch):
    source = tmp_path / "导入"
    folder = source / "普通目录" / "pl202604020001"
    folder.mkdir(parents=True)
    unnamed = folder / "pl 202604020002 【用户上传的策略申请文件】.xlsx"
    _make_workbook(unnamed)
    named = source / "【用户上传的策略申请文件】pl202604020003 - 测 试\u3000标题.xlsx"
    _make_workbook(named)
    broken = source / "pl202604020004-损坏.xlsx"
    broken.write_text("不是Excel", encoding="utf-8")
    output = tmp_path / "统计.xlsx"

    stats = object.__new__(WorkStats)
    records = stats._collect_records(stats._folder_targets(str(source)))
    attachments = []
    monkeypatch.setattr(stats, "_embed_attachments_as_icons", lambda _, records, rows, progress: attachments.extend(rows))
    stats._save_records(records, str(output), embed_attachments=True)

    by_prefix = {record.prefix: record for record in records}
    assert by_prefix["pl202604020001"].title == "文件夹对象"
    assert by_prefix["pl202604020002"].title == "不明确"
    assert by_prefix["pl202604020003"].title == "测试标题"
    assert unnamed.is_file() and named.is_file()
    assert {record.source_file for _, record in attachments} == {str(unnamed), str(named), str(broken)}
    assert all(records[row - 2] is record for row, record in attachments)

    book = load_workbook(output, data_only=True)
    try:
        assert book.sheetnames == ["工作统计", "失败项目"]
        assert all(sheet.freeze_panes == "A2" for sheet in book)
        result_rows = {row[1]: row for row in book["工作统计"].iter_rows(min_row=2, values_only=True)}
        assert result_rows["pl202604020001"][2:7] == ("文件夹对象", None, None, None, str(folder))
        assert result_rows["pl202604020002"][2] == "不明确"
        assert result_rows["pl202604020003"][2] == "测试标题"
        failure, = list(book["失败项目"].iter_rows(min_row=2, values_only=True))
        assert failure[1:4] == ("pl202604020004", "损坏", str(broken))
        assert failure[4]
    finally:
        book.close()


def test_work_stats_preserves_report_when_excel_attachments_are_unavailable(tmp_path, monkeypatch):
    source = tmp_path / "pl202604020001.txt"
    source.write_text("测试", encoding="utf-8")
    output = tmp_path / "统计.xlsx"
    stats = object.__new__(WorkStats)
    records = stats._collect_records([str(source)])

    def excel_unavailable(*args):
        raise RuntimeError("Excel 不可用")

    monkeypatch.setattr(stats, "_embed_attachments_as_icons", excel_unavailable)
    stats._save_records(records, str(output), embed_attachments=True)

    book = load_workbook(output, data_only=True)
    try:
        assert book["工作统计"]["H2"].value == "失败"
        assert "Excel 不可用" in book["失败项目"]["E2"].value
    finally:
        book.close()


def test_monthly_statistics_reads_and_embeds_one_month_at_a_time(tmp_path, monkeypatch):
    feb = tmp_path / "pl202702010001-二月.xlsx"
    jan = tmp_path / "pl202701010001-一月.xlsx"
    generated = tmp_path / "没有编号.xlsx"
    unreadable_date = tmp_path / "没有日期.xlsx"
    for path in (feb, jan, generated, unreadable_date):
        _make_workbook(path)

    def creation_date(path):
        if path == str(generated):
            return "20270101"
        raise OSError("测试：无法读取创建日期")

    monkeypatch.setattr("ip_work_stats._file_creation_date", creation_date)
    stats = object.__new__(WorkStats)
    events = []
    read = stats._read_excel_applicant_info

    def read_source(path):
        events.append(("read", path))
        return read(path)

    def embed(path, records, rows, progress):
        events.append(("embed", [record.prefix for _, record in rows]))

    monkeypatch.setattr(stats, "_read_excel_applicant_info", read_source)
    monkeypatch.setattr(stats, "_embed_attachments_as_icons", embed)
    existing = tmp_path / "工作统计_pl_2027-01.xlsx"
    existing.write_bytes(b"existing report")
    _, outputs = stats._export_statistics(
        [str(feb), str(jan), str(generated), str(unreadable_date)],
        str(tmp_path / "工作统计.xlsx"), True, True, stat_prefix="pl",
    )

    assert [os.path.basename(path) for path in outputs] == [
        "工作统计_pl_2027-01_2.xlsx", "工作统计_pl_2027-02.xlsx", "工作统计_pl_未归月.xlsx",
    ]
    assert existing.read_bytes() == b"existing report"
    assert events == [
        ("read", str(jan)), ("read", str(generated)), ("embed", ["pl202701010001", "pl202701010002"]),
        ("read", str(feb)), ("embed", ["pl202702010001"]), ("read", str(unreadable_date)),
    ]
    for path, expected in zip(outputs, (["pl202701010001", "pl202701010002"], ["pl202702010001"], [None])):
        book = load_workbook(path, data_only=True)
        try:
            assert [row[1] for row in book.active.iter_rows(min_row=2, values_only=True)] == expected
            assert all(sheet.freeze_panes == "A2" for sheet in book)
            if expected == [None]:
                assert "无法读取文件创建日期" in book["失败项目"]["E2"].value
        finally:
            book.close()


def test_monthly_statistics_stops_before_next_month_if_excel_has_not_exited(tmp_path, monkeypatch):
    paths = [tmp_path / name for name in ("pl202701010001.txt", "pl202702010001.txt")]
    for path in paths:
        path.write_text("测试", encoding="utf-8")
    stats = object.__new__(WorkStats)

    def excel_still_open(*args):
        raise ExcelShutdownError("Excel 尚未退出")

    monkeypatch.setattr(stats, "_embed_attachments_as_icons", excel_still_open)
    with pytest.raises(RuntimeError, match="2027-01未完成：Excel 尚未退出"):
        stats._export_statistics(list(map(str, paths)), str(tmp_path / "工作统计.xlsx"), True, True, stat_prefix="pl")
    assert (tmp_path / "工作统计_pl_2027-01.xlsx").is_file()
    assert not (tmp_path / "工作统计_pl_2027-02.xlsx").exists()


@pytest.mark.parametrize("choice", ["add", "pl", "ts"])
def test_work_stats_exports_only_selected_prefix_and_numbers_untagged_files(tmp_path, monkeypatch, choice):
    paths = {
        prefix: tmp_path / f"{prefix.upper()}202704030001-已有编号.txt"
        for prefix in ("add", "pl", "ts")
    }
    untagged = tmp_path / "普通文件.txt"
    malformed_other = tmp_path / ("ts12-不属于本次.txt" if choice != "ts" else "add12-不属于本次.txt")
    for path in (*paths.values(), untagged, malformed_other):
        path.write_text("测试", encoding="utf-8")

    def creation_date(path):
        assert path == str(untagged)
        return "20270403"

    monkeypatch.setattr("ip_work_stats._file_creation_date", creation_date)
    stats = object.__new__(WorkStats)
    _, (output,) = stats._export_statistics(
        list(map(str, (untagged, *paths.values(), malformed_other))),
        str(tmp_path / "工作统计.xlsx"), False, True, stat_prefix=choice,
    )

    assert os.path.basename(output) == f"工作统计_{choice}_2027-04.xlsx"
    book = load_workbook(output, data_only=True)
    try:
        rows = list(book.active.iter_rows(min_row=2, values_only=True))
        assert [(row[1], row[6]) for row in rows] == [
            (f"{choice}202704030002", str(untagged)),
            (f"{choice.upper()}202704030001", str(paths[choice])),
        ]
    finally:
        book.close()


def test_anonymizer_work_stats_input_includes_failed_original_files(tmp_path):
    source_file = tmp_path / "pl202601063001-失败原文件.xlsx"
    output_file = tmp_path / "pl202601063002-成功输出.xlsx"
    _make_workbook(source_file)
    _make_workbook(output_file)

    results = [
        ProcessingResult(
            file_path=str(source_file),
            status="error",
            original_size=1,
            processed_size=0,
            ip_count=0,
            error_message="测试失败",
        ),
        ProcessingResult(
            file_path=str(source_file),
            status="success",
            original_size=1,
            processed_size=1,
            ip_count=1,
            output_path=str(output_file),
        ),
    ]

    anonymizer = object.__new__(IPAnonymizer)

    assert IPAnonymizer._get_work_stats_input_files(anonymizer, results) == [
        str(source_file),
        str(output_file),
    ]


def test_work_stats_includes_txt_and_word_without_applicant_lookup(tmp_path):
    txt_file = tmp_path / "add202601063003-文本申请.txt"
    docx_file = tmp_path / "pl202601063004-Word申请.docx"
    ignored_file = tmp_path / "pl202601063005-忽略.pdf"
    txt_file.write_text("服务器 192.168.1.1", encoding="utf-8")
    docx_file.write_text("placeholder", encoding="utf-8")
    ignored_file.write_text("placeholder", encoding="utf-8")

    work_stats = object.__new__(WorkStats)

    assert WorkStats._is_supported_file(work_stats, str(txt_file))
    assert WorkStats._is_supported_file(work_stats, str(docx_file))
    assert not WorkStats._is_supported_file(work_stats, str(ignored_file))

    txt_record = WorkStats._read_record(work_stats, 1, str(txt_file))
    docx_record = WorkStats._read_record(work_stats, 2, str(docx_file))

    assert txt_record.status == "成功"
    assert txt_record.applicant_unit == ""
    assert txt_record.applicant == ""
    assert "不读取组织和联系人" in txt_record.message
    assert docx_record.status == "成功"
    assert docx_record.applicant_unit == ""
    assert docx_record.applicant == ""
    assert "不读取组织和联系人" in docx_record.message


def test_processing_stats_uses_instance_unprocessed_file_lists():
    assert ProcessingStats().unprocessed_files is not ProcessingStats().unprocessed_files


def test_file_processor_validates_binary_file_access_and_docx_output_path(tmp_path):
    from docx import Document

    docx_file = tmp_path / "source.docx"
    output_file = tmp_path / "output.docx"
    document = Document()
    document.add_paragraph("服务器地址 192.168.1.1")
    document.save(docx_file)

    processor = FileProcessor(partial_anonymize=True)

    assert processor.validate_file_access(str(docx_file))

    result = processor.process_docx_file(str(docx_file), str(output_file))

    assert result.status == "success"
    assert result.output_path == str(output_file)
    assert output_file.exists()


def test_docx_anonymization_preserves_run_formatting(tmp_path):
    from docx import Document

    docx_file = tmp_path / "formatted.docx"
    output_file = tmp_path / "formatted_output.docx"
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("服务器 ")
    ip_run = paragraph.add_run("192.168.1.1")
    ip_run.bold = True
    paragraph.add_run(" 结束")
    document.save(docx_file)

    processor = FileProcessor(partial_anonymize=True)
    result = processor.process_docx_file(str(docx_file), str(output_file))

    assert result.status == "success"

    output_doc = Document(output_file)
    output_paragraph = output_doc.paragraphs[0]

    assert output_paragraph.runs[0].text == "服务器 "
    assert output_paragraph.runs[1].text == "192.x.x.x"
    assert output_paragraph.runs[1].bold is True
    assert output_paragraph.runs[2].text == " 结束"
