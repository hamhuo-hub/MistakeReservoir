import sqlite3
conn = sqlite3.connect('reservoir.db')
c = conn.cursor()
try:
    c.execute("PRAGMA table_info(review_stats)")
    columns = c.fetchall()
    print("Columns in review_stats:")
    for col in columns:
        print(col)
except Exception as e:
    print(e)
conn.close()
