import io
import zipfile

import pytest

from app.services.roster_import import parse_roster


def test_parse_csv_roster_headers_and_rows():
    rows = parse_roster("roster.csv", b"Student ID,Full Name,Email,Phone\nS001,Ada Example,ada@example.edu,12345\n")
    assert rows == [{
        "roll_number": "S001", "full_name": "Ada Example",
        "email": "ada@example.edu", "phone_number": "12345", "_line": 2,
    }]


def test_parse_docx_table_without_external_docx_runtime():
    document = b'''<?xml version="1.0" encoding="UTF-8"?>
      <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body><w:tbl>
          <w:tr><w:tc><w:p><w:r><w:t>Roll Number</w:t></w:r></w:p></w:tc>
          <w:tc><w:p><w:r><w:t>Full Name</w:t></w:r></w:p></w:tc>
          <w:tc><w:p><w:r><w:t>Email</w:t></w:r></w:p></w:tc></w:tr>
          <w:tr><w:tc><w:p><w:r><w:t>R1</w:t></w:r></w:p></w:tc>
          <w:tc><w:p><w:r><w:t>Lin Example</w:t></w:r></w:p></w:tc>
          <w:tc><w:p><w:r><w:t>lin@example.edu</w:t></w:r></w:p></w:tc></w:tr>
        </w:tbl></w:body></w:document>'''
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("word/document.xml", document)
    rows = parse_roster("roster.docx", stream.getvalue())
    assert rows[0]["roll_number"] == "R1"
    assert rows[0]["full_name"] == "Lin Example"
    assert rows[0]["email"] == "lin@example.edu"


@pytest.mark.parametrize("filename,data", [
    ("roster.xlsx", b"not supported"),
    ("empty.csv", b""),
    ("bad.docx", b"not a zip"),
])
def test_roster_parser_reports_unsupported_or_invalid_files(filename, data):
    with pytest.raises(ValueError):
        parse_roster(filename, data)
