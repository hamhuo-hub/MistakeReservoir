from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uvicorn
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from extractor import QuestionExtractor
from database import DatabaseManager

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clean temp dir
    temp_dir = os.path.join(MEDIA_DIR, "temp")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            print("Cleaned media/temp directory.")
        except Exception as e:
            print(f"Failed to clean temp dir: {e}")
    else:
        os.makedirs(temp_dir)
    
    yield
    # Shutdown logic if any

app = FastAPI(lifespan=lifespan)

# ... imports
# Config
import sys

if getattr(sys, 'frozen', False):
    # Running as compiled exe
    # ASSET_DIR: Temporary folder where PyInstaller extracts code/static (Bundle)
    ASSET_DIR = sys._MEIPASS
    # DATA_DIR: Directory where the executable/script resides (User Data)
    DATA_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    ASSET_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = ASSET_DIR

# Mutable User Data (External)
MEDIA_DIR = os.path.join(DATA_DIR, "media")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
if not os.path.exists(MEDIA_DIR): os.makedirs(MEDIA_DIR)

# Init Components
db = DatabaseManager(os.path.join(DATA_DIR, "reservoir.db"))
extractor = QuestionExtractor(MEDIA_DIR)


# ... existing imports ...

class GenerateRequest(BaseModel):
    total_count: int
    types: List[str] = [] # e.g. ["常识", "言语"]

@app.post("/generate")
def generate_paper(req: GenerateRequest):
    # Fetch Questions
    if req.types:
        questions = db.get_random_questions(req.total_count, req.types)
    else:
        # User didn't specify types -> Use Standard Exam Distribution
        questions = db.get_standard_exam_questions(req.total_count)
    
    if not questions:
        raise HTTPException(status_code=400, detail="No questions available in pool")
        
    # Generate DOCX
    from generator import PaperBuilder
    builder = PaperBuilder(MEDIA_DIR)
    
    filename = f"MistakePaper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    output_path = os.path.join(UPLOAD_DIR, filename)
    
    builder.create_paper(questions, output_path)
    
    # Return download URL or File directly?
    # Using JSON with URL is better for fetch handling
    return {"download_url": f"/download/{filename}", "count": len(questions)}

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return HTTPException(404, "File not found")

# Mount Static
app.mount("/static", StaticFiles(directory=os.path.join(ASSET_DIR, "static")), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Models
class AnalyzeRequest(BaseModel):
    filename: str

class ExtractRequest(BaseModel):
    filename: str
    ranges: Optional[str] = None
    ids: Optional[List[int]] = None

class SaveRequest(BaseModel):
    source_filename: str
    questions: List[dict]



class UpdateRequest(BaseModel):
    id: int
    content_html: str
    options_html: str
    answer_html: str

@app.post("/api/question/update")
def update_question(req: UpdateRequest):
    try:
        db.update_question_text(req.id, req.content_html, req.options_html, req.answer_html)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/question/{qid}")
def delete_question(qid: int):
    try:
        # Get Question Info first to find images
        # We need a db method for single question or search
        # Since db.get_all_questions is heavy, let's just use it or add a fetcher.
        # But for now, let's look at get_all_questions usage.
        # Actually, let's implement a direct fetch in the endpoint using raw cursor for efficiency or add to DB.
        # For simplicity/speed without changing DB schema, we can query.
        
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT images FROM questions WHERE id=?", (qid,))
        row = c.fetchone()
        images_to_delete = []
        if row and row[0]:
            try:
                images_to_delete = json.loads(row[0])
            except: pass
        conn.close()

        # Delete FileSystem Images
        for img in images_to_delete:
            p = os.path.join(MEDIA_DIR, img)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as ex:
                    print(f"Failed to delete {p}: {ex}")

        # Delete DB Record
        db.delete_question(qid)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return FileResponse(os.path.join(ASSET_DIR, "static/index.html"))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}

def parse_ranges(range_str: str) -> List[int]:
    if not range_str: return []
    ids = set()
    parts = range_str.split(',')
    for p in parts:
        p = p.strip()
        if not p: continue
        if '-' in p:
            try:
                start, end = map(int, p.split('-'))
                for i in range(start, end + 1):
                    ids.add(i)
            except: pass
        else:
            try:
                ids.add(int(p))
            except: pass
    return sorted(list(ids))

@app.post("/analyze_file")
def analyze_file(req: AnalyzeRequest):
    file_path = os.path.join(UPLOAD_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Extract ALL to get metadata
        # Optimization: We could have a lighter extractor method, but this is fine for now
        questions = extractor.extract_from_file(file_path, target_ids=None, skip_images=True)
        
        # Return lightweight metadata
        meta_list = [
            {"num": q['original_num'], "type": q['type']} 
            for q in questions
        ]
        return {"count": len(meta_list), "questions": meta_list}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract_preview")
def extract_preview(req: ExtractRequest):
    file_path = os.path.join(UPLOAD_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    target_ids = []
    if req.ids:
        target_ids = req.ids
    elif req.ranges:
        target_ids = parse_ranges(req.ranges)
    
    try:
        # Use temp dir for preview images to prevent zombie files
        questions = extractor.extract_from_file(file_path, target_ids if target_ids else None, sub_dir="temp")
        
        if (req.ids is not None) and len(req.ids) == 0:
             questions = []
             
        return {"count": len(questions), "questions": questions}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/confirm_save")
def confirm_save(req: SaveRequest):
    # 1. Add Source
    sid = db.add_source(req.source_filename)
    
    # 2. Add Questions & Materials
    material_map = {} # content_hash -> mid
    
    # Helper to move file if exists
    def move_from_temp(filename):
        src = os.path.join(MEDIA_DIR, "temp", filename)
        dst = os.path.join(MEDIA_DIR, filename)
        if os.path.join(MEDIA_DIR, "temp") in src and os.path.exists(src): # basic safety
            try:
                shutil.move(src, dst)
            except Exception as e:
                print(f"Error moving {filename}: {e}")

    # Helper to fix HTML
    def fix_html_paths(html):
        if not html: return html
        return html.replace("/media/temp/", "/media/")

    count = 0
    for q in req.questions:
        # 1. Move physical files based on the authoritative 'images' list
        if q.get('images'):
            for img in q['images']:
                # img is just filename (uuid.png)
                move_from_temp(img)
        
        # 2. Update HTML content strings (Simple replacement is safer/faster than regex)
        q['content_html'] = fix_html_paths(q['content_html'])
        q['options_html'] = fix_html_paths(q['options_html'])
        q['answer_html'] = fix_html_paths(q['answer_html'])

        # Material handling
        mid = None
        mat_content = q.get('material_content')
        if mat_content:
            # Process material images too!
            # We don't have a separate images list for material easily accessible here
            # without parsing. But usually material images appear in questions list too?
            # Actually Extractor might not put material images in q['images']?
            # Let's check Extractor.
            # Extractor: images = stem + opt + ana. Material not included.
            # So we rely on regex/parsing for material images? 
            # OR we try to find them.
            # For now, let's use the REPLACE logic. Main issue is physical file move.
            # If we don't know the filename, we can't move it unless we parse HTML.
            
            # Fallback: Parse material HTML for /media/temp/ filenames
            import re
            mat_temp_imgs = re.findall(r'/media/temp/([\w\-\.]+\.\w+)', mat_content)
            for img in mat_temp_imgs:
                move_from_temp(img)
            
            mat_content = fix_html_paths(mat_content)
            
            mat_hash = hash(mat_content)
            if mat_hash in material_map:
                mid = material_map[mat_hash]
            else:
                mid = db.add_material(sid, mat_content, type=q['type'])
                material_map[mat_hash] = mid
        
        db.add_question(
            source_id=sid,
            original_num=q['original_num'],
            content=q['content_html'],
            options=q['options_html'],
            answer=q['answer_html'], 
            images=q['images'],
            type=q['type'],
            material_id=mid
        )
        count += 1
        
    return {"status": "success", "saved_count": count}



@app.get("/pool_status")
def pool_status():
    return db.get_pool_status()


@app.get("/api/questions")
def get_all_questions():
    questions = db.get_all_questions()
    return {"count": len(questions), "questions": questions}

@app.get("/browse")
def browse_page():
    return FileResponse(os.path.join(ASSET_DIR, "static/browse.html"))

# To run: uvicorn main:app --reload
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)