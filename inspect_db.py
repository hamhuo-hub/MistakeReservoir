import sqlite3
conn = sqlite3.connect('reservoir.db')
c = conn.cursor()
try:
    c.execute("PRAGMA table_info(questions)")
    columns = c.fetchall()
    print("Columns in questions:")
    for col in columns:
        print(col)
        
    c.execute("PRAGMA table_info(materials)")
    columns = c.fetchall()
    print("Columns in materials:")
    for col in columns:
        print(col)
except Exception as e:
    print(e)
conn.close()
