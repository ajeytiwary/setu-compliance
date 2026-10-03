"""Synthetic tests for PP-StructureV3 markdown post-processing.

paddlex emits tables as raw HTML inside its "markdown" result (with
<html>/<body>/<div> wrappers) and can fall back to structure-only HTML with
empty <td></td> cells when cell OCR fails. app.document_ingest.
html_tables_to_markdown must turn those into real pipe tables with populated
cells, and drop tables that carry no text. Pure-CPU, no paddle import.
"""
from app.document_ingest import html_tables_to_markdown


def test_plain_text_untouched():
    text = "### Heading\nSome paragraph text with CN 84818081.\n"
    assert html_tables_to_markdown(text) == text


def test_empty_string_passthrough():
    assert html_tables_to_markdown("") == ""
    assert html_tables_to_markdown(None) == ""


def test_populated_table_becomes_pipe_table():
    md = (
        "before\n"
        '<div style="text-align: center;">\n'
        '<html><body><table border="1"><tr>'
        "<td>Heat No.</td><td>Chem (%)</td>"
        "</tr><tr><td>H-1234</td><td>C 0.08</td></tr>"
        "</table></body></html></div>\n"
        "after"
    )
    out = html_tables_to_markdown(md)
    assert "<table" not in out and "<div" not in out
    assert "<html" not in out and "</body>" not in out
    assert "| Heat No. | Chem (%) |" in out
    assert "| --- | --- |" in out
    assert "| H-1234 | C 0.08 |" in out
    assert "before" in out and "after" in out


def test_empty_table_dropped():
    md = (
        "text before\n"
        "<table border=\"1\"><tr><td></td><td></td></tr>"
        "<tr><td> </td><td></td></tr></table>\n"
        "text after"
    )
    out = html_tables_to_markdown(md)
    assert "<table" not in out and "<td" not in out
    assert "text before" in out and "text after" in out
    # no pipe row leaked from the empty shell
    assert "|" not in out


def test_structure_only_token_soup_dropped():
    # upstream fallback: structure tokens space-joined around empty cells
    md = "<html><body><table><tr><td></td><td></td></tr></table></body></html>"
    out = html_tables_to_markdown(md)
    assert out.strip() == ""


def test_colspan_rowspan_grid():
    md = (
        "<table>"
        "<tr><td rowspan=\"2\">Item</td><td colspan=\"2\">Spec</td></tr>"
        "<tr><td>A</td><td>B</td></tr>"
        "<tr><td>X</td><td>1</td><td>2</td></tr>"
        "</table>"
    )
    out = html_tables_to_markdown(md)
    lines = [ln for ln in out.strip().splitlines() if ln.startswith("|")]
    # header: Item | Spec | (empty filler for colspan expansion)
    assert lines[0] == "| Item | Spec |  |"
    # rowspan carry keeps Item in the row after the separator
    assert lines[2] == "| Item | A | B |"
    assert lines[3] == "| X | 1 | 2 |"


def test_pipe_in_cell_escaped():
    md = "<table><tr><td>a|b</td><td>c</td></tr></table>"
    out = html_tables_to_markdown(md)
    assert "a\\|b" in out
    row = next(ln for ln in out.splitlines() if "a\\|b" in ln)
    # renders as two cells: first contains a|b (escaped), second c
    assert row == "| a\\|b | c |"


def test_br_becomes_space_in_cell():
    md = "<table><tr><td>line1<br/>line2</td></tr></table>"
    out = html_tables_to_markdown(md)
    assert "| line1 line2 |" in out


def test_multiple_tables_all_converted():
    md = (
        "<table><tr><td>t1</td></tr></table>\n"
        "middle\n"
        "<table><tr><td>t2</td></tr></table>"
    )
    out = html_tables_to_markdown(md)
    assert "<table" not in out
    assert "| t1 |" in out and "| t2 |" in out
    assert "middle" in out


def test_th_header_row():
    md = "<table><tr><th>Col1</th><th>Col2</th></tr><tr><td>1</td><td>2</td></tr></table>"
    out = html_tables_to_markdown(md)
    assert "| Col1 | Col2 |" in out
    assert "| 1 | 2 |" in out


def test_newline_in_cell_collapsed():
    md = "<table><tr><td>multi\nline cell</td></tr></table>"
    out = html_tables_to_markdown(md)
    assert "| multi line cell |" in out


def test_leading_empty_row_not_used_as_header():
    md = (
        "<table>"
        "<tr><td></td><td></td></tr>"
        "<tr><td>Heat No.</td><td>Qty</td></tr>"
        "<tr><td></td><td></td></tr>"
        "<tr><td>H-1</td><td>12</td></tr>"
        "</table>"
    )
    out = html_tables_to_markdown(md)
    lines = [ln for ln in out.strip().splitlines() if ln.startswith("|")]
    assert lines[0] == "| Heat No. | Qty |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| H-1 | 12 |"
    assert len(lines) == 3  # both empty rows dropped


def test_idempotent_on_already_markdown():
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    assert html_tables_to_markdown(md) == md
