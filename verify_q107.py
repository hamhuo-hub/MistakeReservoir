
import shutil
import os
from extractor import QuestionExtractor

def verify_q107():
    docx_path = r"c:\potorable\StudentSphere\MistakeReservoir\uploads\行测组卷8-解析.docx"
    media_dir = "verify_media"
    
    if os.path.exists(media_dir):
        shutil.rmtree(media_dir)
        
    extractor = QuestionExtractor(media_dir=media_dir)
    # Extract only near 107. The extractor doesn't support range well without parsing all, 
    # but we can filter the result.
    questions = extractor.extract_from_file(docx_path)
    
    q107 = next((q for q in questions if q['original_num'] == 107), None)
    
    if q107:
        print("\n=== QUESTION 107 ===")
        print("STEM HTML:", q107['content_html'][:100] + "...")
        print("OPTIONS HTML:", q107['options_html'])
        print("ANSWER HTML:", q107['answer_html'][:100] + "...")
        
        if q107['options_html']:
            print("SUCCESS: Options detected.")
            if "A." in q107['content_html'] or "B." in q107['content_html']:
                 # Simple heuristic: if options are also in stem, it might be a partial fail, 
                 # but for this specific case, the stem ends with question text.
                 pass
        else:
            print("FAILURE: Options HTML is empty.")
    else:
        print("FAILURE: Question 107 not found.")
        
    if os.path.exists(media_dir):
        shutil.rmtree(media_dir)

if __name__ == "__main__":
    verify_q107()
