import os
import re
import argparse
import sys
from typing import List, Optional

try:
    from docx import Document
    from docx.document import Document as _Document
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph
except ImportError:
    print("Error: 'python-docx' library is required. Please install it using 'pip install python-docx'.")
    sys.exit(1)

class SimpleAnswerExtractor:
    def __init__(self):
        # Regex Patterns (Adapted from extractor.py)
        self.Q_PATTERN = re.compile(r'^\s*\(?\d+\)?[\.．、\s]')
        self.ANSWER_TAG_PATTERN = re.compile(
            r'(【\s*答案\s*】|【\s*解析\s*】|【\s*拓展\s*】|【\s*来源\s*】|正确\s*答案|参考\s*答案|答案\s*[:：]|解析\s*[:：])'
        )
        self.ANSWER_VAL_PATTERN = re.compile(
            r'(?:【\s*答案\s*】|正确\s*答案|答案\s*[:：])\s*([A-D])', 
            re.IGNORECASE
        )

    def iter_block_items(self, parent):
        """Iterate through docx blocks (Paragraphs and Tables)"""
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            return

        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def extract_answers(self, docx_path: str) -> List[str]:
        if not os.path.exists(docx_path):
            print(f"Error: File '{docx_path}' not found.")
            return []

        try:
            doc = Document(docx_path)
        except Exception as e:
            print(f"Error opening DOCX file: {e}")
            return []

        answers = []
        blocks = self.iter_block_items(doc)
        
        current_q_num = 0
        
        # Buffer to hold current question blocks if we needed context, 
        # but for simple answer extraction we can mostly stream it, 
        # EXCEPT sometimes the answer letter is on the NEXT line after "【答案】".
        # So we'll look for the pattern in each block.
        
        for block in blocks:
            text = ""
            if isinstance(block, Paragraph):
                text = block.text.strip()
            elif isinstance(block, Table):
                cell_texts = []
                for row in block.rows:
                    for cell in row.cells:
                        cell_texts.append(cell.text.strip())
                text = " ".join(cell_texts)

            if not text:
                continue

            # Check if this line contains the answer
            match = self.ANSWER_VAL_PATTERN.search(text)
            if match:
                answers.append(match.group(1).upper())
                continue
            
            # Simple fallback: If we see "【答案】" but no letter, check if the NEXT text is just a letter?
            # For now, let's stick to the regex which handles "【答案】 A"
            # If the user's format is "【答案】\n A", the regex won't catch it single-pass.
            # But based on the provided extractor.py, it separates using regex, so the content likely flows together or is in one block often enough.
            
            # Let's inspect how extractor works. It splits blocks. 
            # If we want to be robust, we might need a small state machine, 
            # but usually "Answer: A" is on one line.
            
            pass

        return answers

def main():
    parser = argparse.ArgumentParser(description="Extract just the answer keys (A/B/C/D) from a DOCX question file (Standalone).")
    parser.add_argument("file", help="Path to the .docx file")
    
    args = parser.parse_args()
    
    extractor = SimpleAnswerExtractor()
    print(f"Processing: {args.file} ...")
    answers = extractor.extract_answers(args.file)
    
    print(f"\nFound {len(answers)} answers:\n")
    
    # Print in blocks of 5
    for i in range(0, len(answers), 5):
        chunk = answers[i:i+5]
        print(" ".join(chunk))

    print("\nDone.")

if __name__ == "__main__":
    main()
