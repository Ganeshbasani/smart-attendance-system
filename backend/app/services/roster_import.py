"""In-memory roster table extraction for CSV, DOCX, and text-based PDF files."""

import csv
import io
import re
import zipfile
from xml.etree import ElementTree


FIELD_ALIASES = {
    "roll_number": {"roll", "rollno", "rollnumber", "studentid", "id", "employeeid", "staffid"},
    "full_name": {"name", "fullname", "studentname", "employeename", "staffname"},
    "email": {"email", "emailaddress", "mail"},
    "phone_number": {"phone", "phonenumber", "mobile", "contact"},
}


def _canonical(value: str) -> str:
    token = re.sub(r"[^a-z0-9]", "", (value or "").lower())
    for field, aliases in FIELD_ALIASES.items():
        if token in aliases:
            return field
    return ""


def _rows_from_table(rows: list[list[str]]) -> list[dict]:
    if len(rows) < 2:
        raise ValueError("The document must have a header row and at least one student row")
    headers = [_canonical(cell) for cell in rows[0]]
    if "roll_number" not in headers or "full_name" not in headers or "email" not in headers:
        raise ValueError("Include columns for Student ID/Roll Number, Full Name, and Email")
    output = []
    for line_number, cells in enumerate(rows[1:], start=2):
        if not any((cell or "").strip() for cell in cells):
            continue
        row = {field: "" for field in FIELD_ALIASES}
        for index, header in enumerate(headers):
            if header and index < len(cells):
                row[header] = (cells[index] or "").strip()
        row["_line"] = line_number
        output.append(row)
    return output


def _parse_csv(data: bytes) -> list[dict]:
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be encoded as UTF-8") from exc
    try:
        return _rows_from_table(list(csv.reader(io.StringIO(decoded))))
    except csv.Error as exc:
        raise ValueError("Could not read the CSV table") from exc


def _parse_docx(data: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            document = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise ValueError("Could not read the Word document") from exc
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    tables = document.findall(".//w:tbl", namespace)
    if not tables:
        raise ValueError("The Word document needs a roster table with column headings")
    rows = []
    for row in tables[0].findall("w:tr", namespace):
        cells = []
        for cell in row.findall("w:tc", namespace):
            cells.append(" ".join(node.text or "" for node in cell.findall(".//w:t", namespace)).strip())
        rows.append(cells)
    return _rows_from_table(rows)


def _parse_pdf(data: bytes) -> list[dict]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=False)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError("Could not read the PDF roster") from exc
    if not text.strip():
        raise ValueError("This PDF has no selectable text. Export a text-based PDF or upload DOCX/CSV.")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_index = next((i for i, line in enumerate(lines)
                         if _canonicalized_header(line)), None)
    if header_index is None:
        raise ValueError("Could not identify the roster header. Include Roll Number, Full Name, and Email columns.")
    separator = re.compile(r"\t+|\s{2,}|\s*\|\s*|\s*,\s*|\s*;\s*")
    table = [separator.split(lines[header_index])]
    for line in lines[header_index + 1:]:
        cells = separator.split(line)
        if len(cells) >= len(table[0]):
            table.append(cells)
    return _rows_from_table(table)


def _canonicalized_header(line: str) -> bool:
    cells = re.split(r"\t+|\s{2,}|\s*\|\s*|\s*,\s*|\s*;\s*", line.strip())
    fields = {_canonical(cell) for cell in cells}
    return {"roll_number", "full_name", "email"}.issubset(fields)


def parse_roster(filename: str, data: bytes) -> list[dict]:
    """Extract rows; caller validates the values and confirms before writing."""
    if not data:
        raise ValueError("Uploaded roster is empty")
    extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if extension == "csv":
        rows = _parse_csv(data)
    elif extension == "docx":
        rows = _parse_docx(data)
    elif extension == "pdf":
        rows = _parse_pdf(data)
    else:
        raise ValueError("Supported roster files are PDF, DOCX, and CSV")
    if not rows:
        raise ValueError("The roster contains no student rows")
    if len(rows) > 500:
        raise ValueError("Import at most 500 students per upload")
    return rows
