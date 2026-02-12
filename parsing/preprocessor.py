import re
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

# Regex Patterns
Q_PATTERN = re.compile(r'^\s*\(?\d+\)?[\.．、\s]')
HEADER_PATTERN = re.compile(
    r'^\s*第[一二三四五六七八九十]+部分|'
    r'^\s*[一二三四五六七八九十]+、|'
    r'^\s*(根据|阅读).*(材料|回答|短文)'
)

# Ignore Pattern (e.g. （共20题，参考时限10分钟）)
IGNORE_PATTERN = re.compile(r'^\s*[\(（]共\d+题[，,]\s*参考时限\d+分钟[\)）]')

def iter_block_items(parent):
    """Iterate through docx blocks (Paragraphs and Tables)"""
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Parent object error")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)
