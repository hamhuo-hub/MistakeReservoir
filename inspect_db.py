import sqlite3

def inspect_db():
    conn = sqlite3.connect("reservoir.db")
    cursor = conn.cursor()
    
    # List Tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables found:")
    for t in tables:
        print(f"- {t[0]}")
        
    print("\nColumns per table:")
    for t in tables:
        table_name = t[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n[{table_name}]")
        for col in columns:
            # cid, name, type, notnull, dflt_value, pk
            print(f"  {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    inspect_db()
