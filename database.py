import aiosqlite 
import os
from datetime import datetime 

DB_path = 'tasks.db'

async def init_db():
    """Initialize the database and create tables"""
    async with aiosqlite.connect(DB_path) as conn:
        await conn.execute('''
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
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await conn.commit()

async def create_task_db(title, description= "", priority= "medium", assigned_to= "", due_date= ""):
    """Create a new task in the database"""
    async with aiosqlite.connect(DB_path) as conn:
        # Normalize inputs to lowercase where appropriate (status and priority)
        priority_lower = priority.lower().strip() if priority else "medium"
        cursor = await conn.execute('''
            INSERT INTO tasks (title, description, priority, assigned_to, due_date)
             VALUES (?, ?, ?, ?, ?)
         ''', (title, description, priority_lower, assigned_to, due_date))
        task_id = cursor.lastrowid
        await conn.commit()
        return task_id

async def get_tasks_db(status=None):
    """Retrieve tasks from the database, optionally filtered by status"""
    async with aiosqlite.connect(DB_path) as conn:
        conn.row_factory = aiosqlite.Row
        if status:
            cursor = await conn.execute('SELECT * FROM tasks WHERE status = ?', (status.lower().strip(),))
        else:
            cursor = await conn.execute('SELECT * FROM tasks')
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_task_db(task_id, updates: dict):
    async with aiosqlite.connect(DB_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        allowed_fields = ['title', 'description', 'priority', 'status', 'assigned_to', 'due_date']
        
        # Filter only allowed fields
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not safe_updates:
            return False
            
        if 'status' in safe_updates:
            safe_updates['status'] = safe_updates['status'].lower().strip()
        if 'priority' in safe_updates:
            safe_updates['priority'] = safe_updates['priority'].lower().strip()
        
        # Build dynamic SET clause
        set_clause = ", ".join([f"{k} = ?" for k in safe_updates.keys()])
        values = list(safe_updates.values())
        values.append(datetime.now().isoformat())
        values.append(task_id)
        
        cursor = await conn.execute(f'''
            UPDATE tasks SET {set_clause}, updated_at = ?
            WHERE id = ?
        ''', values)

        affected = cursor.rowcount
        await conn.commit()
        return affected > 0

async def complete_task_db(task_id):
    async with aiosqlite.connect(DB_path) as conn:
        cursor = await conn.execute('''
            UPDATE tasks SET status = 'completed', updated_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), task_id))
        affected = cursor.rowcount
        await conn.commit()
        return affected > 0

async def delete_task_db(task_id):
    async with aiosqlite.connect(DB_path) as conn:
        cursor = await conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        affected = cursor.rowcount
        await conn.commit()
        return affected > 0

async def get_overdue_tasks_db():
    async with aiosqlite.connect(DB_path) as conn:
        conn.row_factory = aiosqlite.Row
        today = datetime.now().strftime('%Y-%m-%d')
        cursor = await conn.execute('''
            SELECT * FROM tasks 
            WHERE due_date < ? AND status != 'completed'
            AND due_date != ''
        ''', (today,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def search_tasks_db(keyword):
    async with aiosqlite.connect(DB_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute('''
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
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def save_setting(key: str, value: str):
    """Safely saves or updates a key-value setting"""
    async with aiosqlite.connect(DB_path) as conn:
        # Using ? parameters prevents SQL Injection
        await conn.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, value))
        await conn.commit()

async def get_setting(key: str):
    """Safely retrieves a setting by key, returns None if not found"""
    async with aiosqlite.connect(DB_path) as conn:
        conn.row_factory = aiosqlite.Row
        # Using ? parameters prevents SQL Injection
        cursor = await conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = await cursor.fetchone()
        return row['value'] if row else None