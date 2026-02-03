
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
import re

def iter_block_items(parent):
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

def inspect_q107():
    docx_path = r"c:\potorable\StudentSphere\MistakeReservoir\uploads\行测组卷8-解析.docx"
    doc = Document(docx_path)
    
    # Regex from extractor.py
    Q_PATTERN = re.compile(r'^\s*\(?\d+\)?[\.．、\s]')
    OPTION_PATTERN = re.compile(r'^\s*\(?[A-D]\)?[\.．、\s]')
    
    found_107 = False
    count = 0
    
    for block in iter_block_items(doc):
        text = ""
        if isinstance(block, Paragraph):
            text = block.text.strip()
        elif isinstance(block, Table):
            cell_texts = []
            for row in block.rows:
                for cell in row.cells:
                    cell_texts.append(cell.text.strip())
            text = " ".join(cell_texts)
            text = f"[TABLE] {text}"

        if not text: continue
        
        # Check start
        if "107" in text and (text.startswith("107") or text.startswith("(107")):
            found_107 = True
            print(f"\n=== FOUND 107 ===")
            
        if found_107:
            print(f"\nText: {repr(text)}")
            hex_dump = [hex(ord(c)) for c in text[:10]]
            print(f"Hex start: {hex_dump}")
            
            q_match = Q_PATTERN.match(text)
            opt_match = OPTION_PATTERN.match(text)
            
            print(f"Q_PATTERN match: {bool(q_match)}")
            print(f"OPT_PATTERN match: {bool(opt_match)}")
            
            if opt_match:
                print(">>> IDENTIFIED AS OPTION")
            elif q_match:
                print(">>> IDENTIFIED AS QUESTION START")
            else:
                print(">>> IDENTIFIED AS STEM/OTHER")

            count += 1
            if count > 15:
                break

if __name__ == "__main__":
    inspect_q107()
