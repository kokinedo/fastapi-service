from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import asyncio
import logging

from app.database import get_db, engine, Base
from app.crud import TaskCRUD, ConversationCRUD
from app.schemas import Task, TaskCreate, TaskUpdate, TaskList, Conversation, ConversationCreate, ConversationUpdate
from app.background_worker import start_background_worker, stop_background_worker
from app.config import settings
from app.logging_config import setup_logging
from app.exceptions import (
    TaskNotFoundError, ConversationNotFoundError, TaskProcessingError, 
    DatabaseError, task_not_found_handler, conversation_not_found_handler,
    task_processing_error_handler, database_error_handler, 
    general_exception_handler, custom_http_exception_handler
)
from app.health import check_database_health, get_system_metrics, get_app_info

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add exception handlers
app.add_exception_handler(TaskNotFoundError, task_not_found_handler)
app.add_exception_handler(ConversationNotFoundError, conversation_not_found_handler)
app.add_exception_handler(TaskProcessingError, task_processing_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Background task for the worker
background_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize database and start background worker"""
    global background_task
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start background worker
    background_task = asyncio.create_task(start_background_worker())
    logger.info("Application started with background worker")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background worker"""
    global background_task
    
    stop_background_worker()
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    logger.info("Application shutdown complete")

# Task endpoints
@app.post("/tasks/", response_model=Task)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task with optional conversations"""
    return await TaskCRUD.create_task(db, task)

@app.get("/tasks/", response_model=List[TaskList])
async def get_tasks(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all tasks with conversation counts"""
    tasks_with_counts = await TaskCRUD.get_tasks(db, skip=skip, limit=limit)
    
    result = []
    for task, conversation_count in tasks_with_counts:
        result.append(TaskList(
            id=task.id,
            title=task.title,
            status=task.status,
            created_at=task.created_at,
            conversation_count=conversation_count or 0
        ))
    
    return result

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific task with all its conversations"""
    task = await TaskCRUD.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_update: TaskUpdate, db: AsyncSession = Depends(get_db)):
    """Update a task"""
    task = await TaskCRUD.update_task(db, task_id, task_update)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task and all its conversations"""
    success = await TaskCRUD.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Conversation endpoints
@app.post("/tasks/{task_id}/conversations/", response_model=Conversation)
async def create_conversation(task_id: int, conversation: ConversationCreate, db: AsyncSession = Depends(get_db)):
    """Create a new conversation for a task"""
    # Check if task exists
    task = await TaskCRUD.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return await ConversationCRUD.create_conversation(db, conversation, task_id)

@app.get("/tasks/{task_id}/conversations/", response_model=List[Conversation])
async def get_conversations(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get all conversations for a task"""
    # Check if task exists
    task = await TaskCRUD.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return await ConversationCRUD.get_conversations_by_task(db, task_id)

@app.put("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(conversation_id: int, conversation_update: ConversationUpdate, db: AsyncSession = Depends(get_db)):
    """Update a conversation"""
    conversation = await ConversationCRUD.update_conversation(db, conversation_id, conversation_update)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {"status": "healthy", "message": "Task management service is running"}

# Detailed health check
@app.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check including database connectivity"""
    db_health = await check_database_health()
    app_info = get_app_info()
    
    return {
        "service": "healthy",
        "database": db_health,
        "application": app_info
    }

# Status endpoint
@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get service status including worker information"""
    from app.background_worker import worker
    return {
        "status": "running",
        "worker_instance_id": worker.instance_id,
        "worker_running": worker.is_running
    }

# Metrics endpoint
@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics and statistics"""
    return await get_system_metrics()

# Application info endpoint
@app.get("/info")
async def get_info() -> Dict[str, Any]:
    """Get application information"""
    return get_app_info()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)