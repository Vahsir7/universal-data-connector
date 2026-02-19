import csv
from io import BytesIO, StringIO
from typing import Any, Dict, List, Tuple

from openpyxl import Workbook


def _collect_columns(rows: List[Dict[str, Any]]) -> List[str]:
    columns: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in columns:
                columns.append(key)
    return columns


def to_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    output = StringIO()
    columns = _collect_columns(rows)
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in columns})
    return output.getvalue().encode("utf-8")


def to_excel_bytes(rows: List[Dict[str, Any]], sheet_name: str = "Data") -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name[:31] if sheet_name else "Data"

    columns = _collect_columns(rows)
    worksheet.append(columns)
    for row in rows:
        worksheet.append([row.get(key) for key in columns])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_export(filename_base: str, export_format: str, rows: List[Dict[str, Any]]) -> Tuple[str, str, bytes]:
    if export_format == "xlsx":
        payload = to_excel_bytes(rows, sheet_name=filename_base)
        return (
            f"{filename_base}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            payload,
        )

    payload = to_csv_bytes(rows)
    return (f"{filename_base}.csv", "text/csv; charset=utf-8", payload)
