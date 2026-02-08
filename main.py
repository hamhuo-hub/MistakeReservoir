from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uvicorn
from datetime import datetime
from typing import List, Optional, Dict
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
import threading
import time
import webbrowser

# ... imports
# Config
import sys

# Heartbeat Monitor
# Last heartbeat time
last_heartbeat = time.time()

@app.post("/api/heartbeat")
def heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()
    return {"status": "ok"}

def monitor_heartbeat():
    global last_heartbeat
    print("Heartbeat monitor started...")
    while True:
        time.sleep(1)
        # If no heartbeat for > 3 seconds, exit
        if time.time() - last_heartbeat > 15:
            print("No heartbeat detected. Shutting down...")
            os._exit(0)

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
async def generate_paper(req: GenerateRequest):
    # 1. Get Questions
    if not req.types:
        questions = db.get_standard_exam_questions()
    else:
        questions = db.get_random_questions(req.types, req.total_count)
    
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found matching criteria")

    # 2. Generate UUID & Record
    import uuid
    paper_uuid = str(uuid.uuid4())
    qids = [q['id'] for q in questions]
    db.record_generated_paper(paper_uuid, qids)

    # 3. Generate Doc
    from generator import PaperBuilder
    generator = PaperBuilder(MEDIA_DIR) # Assuming generator is an instance of PaperBuilder
    filename = f"Paper_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    output_path = os.path.join("temp", filename)
    os.makedirs("temp", exist_ok=True)
    
    # Process images for docx
    # (Existing logic to make absolute paths)
    for q in questions:
        # Material Images
        if q.get('material_images'):
            try:
                m_imgs = json.loads(q['material_images'])
                # Prepend media_dir
                q['material_images_abs'] = [os.path.join(MEDIA_DIR, img) for img in m_imgs]
            except: pass
            
        if q.get('images'):
            try:
                imgs = json.loads(q['images'])
                q['images_abs'] = [os.path.join(MEDIA_DIR, img) for img in imgs]
            except: pass

    generator.create_paper(questions, output_path, paper_uuid=paper_uuid)
    
    return FileResponse(output_path, filename=filename)
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
    all_questions_meta: List[dict] # {num, type} for stats calculation

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

@app.get("/api/exam_stats")
def get_exam_stats():
    try:
        stats = db.get_exam_stats()
        return {"count": len(stats), "stats": stats}
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

    # --- 1. Detect Paper ID (Review Mode) ---
    paper_uuid = None
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(file_path)
        if len(doc.paragraphs) > 0:
            first_para = doc.paragraphs[0].text.strip()
            if first_para.startswith("Paper ID: "):
                paper_uuid = first_para.replace("Paper ID: ", "").strip()
    except Exception as e:
        print(f"Error checking Paper ID: {e}")
        # Continue to standard extraction if fails (might be PDF or other format)

    if paper_uuid:
        # --- REVIEW MODE ---
        try:
            qids = db.get_generated_paper_qids(paper_uuid)
            if not qids:
                 return JSONResponse(status_code=404, content={"message": f"Paper ID {paper_uuid} not found locally."})

            # Fetch Original Questions for Matching
            import sqlite3
            conn = db.get_connection()
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(f"SELECT id, content_html FROM questions WHERE id IN ({','.join(['?']*len(qids))})", qids)
            rows = c.fetchall()
            conn.close()

            # Normalization Helper
            import re
            from bs4 import BeautifulSoup
            def normalize(text):
                return re.sub(r'\s+', '', text)

            original_map = {} 
            for r in rows:
                soup = BeautifulSoup(r['content_html'], 'html.parser')
                text = soup.get_text()
                norm = normalize(text)
                if len(norm) > 5: 
                    original_map[norm] = r['id']
            
            # Read Upload Content (Text Only)
            full_doc_text = normalize("\n".join([p.text for p in doc.paragraphs]))
            
            wrong_qids = []
            for norm_text, qid in original_map.items():
                if norm_text in full_doc_text:
                    wrong_qids.append(qid)
            
            # Update Stats
            stats = db.process_review_results(wrong_qids, qids)
            
            return {
                "type": "review",
                "data": {
                    "paper_id": paper_uuid,
                    "total_questions": len(qids),
                    "wrong_count": len(wrong_qids),
                    "right_count": len(qids) - len(wrong_qids),
                    "stats_update": stats
                }
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Review processing failed: {str(e)}")

    # --- 2. Standard Extraction Mode (Import) ---
    try:
        from extractor import QuestionExtractor
        extractor = QuestionExtractor(MEDIA_DIR)
        questions = extractor.extract_from_file(file_path)
        
        return {
            "type": "import",
            "data": questions
        }
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

    # Counters
    new_count = 0
    repeat_count = 0
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
            # Mistake in original code: logic to rescue material images missing?
            # We implemented text replacement in previous steps but maybe images are lost if only in material.
            # For now, let's stick to existing logic plus helper usage.
            
            # Fallback: Parse material HTML for /media/temp/ filenames
            # We must import re here if not globally imported or use the one from top
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
        
        qid, is_new = db.add_question(
            source_id=sid,
            original_num=q['original_num'],
            content=q['content_html'],
            options=q['options_html'],
            answer=q['answer_html'], 
            images=q['images'],
            type=q['type'],
            material_id=mid
        )
        
        if is_new:
            new_count += 1
        else:
            repeat_count += 1
            
        count += 1
        
    # --- Stats Calculation ---
    try:
        # Weights
        WEIGHTS = {
            "常识": 0.5,
            "言语": 0.8,
            "数量": 0.8,
            "判断": 0.7,
            "资料": 1.0,
            # Subtypes just in case
            "图形": 0.7, "定义": 0.7, "类比": 0.7, "逻辑": 0.7
        }

        mistake_nums = set(q['original_num'] for q in req.questions)
        
        module_stats = {} # {"Verbal": {correct: 0, total: 0}}
        total_score = 0.0
        total_questions = 0
        total_correct = 0

        for q in req.all_questions_meta:
            q_type = q.get('type', '未知')
            
            # Find Standard Module Name (grouping subtypes)
            module_name = "未知"
            if "常识" in q_type: module_name = "常识"
            elif "言语" in q_type: module_name = "言语"
            elif "数量" in q_type: module_name = "数量"
            elif "资料" in q_type: module_name = "资料"
            elif any(x in q_type for x in ["判断", "图形", "定义", "类比", "逻辑"]): module_name = "判断"

            # Init Module Entry
            if module_name not in module_stats:
                module_stats[module_name] = {"correct": 0, "total": 0}
            
            is_mistake = q['num'] in mistake_nums
            
            # Update Total
            module_stats[module_name]["total"] += 1
            total_questions += 1
            
            # Update Correct & Score
            if not is_mistake:
                module_stats[module_name]["correct"] += 1
                total_correct += 1
                
                # Add Score
                w = WEIGHTS.get(module_name, 0.5) # Default 0.5 for unknown
                total_score += w

        total_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0
        
        db.add_exam_record(req.source_filename, total_score, total_accuracy, module_stats)
        
    except Exception as e:
        print(f"Stats Calculation Failed: {e}")
        # Non-blocking, still return success for saving

    return {"status": "success", "saved_count": count, "new_count": new_count, "repeat_count": repeat_count}



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
def find_available_port(start_port, max_port=65535):
    import socket
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return None

if __name__ == "__main__":
    import argparse
    import uvicorn
    import threading
    import webbrowser
    import time
    import sys
    import os
    
    # Simple CLI Args
    parser = argparse.ArgumentParser(description="MistakeReservoir Server")
    parser.add_argument("--t", action="store_true", help="Enter terminal debug mode (no server)")
    parser.add_argument("--port", type=int, default=8000, help="Starting port number")
    args = parser.parse_args()
    
    # Debug Mode
    if args.t:
        print("Entering Terminal Debug Mode...")
        print("Variables available: app, db, extractor, etc.")
        import code
        context = globals().copy()
        context.update(locals())
        code.interact(local=context, banner="MistakeReservoir Debug Shell")
        sys.exit(0)

    # Server Mode
    port = find_available_port(args.port)
    if not port:
        # Try to print if possible, then exit
        if sys.stdout: print("Error: No available ports found.")
        sys.exit(1)
        
    print(f"Starting server on port {port}...")
    
    url = f"http://127.0.0.1:{port}"
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)
        
    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=monitor_heartbeat, daemon=True).start()
    
    # Uvicorn needs these streams to be valid file-like objects
    # Fix for PyInstaller --noconsole mode where sys.stdout/stderr/stdin are None
    if sys.stdout is None: sys.stdout = open(os.devnull, "w")
    if sys.stderr is None: sys.stderr = open(os.devnull, "w")
    if sys.stdin is None: sys.stdin = open(os.devnull, "r")
    
    try:
        # Enable logging by default (using uvicorn defaults)
        uvicorn.run(app, host="127.0.0.1", port=port)
    except Exception as e:
        # Minimal fail-safe error log
        if getattr(sys, 'frozen', False):
             try:
                 with open("startup_error.log", "w") as f:
                     f.write(f"Startup Failed: {str(e)}\n")
             except: pass
        raise e
