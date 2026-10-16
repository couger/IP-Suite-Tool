"""Table layout contracts independent of company, site, or worksheet names."""
import re

import openpyxl


APPLICATION_COLUMNS = (
    "记录编号", "位置", "资源标识", "业务类别", "IPv4地址", "IPv6地址",
    "网关", "掩码", "组织", "联系人",
)
PLAN_COLUMNS = (
    "位置", "IPv4网段", "IPv6网段", "用途",
)

# Only individual, common import aliases are retained, not a customer template.
COLUMN_ALIASES = {
    "记录编号": ("申请单号",),
    "位置": ("站点",),
    "资源标识": ("设备点位",),
    "业务类别": ("所属业务",),
    "IPv4地址": ("IPv4地址（按需）",),
    "IPv6地址": ("IPv6地址（默认分配）",),
    "网关": ("IPv6/IPv4网关",),
    "掩码": ("IPv6/IPv4掩码",),
    "组织": ("申请单位",),
    "联系人": ("申请人",),
}


def header_key(value):
    return re.sub(r"[\s*＊]+", "", str(value)).replace("（", "(").replace("）", ")")


def canonical_column(value):
    name = str(value).strip()
    return next((col for col in APPLICATION_COLUMNS
                 if header_key(name) in {header_key(value) for value in (col, *COLUMN_ALIASES.get(col, ()))}), name)


def read_display_table(path):
    """Use the first sheet and first row; keep caller-facing header labels intact."""
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = iter(sheet.iter_rows(values_only=True))
        header = next(rows, ())
        indexed = [(i, str(value).strip()) for i, value in enumerate(header) if value is not None and str(value).strip()]
        columns = [name for _, name in indexed]
        if not columns:
            raise ValueError("首行未找到列标题")
        if len(set(columns)) != len(columns):
            raise ValueError("列标题重复，请为每列使用不同名称")
        records = []
        for row in rows:
            if not any(value not in (None, "") for value in row):
                continue
            records.append([str(row[i]) if i < len(row) and row[i] is not None else "" for i, _ in indexed])
        return columns, records
    finally:
        workbook.close()
