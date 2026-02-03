
from docx import Document
import re

def inspect_v3():
    docx_path = r"c:\potorable\StudentSphere\MistakeReservoir\uploads\行测组卷8-解析.docx"
    doc = Document(docx_path)
    
    OPTION_PATTERN = re.compile(r'^\s*\(?[A-D]\)?[\.．、\s]')
    
    found_107 = False
    
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        if not text: continue
        
        # Helper to find 107
        if "107" in text and (text.startswith("107") or text.startswith("(107")):
            found_107 = True
            print(f"--- FOUND 107 at index {i} ---")
            
        if found_107:
            # Look for the option line
            if "A." in text or "A．" in text or text.startswith("A"):
                print(f"\n--- POTENTIAL OPTION LINE at index {i} ---")
                print(f"Text: {repr(text)}")
                
                # Check first 5 chars hex
                hex_dump = [hex(ord(c)) for c in text[:5]]
                print(f"Hex start: {hex_dump}")
                
                match = OPTION_PATTERN.match(text)
                print(f"Match OPTION_PATTERN: {bool(match)}")
                
                # If "B." is also in line, checking that too
                if "B." in text:
                    print(f"Contains 'B.': True")
                
                # Only need the first one
                break
                
            # Stop if we went too far
            if "108" in text and text.startswith("108"):
                print("Reached 108 without finding options.")
                break

if __name__ == "__main__":
    inspect_v3()
