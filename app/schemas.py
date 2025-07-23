from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ConversationBase(BaseModel):
    content: str
    status: Optional[str] = "active"

class ConversationCreate(ConversationBase):
    pass

class ConversationUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None

class Conversation(ConversationBase):
    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    conversations: Optional[List[ConversationCreate]] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class Task(TaskBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    conversations: List[Conversation] = []
    
    class Config:
        from_attributes = True

class TaskList(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    conversation_count: int
    
    class Config:
        from_attributes = True