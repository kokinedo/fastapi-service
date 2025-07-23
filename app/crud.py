from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, text
from typing import List, Optional
import uuid
from datetime import datetime

from app.models import Task, Conversation
from app.schemas import TaskCreate, TaskUpdate, ConversationCreate, ConversationUpdate

class TaskCRUD:
    @staticmethod
    async def create_task(db: AsyncSession, task: TaskCreate) -> Task:
        db_task = Task(
            title=task.title,
            description=task.description,
            status="pending"
        )
        db.add(db_task)
        await db.flush()  # Get the task ID
        
        # Create associated conversations
        for conv_data in task.conversations:
            db_conversation = Conversation(
                task_id=db_task.id,
                content=conv_data.content,
                status=conv_data.status
            )
            db.add(db_conversation)
        
        await db.commit()
        
        # Reload the task with conversations
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.conversations))
            .where(Task.id == db_task.id)
        )
        return result.scalar_one()
    
    @staticmethod
    async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.conversations))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tasks(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Task]:
        result = await db.execute(
            select(Task, func.count(Conversation.id).label("conversation_count"))
            .outerjoin(Conversation)
            .group_by(Task.id)
            .offset(skip)
            .limit(limit)
            .order_by(Task.created_at.desc())
        )
        return result.all()
    
    @staticmethod
    async def update_task(db: AsyncSession, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        result = await db.execute(select(Task).where(Task.id == task_id))
        db_task = result.scalar_one_or_none()
        
        if not db_task:
            return None
        
        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_task, field, value)
        
        await db.commit()
        
        # Reload the task with conversations
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.conversations))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_task(db: AsyncSession, task_id: int) -> bool:
        result = await db.execute(select(Task).where(Task.id == task_id))
        db_task = result.scalar_one_or_none()
        
        if not db_task:
            return False
        
        await db.delete(db_task)
        await db.commit()
        return True
    
    @staticmethod
    async def get_next_pending_task(db: AsyncSession, instance_id: str) -> Optional[Task]:
        """Get and lock the next pending task for processing"""
        # First, find the next pending task
        result = await db.execute(
            text("""
                SELECT id FROM tasks 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                FOR UPDATE SKIP LOCKED 
                LIMIT 1
            """)
        )
        
        row = result.fetchone()
        if not row:
            return None
        
        task_id = row[0]
        
        # Now update the task to processing status
        result = await db.execute(
            text("""
                UPDATE tasks 
                SET status = 'processing', 
                    processing_instance_id = :instance_id,
                    updated_at = NOW()
                WHERE id = :task_id
                AND status = 'pending'
            """),
            {"instance_id": instance_id, "task_id": task_id}
        )
        
        await db.commit()
        
        if result.rowcount > 0:
            # Get the updated task
            task_result = await db.execute(select(Task).where(Task.id == task_id))
            return task_result.scalar_one_or_none()
        
        return None
    
    @staticmethod
    async def complete_task(db: AsyncSession, task_id: int, instance_id: str) -> bool:
        """Mark task as completed if it's being processed by this instance"""
        result = await db.execute(
            text("""
                UPDATE tasks 
                SET status = 'completed', 
                    processed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :task_id 
                AND processing_instance_id = :instance_id
                AND status = 'processing'
            """),
            {"task_id": task_id, "instance_id": instance_id}
        )
        
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def fail_task(db: AsyncSession, task_id: int, instance_id: str) -> bool:
        """Mark task as failed if it's being processed by this instance"""
        result = await db.execute(
            text("""
                UPDATE tasks 
                SET status = 'failed', 
                    updated_at = NOW()
                WHERE id = :task_id 
                AND processing_instance_id = :instance_id
                AND status = 'processing'
            """),
            {"task_id": task_id, "instance_id": instance_id}
        )
        
        await db.commit()
        return result.rowcount > 0

class ConversationCRUD:
    @staticmethod
    async def create_conversation(db: AsyncSession, conversation: ConversationCreate, task_id: int) -> Conversation:
        db_conversation = Conversation(
            task_id=task_id,
            content=conversation.content,
            status=conversation.status
        )
        db.add(db_conversation)
        await db.commit()
        await db.refresh(db_conversation)
        return db_conversation
    
    @staticmethod
    async def get_conversations_by_task(db: AsyncSession, task_id: int) -> List[Conversation]:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.task_id == task_id)
            .order_by(Conversation.created_at.asc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_conversation(db: AsyncSession, conversation_id: int, conversation_update: ConversationUpdate) -> Optional[Conversation]:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            return None
        
        update_data = conversation_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_conversation, field, value)
        
        await db.commit()
        await db.refresh(db_conversation)
        return db_conversation
    
    @staticmethod
    async def update_conversations_by_task(db: AsyncSession, task_id: int, status: str = "processed") -> int:
        """Update all conversations for a task (used during task processing)"""
        result = await db.execute(
            text("""
                UPDATE conversations 
                SET status = :status, updated_at = NOW()
                WHERE task_id = :task_id
            """),
            {"status": status, "task_id": task_id}
        )
        
        await db.commit()
        return result.rowcount