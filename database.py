import sqlite3 
import os
from datetime import datetime 

DB_path = 'tasks.db'

def get_db_connection():
    conn = sqlite3.connect(DB_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            assigned_to TEXT,
            due_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def create_task_db(title, description= "", priority= "medium", assigned_to= "", due_date= ""):
    """Create a new task in the database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (title, description, priority, assigned_to, due_date)
             VALUES (?, ?, ?, ?, ?)
         ''', (title, description, priority, assigned_to, due_date))
        task_id = cursor.lastrowid
        conn.commit()
        return task_id
    finally:
         conn.close()

def get_tasks_db(status=None):
    """Retrieve tasks from the database, optionally filtered by status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute('SELECT * FROM tasks WHERE status = ?', (status,))
    else:
        cursor.execute('SELECT * FROM tasks')
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def update_task_db(task_id, updates: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['title', 'description', 'priority', 'status', 'assigned_to', 'due_date']
    
    # Filter only allowed fields
    safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not safe_updates:
        return False
    
    # Build dynamic SET clause
    set_clause = ", ".join([f"{k} = ?" for k in safe_updates.keys()])
    values = list(safe_updates.values())
    values.append(datetime.now().isoformat())
    values.append(task_id)
    
    cursor.execute(f'''
        UPDATE tasks SET {set_clause}, updated_at = ?
        WHERE id = ?
    ''', values)

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def complete_task_db(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks SET status = 'completed', updated_at = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), task_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def delete_task_db(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_overdue_tasks_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE due_date < ? AND status != 'completed'
        AND due_date != ''
    ''', (today,))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def search_tasks_db(keyword):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE title LIKE ? 
        OR description LIKE ? 
        OR assigned_to LIKE ?
        OR priority LIKE ?
        OR status LIKE ?
        OR due_date LIKE ?
    ''', (
        f'%{keyword}%',
        f'%{keyword}%',
        f'%{keyword}%',
        f'%{keyword}%',
        f'%{keyword}%',
        f'%{keyword}%'
    ))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks