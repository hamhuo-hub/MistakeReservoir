
from docx import Document
import re

def inspect_q107():
    docx_path = r"c:\potorable\StudentSphere\MistakeReservoir\uploads\行测组卷8-解析.docx"
    doc = Document(docx_path)
    
    found_107 = False
    print_count = 0
    
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text: continue
        
        # Look for start of 107
        if "107" in text and (text.startswith("107") or text.startswith("(107")):
            found_107 = True
            print(f"--- FOUND START OF 107: {text} ---")
            
        if found_107:
            print(f"Line: {repr(text)}")
            print_count += 1
            
            # Stop after a reasonable amount of lines to see the answer part
            if "【解析】" in text or "【答案】" in text:
                print("--- FOUND ANALYSIS/ANSWER ---")
                if print_count > 10: # Print a bit more to be sure
                    break
            
            if print_count > 20: # Safety break
                break

if __name__ == "__main__":
    try:
        inspect_q107()
    except Exception as e:
        print(f"Error: {e}")
