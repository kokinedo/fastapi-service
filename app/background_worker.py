import asyncio
import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.crud import TaskCRUD, ConversationCRUD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundTaskProcessor:
    def __init__(self):
        self.instance_id = str(uuid.uuid4())
        self.is_running = False
        
    async def process_task(self, task_id: int) -> bool:
        """Process a single task - simulates 6-7 seconds of work"""
        logger.info(f"Instance {self.instance_id} processing task {task_id}")
        
        try:
            # Simulate processing time (6-7 seconds)
            await asyncio.sleep(6.5)
            
            # Update all related conversations
            async with async_session_maker() as db:
                updated_count = await ConversationCRUD.update_conversations_by_task(
                    db, task_id, status="processed"
                )
                logger.info(f"Updated {updated_count} conversations for task {task_id}")
                
                # Mark task as completed
                success = await TaskCRUD.complete_task(db, task_id, self.instance_id)
                if success:
                    logger.info(f"Task {task_id} completed successfully")
                    return True
                else:
                    logger.error(f"Failed to mark task {task_id} as completed")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            # Mark task as failed
            async with async_session_maker() as db:
                await TaskCRUD.fail_task(db, task_id, self.instance_id)
            return False
    
    async def worker_loop(self):
        """Main worker loop that continuously processes tasks"""
        logger.info(f"Starting background worker with instance ID: {self.instance_id}")
        self.is_running = True
        
        while self.is_running:
            try:
                async with async_session_maker() as db:
                    # Get next pending task
                    task = await TaskCRUD.get_next_pending_task(db, self.instance_id)
                    
                    if task:
                        logger.info(f"Found task {task.id} to process")
                        await self.process_task(task.id)
                    else:
                        # No tasks available, wait before checking again
                        await asyncio.sleep(5)
                        
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    def stop(self):
        """Stop the worker loop"""
        logger.info(f"Stopping background worker {self.instance_id}")
        self.is_running = False

# Global worker instance
worker = BackgroundTaskProcessor()

async def start_background_worker():
    """Start the background worker"""
    await worker.worker_loop()

def stop_background_worker():
    """Stop the background worker"""
    worker.stop()