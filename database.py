import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "reservoir.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Sources
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_date TEXT
            )
        ''')
        
        # Materials (Shared content for Data Analysis etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                content_html TEXT,
                images TEXT, -- JSON List
                type TEXT
            )
        ''')
        
        # Questions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                material_id INTEGER,
                original_num INTEGER,
                type TEXT,
                content_html TEXT,
                options_html TEXT, -- Separated Options
                answer_html TEXT, -- Analysis + Answer
                images TEXT, -- JSON List
                FOREIGN KEY(source_id) REFERENCES sources(id),
                FOREIGN KEY(material_id) REFERENCES materials(id)
            )
        ''')
        
        # Review Stats (NEW SCHEMA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_stats (
                question_id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'pool',
                mistake_count INTEGER DEFAULT 2,
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        ''')
        
        # Add Trigger via Python if not exists?
        # Ideally schema init should include it.
        # But our migration script already added it.
        # For new installs:
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS auto_delete_mastered
            AFTER UPDATE OF mistake_count ON review_stats
            WHEN NEW.mistake_count <= 0
            BEGIN
                DELETE FROM questions WHERE id = NEW.question_id;
            END;
        ''')
        
        # Exam Records (Auto-Calculated from Uploads)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_date TEXT, -- ISO Timestamp
                filename TEXT,
                total_score REAL,
                total_accuracy REAL,
                module_stats TEXT, -- JSON breakdown
                time_used INTEGER -- Actual time used in minutes (Added in v2)
            )
        ''')
        
        # Generated Papers (For Review Mode)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_papers (
                uuid TEXT PRIMARY KEY,
                created_at TEXT,
                question_ids TEXT -- JSON List of Int
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_source(self, filename: str) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        
        # Check if source exists to prevent duplication
        c.execute("SELECT id FROM sources WHERE filename=?", (filename,))
        row = c.fetchone()
        
        if row:
            sid = row['id']
            # Update upload date to reflect recent activity
            c.execute("UPDATE sources SET upload_date=? WHERE id=?", 
                      (datetime.now().isoformat(), sid))
        else:
            c.execute("INSERT INTO sources (filename, upload_date) VALUES (?, ?)", 
                      (filename, datetime.now().isoformat()))
            sid = c.lastrowid
            
        conn.commit()
        conn.close()
        return sid

    def add_material(self, source_id: int, content: str, images: List[str] = [], type: str = "data_analysis") -> int:
        # Check duplicate? (Simple check by content hash or just text matching if needed, 
        # but here we allow dupes if from different imports or relying on source_id)
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO materials (source_id, content_html, images, type) VALUES (?, ?, ?, ?)",
                  (source_id, content, json.dumps(images), type))
        mid = c.lastrowid
        conn.commit()
        conn.close()
        return mid

    def add_question(self, source_id: int, original_num: int, content: str, options: str,
                     answer: str, images: List[str], type: str, material_id: Optional[int] = None) -> (int, bool):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Check existence?
        c.execute("SELECT id FROM questions WHERE source_id=? AND original_num=?", (source_id, original_num))
        exist = c.fetchone()
        if exist:
            qid = exist['id']
            # Update content
            c.execute('''
                UPDATE questions 
                SET content_html=?, options_html=?, answer_html=?, images=?, type=?, material_id=?
                WHERE id=?
            ''', (content, options, answer, json.dumps(images), type, material_id, qid))
            
            # Increment Mistake Count (Repetition)
            # Ensure it bumps back to at least 2 (New) even if it was at 1.
            c.execute('''
                UPDATE review_stats 
                SET mistake_count = MAX(mistake_count + 1, 2)
                WHERE question_id = ?
            ''', (qid,))
            
            conn.commit()
            conn.close()
            return qid, False # Not new
            
        c.execute('''
            INSERT INTO questions (source_id, material_id, original_num, type, content_html, options_html, answer_html, images)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source_id, material_id, original_num, type, content, options, answer, json.dumps(images)))
        
        qid = c.lastrowid
        
        c.execute('''
            INSERT INTO review_stats (question_id, status, mistake_count)
            VALUES (?, 'pool', 2)
        ''', (qid,))
        
        conn.commit()
        conn.close()
        return qid, True # New

    def update_question_text(self, qid: int, content: str, options: str, answer: str):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE questions 
            SET content_html=?, options_html=?, answer_html=?
            WHERE id=?
        ''', (content, options, answer, qid))
        conn.commit()
        conn.close()

    def delete_question(self, qid: int):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM review_stats WHERE question_id=?", (qid,))
            c.execute("DELETE FROM questions WHERE id=?", (qid,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_pool_status(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''
            SELECT q.type, COUNT(*) as count 
            FROM review_stats r
            JOIN questions q ON r.question_id = q.id
            WHERE r.status = 'pool'
            GROUP BY q.type
        ''')
        stats = {row['type']: row['count'] for row in c.fetchall()}
        conn.close()
        return stats

    def get_all_questions(self):
        """
        Fetch all questions with source info.
        """
        conn = self.get_connection()
        c = conn.cursor()
        
        query = '''
            SELECT q.*, s.filename as source_filename, m.content_html as material_content
            FROM questions q
            JOIN sources s ON q.source_id = s.id
            LEFT JOIN materials m ON q.material_id = m.id
            ORDER BY q.id DESC
        '''
        
        c.execute(query)
        rows = c.fetchall()
        
        questions = []
        for row in rows:
            q = dict(row)
            if q.get('images'): q['images'] = json.loads(q['images'])
            questions.append(q)
            
        conn.close()
        return questions

    def get_random_questions(self, count: int, type_filter: List[str] = None):
        """
        Fetch random questions from the pool.
        """
        conn = self.get_connection()
        c = conn.cursor()
        
        query = '''
            SELECT q.*, m.content_html as material_content, m.images as material_images
            FROM review_stats r
            JOIN questions q ON r.question_id = q.id
            LEFT JOIN materials m ON q.material_id = m.id
            WHERE r.status = 'pool'
        '''
        params = []
        
        if type_filter:
            placeholders = ','.join(['?'] * len(type_filter))
            query += f" AND q.type IN ({placeholders})"
            params.extend(type_filter)
            
        query += " ORDER BY r.mistake_count DESC, RANDOM() LIMIT ?"
        params.append(count)
        
        c.execute(query, params)
        rows = c.fetchall()
        
        # Convert to dict
        questions = []
        for row in rows:
            q = dict(row)
            # Parse JSONs
            if q.get('images'): q['images'] = json.loads(q['images'])
            if q.get('material_images'): q['material_images'] = json.loads(q['material_images'])
            questions.append(q)
            
        conn.close()
        return questions

    def get_standard_exam_questions(self, count: int = 130):
        """
        Fetch questions respecting the standard composition:
        Common: 20
        Verbal: 40
        Quant: 15
        Judgment: 40 (Graph 10, Dict 10, Analogy 10, Logic 10)
        Data: 15
        
        If count != 130, we scale these ratios.
        """
        SCALE = count / 130.0
        
        # Define Composition
        # Using exact matching for types stored in DB
        
        # Note: In DB, '判断' might be stored as specific subtypes '图形', '定义', '类比', '逻辑'
        # based on extractor logic if section headers were found.
        # However, extractor defaults to '判断' if only "判断" found.
        # We need to handle fallback.
        
        composition = [
            ("常识", int(20 * SCALE)),
            ("言语", int(40 * SCALE)),
            ("数量", int(15 * SCALE)),
            ("资料", int(15 * SCALE)),
            # Judyment Subtypes
            ("图形", int(10 * SCALE)),
            ("定义", int(10 * SCALE)),
            ("类比", int(10 * SCALE)),
            ("逻辑", int(10 * SCALE)),
        ]
        
        all_questions = []
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row # Ensure we get dict-like access
        
        # Fetch for each type
        for type_key, needed in composition:
            if needed <= 0: continue
            
            # For Judgment subtypes, we query specifically.
            # But what if DB has just "判断"? 
            # We add a fallback: if specific subtypes yield 0, try fetching "判断" and distribute?
            # For now, simplistic approach:
            
            c = conn.cursor()
            # Select with limit
            # Also join materials
            query = '''
                SELECT q.*, m.content_html as material_content, m.images as material_images
                FROM review_stats r
                JOIN questions q ON r.question_id = q.id
                LEFT JOIN materials m ON q.material_id = m.id
                WHERE r.status = 'pool' AND q.type LIKE ?
                ORDER BY r.mistake_count DESC, RANDOM() LIMIT ?
            '''
            c.execute(query, (f"%{type_key}%", needed))
            rows = c.fetchall()
            
            for row in rows:
                q = dict(row)
                if q.get('images'): q['images'] = json.loads(q['images'])
                if q.get('material_images'): q['material_images'] = json.loads(q['material_images'])
                all_questions.append(q)
                
            c.close()

        conn.close()
        
        # If we are short on questions (e.g. didn't find "图形" but only "判断"), 
        # we currently just return what we found. 
        # Ideally we should fill gaps with "Unknown" or generic "判断" if subtypes missing.
        
        return all_questions

    def wipe_database(self):
        """
        Wipe all data from tables but keep the schema.
        """
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM review_stats")
            c.execute("DELETE FROM questions")
            c.execute("DELETE FROM materials")
            c.execute("DELETE FROM sources")
            conn.commit()
            print("Database Wiped Clean.")
        except Exception as e:
            print(f"Error wiping database: {e}")
            conn.rollback()
        finally:
            conn.close()

    def migrate_cleanup_stats(self):
        """
        Migration:
        1. Calculate mistake_count = mistake_count - right_streak (where right_streak exists)
        2. Remove right_streak and last_right_date columns by recreating table
        """
        conn = self.get_connection()
        c = conn.cursor()
        print("Starting migration: Clean up review stats...")
        
        try:
            # 1. Update data in place first (if column exists)
            try:
                # Check if right_streak exists
                c.execute("SELECT right_streak FROM review_stats LIMIT 1")
                # Update logic: mistake_count = MAX(mistake_count - right_streak, ?) 
                # Actually user just said subtract. If it goes below 0 trigger handles it?
                # Trigger fires on UPDATE. 
                # But we probably want to apply this calculation BEFORE recreating table.
                
                print("Applying formula: mistake_count = mistake_count - right_streak")
                c.execute("UPDATE review_stats SET mistake_count = mistake_count - right_streak")
                
                # Check for deletions handled by trigger? 
                # The trigger `auto_delete_mastered` fires AFTER UPDATE.
                # So if mistake_count becomes <= 0, the question is deleted.
                # This is correct per user intent (mastered items gone).
                
            except sqlite3.OperationalError:
                print("Column 'right_streak' not found, skipping data update.")

            # 2. Recreate Table to drop columns
            print("Recreating review_stats table...")
            
            # Rename old
            c.execute("ALTER TABLE review_stats RENAME TO review_stats_old")
            
            # Create new
            c.execute('''
                CREATE TABLE review_stats (
                    question_id INTEGER PRIMARY KEY,
                    status TEXT DEFAULT 'pool',
                    mistake_count INTEGER DEFAULT 2,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                )
            ''')
            
            # Check if last_wrong_date exists in old table
            c.execute("PRAGMA table_info(review_stats_old)")
            old_columns = [col[1] for col in c.fetchall()]
            
            # Copy Data (Ignore dates)
            c.execute('''
                INSERT INTO review_stats (question_id, status, mistake_count)
                SELECT question_id, status, mistake_count
                FROM review_stats_old
            ''')
            
            # Drop old
            c.execute("DROP TABLE review_stats_old")
            
            # Recreate Trigger
            c.execute("DROP TRIGGER IF EXISTS auto_delete_mastered")
            c.execute('''
                CREATE TRIGGER auto_delete_mastered
                AFTER UPDATE OF mistake_count ON review_stats
                WHEN NEW.mistake_count <= 0
                BEGIN
                    DELETE FROM questions WHERE id = NEW.question_id;
                END;
            ''')
            
            conn.commit()
            print("Migration completed info.")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            conn.rollback()
        finally:
            conn.close()

    def migrate_database(self):
        """
        Run schema migrations.
        """
        conn = self.get_connection()
        c = conn.cursor()
        try:
            # Migration 1: Add options_html if missing (Old)
            try:
                c.execute("ALTER TABLE questions ADD COLUMN options_html TEXT")
                print("Added options_html column.")
            except sqlite3.OperationalError:
                pass # Already exists

            # Migration 2: Add time_used to exam_records (New)
            try:
                c.execute("ALTER TABLE exam_records ADD COLUMN time_used INTEGER")
                print("Added time_used column to exam_records.")
            except sqlite3.OperationalError:
                pass # Already exists
            
            conn.commit()
            print("Migration checks completed.")
        except Exception as e:
            print(f"Error migrating database: {e}")
        finally:
            conn.close()

    def add_exam_record(self, filename: str, total_score: float, total_accuracy: float, module_stats: dict, time_used: Optional[int] = None) -> int:
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO exam_records (upload_date, filename, total_score, total_accuracy, module_stats, time_used)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), filename, total_score, total_accuracy, json.dumps(module_stats), time_used))
        
        sid = c.lastrowid
        conn.commit()
        conn.close()
        return sid

    def get_exam_stats(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM exam_records ORDER BY upload_date ASC")
        rows = c.fetchall()
        
        results = []
        for row in rows:
            r = dict(row)
            if r.get('module_stats'): r['module_stats'] = json.loads(r['module_stats'])
            results.append(r)
            
        conn.close()
        return results

    # --- Review Mode Methods ---

    def record_generated_paper(self, uuid: str, question_ids: List[int]):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO generated_papers (uuid, created_at, question_ids) VALUES (?, ?, ?)",
                  (uuid, datetime.now().isoformat(), json.dumps(question_ids)))
        conn.commit()
        conn.close()

    def get_generated_paper_qids(self, uuid: str) -> List[int]:
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT question_ids FROM generated_papers WHERE uuid=?", (uuid,))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row['question_ids'])
        return []

    def get_all_generated_papers(self):
        """
        Fetch all generated papers for history view.
        """
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM generated_papers ORDER BY created_at DESC")
        rows = c.fetchall()
        
        papers = []
        for row in rows:
            p = dict(row)
            if p.get('question_ids'):
                try:
                    qids = json.loads(p['question_ids'])
                    p['question_count'] = len(qids)
                except:
                    p['question_count'] = 0
            papers.append(p)
            
        conn.close()
        return papers

    def process_review_results(self, wrong_qids: List[int], all_paper_qids: List[int]) -> Dict:
        """
        Updates stats.
        Simplified Logic:
        - Wrong: mistake_count + 1
        - Right: mistake_count - 1
        - Deletion: Handled by DB Trigger (mistake_count <= 0)
        """
        conn = self.get_connection()
        c = conn.cursor()
        
        wrong_set = set(wrong_qids)
        stats = {"mistakes": 0, "improved": 0}
        
        for qid in all_paper_qids:
            if qid in wrong_set:
                # Wrong: +1
                c.execute('''
                    UPDATE review_stats 
                    SET mistake_count = mistake_count + 1
                    WHERE question_id = ?
                ''', (qid,))
                stats['mistakes'] += 1
            else:
                # Right: -1
                c.execute('''
                    UPDATE review_stats 
                    SET mistake_count = mistake_count - 1
                    WHERE question_id = ?
                ''', (qid,))
                stats['improved'] += 1
        
        conn.commit()
        conn.close()
        return stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Manager CLI")
    parser.add_argument("--wipe", action="store_true", help="Wipe all data from database")
    parser.add_argument("--migrate", action="store_true", help="Run schema migrations")
    parser.add_argument("--migrate-stats", action="store_true", help="Clean up stats table (Remove right_streak)")
    
    args = parser.parse_args()
    
    db = DatabaseManager()
    
    if args.wipe:
        confirm = input("Are you sure you want to WIPE the database? (y/n): ")
        if confirm.lower() == 'y':
            db.wipe_database()
        else:
            print("Wipe cancelled.")
            
    if args.migrate:
        db.migrate_database()

    if args.migrate_stats:
        db.migrate_cleanup_stats()
        
    print(f"Database Manager initialized at {db.db_path}")

