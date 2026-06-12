from langchain_core.tools import tool 
from database import (
    create_task_db,
    get_tasks_db,
    update_task_db,
    complete_task_db,
    delete_task_db,
    get_overdue_tasks_db,
    search_tasks_db
)

@tool
async def create_task(title: str, description: str, assigned_to: str, priority: str, due_date: str) -> str:
    """Create a new task in database.
    priority can be: low, medium, high.
    due_date format: YYYY-MM-DD
    """
    try:
        task_id = await create_task_db(title, description, priority, assigned_to, due_date)
        return f'Task created successfully with ID: {task_id}'
    except Exception as e:
        return f'Error creating task: {str(e)}'
    
@tool 
async def get_tasks(status: str= "") -> str:
    """Get all tasks from the database. 
    Optionally filter by status: pending, completed, in_progress."""
    try:
        tasks = await get_tasks_db(status if status else None)
        if not tasks:
            return "No tasks found."
        output= ""
        for t in tasks:
             output += f"ID: {t['id']} | {t['title']} | Priority: {t['priority']} | Status: {t['status']} | Assigned: {t['assigned_to']} | Due: {t['due_date']}\n"
        return output 
    except Exception as e:
        return f'Error fetching tasks: {str(e)}'
    
@tool 
async def update_task(task_id: int, updates: dict) -> str:
    """Update one or more fields of a task.
    Updates is a dict of field:value pairs.
    Allowed fields: title, description, priority, status, assigned_to, due_date"""
    try:
        tasks = await get_tasks_db()
        task = next((t for t in tasks if t['id'] == task_id), None)
        
        if not task:
            return f"Task {task_id} not found."
        
        success = await update_task_db(task_id, updates)
        if success:
            return f'Task {task_id} updated successfully.'
        return f'no valid fields to update for task {task_id}.'
    except Exception as e:
        return f'Error updating task: {str(e)}'
    
@tool
async def complete_task(task_id: int) -> str:
    """Mark a task as completed."""
    try:
        tasks = await get_tasks_db()
        task = next((t for t in tasks if t['id'] == task_id), None)
        
        if not task:
            return f"Task {task_id} not found."
        
        if task['status'] == 'completed':
            return f"Task {task_id} is already completed."
        
        await complete_task_db(task_id)
        return f"Task {task_id} marked as completed."
    except Exception as e:
        return f"Failed to complete task: {str(e)}"
    
@tool 
async def delete_task(task_id: int) -> str:
    """Delete a task"""
    try:
        tasks = await get_tasks_db()
        task = next((t for t in tasks if t['id'] == task_id), None)

        if not task:
            return f'Task {task_id} does not exist or was already deleted'
        
        await delete_task_db(task_id)
        return f'Task {task_id} deleted successfully.'
    except Exception as e:
       return f'Failed to delete task {task_id}: {str(e)}'
    
@tool 
async def get_overdue_tasks() -> str:
    """Get all that tasks that are passed their due dates and not completed"""
    try:
        tasks = await get_overdue_tasks_db()
        if not tasks:
            return "No over dues Tasks found"
        output = "Overdue tasks: \n"
        for t in tasks:
            output += f"ID: {t['id']} | {t['title']} | Due: {t['due_date']} | Assigned: {t['assigned_to']}\n"
        return output 
    except Exception as e:
        return f"Failed to get overdue tasks: {str(e)}"
    
@tool
async def search_tasks(keyword: str) -> str:
    """Search tasks by keyword in title, description, assigned person, priority, status or due date."""
    try:
        tasks = await search_tasks_db(keyword)
        if not tasks:
            return f"No tasks found matching '{keyword}'."
        output = f"Tasks matching '{keyword}':\n"
        for t in tasks:
            output += f"ID: {t['id']} | {t['title']} | Priority: {t['priority']} | Status: {t['status']} | Assigned: {t['assigned_to']}\n"
        return output
    except Exception as e:
        return f"Search failed: {str(e)}"
