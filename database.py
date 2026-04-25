import sqlite3

def init_db():
    conn = sqlite3.connect("student.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS STUDENT (
        NAME VARCHAR(25), 
        COURSE VARCHAR(25), 
        SECTION VARCHAR(25), 
        MARKS INT
    );
    """)
    
    # Check if empty before inserting
    cursor.execute("SELECT COUNT(*) FROM STUDENT")
    if cursor.fetchone()[0] == 0:
        data = [
            ('Student1', 'Data Science', 'A', 90),
            ('Student2', 'Data Science', 'B', 100),
            ('Student3', 'Data Science', 'A', 86),
            ('Student4', 'DEVOPS', 'A', 50),
            ('Student5', 'DEVOPS', 'A', 35)
        ]
        cursor.executemany("INSERT INTO STUDENT VALUES (?,?,?,?)", data)
        conn.commit()
        print("Database initialized with 5 students.")
    conn.close()

if __name__ == "__main__":
    init_db()