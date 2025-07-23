from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and basic operations."""
    try:
        async for db in get_db():
            # Test basic connectivity
            result = await db.execute(text("SELECT 1"))
            result.fetchone()
            
            # Test task table access
            task_count = await db.execute(text("SELECT COUNT(*) FROM tasks"))
            total_tasks = task_count.scalar()
            
            # Test conversation table access
            conv_count = await db.execute(text("SELECT COUNT(*) FROM conversations"))
            total_conversations = conv_count.scalar()
            
            return {
                "status": "healthy",
                "total_tasks": total_tasks,
                "total_conversations": total_conversations,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics and statistics."""
    try:
        async for db in get_db():
            # Task statistics
            task_stats = await db.execute(text("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM tasks 
                GROUP BY status
            """))
            
            task_counts = {row[0]: row[1] for row in task_stats.fetchall()}
            
            # Processing statistics
            processing_stats = await db.execute(text("""
                SELECT 
                    processing_instance_id,
                    COUNT(*) as processed_count
                FROM tasks 
                WHERE status = 'completed' AND processing_instance_id IS NOT NULL
                GROUP BY processing_instance_id
            """))
            
            instance_stats = {row[0]: row[1] for row in processing_stats.fetchall()}
            
            # Recent activity
            recent_tasks = await db.execute(text("""
                SELECT COUNT(*) 
                FROM tasks 
                WHERE created_at > NOW() - INTERVAL '1 hour'
            """))
            
            recent_count = recent_tasks.scalar()
            
            return {
                "task_counts": task_counts,
                "instance_processing_stats": instance_stats,
                "recent_tasks_1h": recent_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def get_app_info() -> Dict[str, Any]:
    """Get application information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "worker_poll_interval": settings.worker_poll_interval,
        "task_processing_time": settings.task_processing_time
    }