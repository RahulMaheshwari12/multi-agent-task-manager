from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import pathlib
from dotenv import load_dotenv
from graphs import run_pipeline
from database import (
    init_db,
    get_tasks_db,
    get_overdue_tasks_db,
    search_tasks_db,
    create_task_db,
    update_task_db,
    complete_task_db,
    delete_task_db
)

load_dotenv()

BASE_DIR = pathlib.Path(__file__).parent

# ── Lifespan ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down")

# ── App Setup ──────────────────────────────────────────
app = FastAPI(
    title="Multi-Agent Task Manager",
    description="AI powered task management system using LangGraph + Ollama",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name= "static")

class UserMessage(BaseModel):
    message : str

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    assigned_to: str = ""
    due_date: str = ""

class TaskUpdate(BaseModel):
    updates : dict

@app.get("/dashboard", response_class= HTMLResponse)
async def dashboard():
    with open(BASE_DIR / 'static' / 'index.html', encoding='utf-8') as f:
        return f.read()
    
@app.post("/chat")
async def chat(body : UserMessage):
    """Main endpoint — receives message, runs through agents, returns response"""
    try:
        if not body.message.strip():
            raise HTTPException(status_code= 400, detail = "Message cannot be empty")
        
        result = await run_pipeline(body.message)

        return {
            "success": True,
            "response": result.get("final_response", "Sorry, I could not process that."),
            "intent": result.get("intent", ""),
            "tool_output": result.get("tool_output", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/tasks")
async def get_tasks(status : str= ""):
    """Get all tasks, optionally filtered by status"""
    try:
        tasks = await get_tasks_db(status if status else None)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code= 500, detail= str(e))
    
@app.get("/tasks/overdue")
async def get_overdue_tasks():
    """Get all tasks that are not complete"""
    try:
        tasks = await get_overdue_tasks_db()
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code= 500, detail= str(e))
    
@app.get("/tasks/search")
async def search_tasks(keyword : str):
    """Search tasks by keyword"""
    try:
        tasks = await search_tasks_db(keyword)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code= 500, detail= str(e))
    
@app.post("/tasks")
async def create_task(body : TaskCreate):
    """Create task directly from dashboard"""
    try:
        task_id = await create_task_db(
            body.title,
            body.description,
            body.priority,
            body.assigned_to,
            body.due_date
        )
        return {"success": True, "Task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code= 500, detail= str(e))
    
@app.put("/tasks/{task_id}")
async def update_task(task_id : int, body : TaskUpdate):
    """Update tasks from dashboard"""
    try:
        tasks = await get_tasks_db()
        task = next((t for t in tasks if t['id'] == task_id), None)

        if not task:
            raise HTTPException(status_code= 404, detail=f"task {task_id} not found")
        
        success = await update_task_db(task_id, body.updates)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid fields or task not found")
        return {"success": True, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
@app.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    """Mark tasks as complete from dashboard"""
    try:
        tasks = await get_tasks_db()
        task = next((t for t in tasks if t['id'] == task_id), None)

        if not task:
            raise HTTPException(status_code= 404, detail=f"task {task_id} not found")
        
        if task['status'] == 'completed':
            raise HTTPException(status_code= 400, detail= f"Task {task_id} is already completed")
        
        await complete_task_db(task_id)
        return {"success" : True, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code= 500, detail= str(e))
        
@app.delete("/tasks/{task_id}")
async def delete_task(task_id : int):
    """Delete task from dashboard"""
    try:
        tasks = await get_tasks_db()
        task = next((t for t in tasks if t['id'] == task_id), None)

        if not task:
            raise HTTPException(status_code= 404, detail=f"task {task_id} not found")
        
        await delete_task_db(task_id)
        return {"success": True, "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code= 500, detail= str(e))
    

@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "Multi-Agent Task Manager API",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )