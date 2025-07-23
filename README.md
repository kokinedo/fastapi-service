# Task Management Service

A FastAPI-based service that manages tasks and processes them asynchronously in the background. Each task has a one-to-many relationship with conversations, and the service is designed to run with multiple instances safely.

## Features

- **Task Management**: Full CRUD operations for tasks
- **Conversation Management**: One-to-many relationship between tasks and conversations
- **Background Processing**: Asynchronous task processing that takes 6-7 seconds per task
- **Multi-instance Support**: Safe concurrent processing across multiple service instances
- **Database Backend**: PostgreSQL with SQLAlchemy ORM
- **REST API**: FastAPI with automatic OpenAPI documentation

## Architecture

### Data Model

- **Task**: Main entity with fields for title, description, status, timestamps, and processing metadata
- **Conversation**: Related entity with content, status, and timestamps, linked to tasks via foreign key

### Concurrency Safety

The service handles multiple instances safely using:

1. **Database-level Locking**: Uses PostgreSQL's `SELECT FOR UPDATE SKIP LOCKED` to ensure only one instance can claim a pending task
2. **Instance Identification**: Each service instance has a unique UUID to track which instance is processing which task
3. **Atomic Operations**: Task status updates are atomic and include instance ID validation

### Background Processing

- Each instance runs a background worker that continuously polls for pending tasks
- Tasks are processed one at a time per instance
- Processing includes updating all related conversations
- Failed tasks are marked appropriately and can be retried

## API Endpoints

### Tasks
- `POST /tasks/` - Create a new task with optional conversations
- `GET /tasks/` - List all tasks with conversation counts
- `GET /tasks/{task_id}` - Get a specific task with all conversations
- `PUT /tasks/{task_id}` - Update a task
- `DELETE /tasks/{task_id}` - Delete a task and all its conversations

### Conversations
- `POST /tasks/{task_id}/conversations/` - Create a conversation for a task
- `GET /tasks/{task_id}/conversations/` - Get all conversations for a task
- `PUT /conversations/{conversation_id}` - Update a conversation

### System
- `GET /health` - Health check endpoint
- `GET /status` - Service status including worker information

## Running the Service

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database on port 5432
   - First service instance on port 12000
   - Second service instance on port 12001

2. **View logs**:
   ```bash
   docker-compose logs -f
   ```

3. **Stop services**:
   ```bash
   docker-compose down
   ```

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL**:
   ```bash
   docker run -d --name postgres \
     -e POSTGRES_USER=user \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=taskdb \
     -p 5432:5432 \
     postgres:15
   ```

3. **Set environment variable**:
   ```bash
   export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/taskdb
   ```

4. **Run the service**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Testing the Service

### Example Usage

1. **Create a task with conversations**:
   ```bash
   curl -X POST "http://localhost:12000/tasks/" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Process customer feedback",
       "description": "Analyze and respond to customer feedback",
       "conversations": [
         {"content": "Customer says the app is slow"},
         {"content": "Customer wants new features"}
       ]
     }'
   ```

2. **List all tasks**:
   ```bash
   curl "http://localhost:12000/tasks/"
   ```

3. **Check service status**:
   ```bash
   curl "http://localhost:12000/status"
   ```

### Multi-instance Testing

To verify that multiple instances work correctly:

1. Create several tasks using either instance
2. Monitor the logs to see which instance processes each task
3. Verify that no task is processed by multiple instances
4. Check that conversations are updated when tasks complete

## How Multi-instance Concurrency Works

### Distributed Locking Mechanism

1. **Task Claiming**: When a worker looks for the next task, it uses an atomic SQL operation:
   ```sql
   UPDATE tasks 
   SET status = 'processing', 
       processing_instance_id = :instance_id,
       updated_at = NOW()
   WHERE id = (
       SELECT id FROM tasks 
       WHERE status = 'pending' 
       ORDER BY created_at ASC 
       FOR UPDATE SKIP LOCKED 
       LIMIT 1
   )
   ```

2. **SKIP LOCKED**: This PostgreSQL feature ensures that if one instance is examining a row, other instances skip it entirely rather than waiting

3. **Instance Validation**: When completing or failing a task, the service verifies that the current instance is the one that claimed the task

4. **Atomic Updates**: All status changes are atomic and include instance ID validation to prevent race conditions

### Benefits

- **No External Dependencies**: Uses database features for coordination
- **Fault Tolerant**: If an instance crashes, tasks remain in "processing" state and can be manually reset or handled by monitoring
- **Scalable**: Can easily add more instances without configuration changes
- **Simple**: No complex distributed locking mechanisms or message queues required

## Database Schema

```sql
-- Tasks table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_instance_id VARCHAR(255)
);

-- Conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql+asyncpg://user:password@localhost:5432/taskdb`)

## Monitoring and Troubleshooting

- Check service health: `GET /health`
- View service status: `GET /status`
- Monitor logs for task processing information
- Database queries can be monitored through SQLAlchemy's echo feature (enabled in development)

## Future Enhancements

- Add task retry mechanisms for failed tasks
- Implement task priorities
- Add metrics and monitoring endpoints
- Support for task scheduling
- WebSocket notifications for real-time updates

## Quick Reference: Common Commands

### Start all services (DB + multiple FastAPI instances)
```bash
docker-compose up -d
```

### Check that services are running
```bash
docker-compose ps
```

### Check health and status endpoints for both instances
```bash
curl http://localhost:12000/health
curl http://localhost:12001/health

curl http://localhost:12000/status
curl http://localhost:12001/status
```

### Create a task with multiple conversations
```bash
curl -X POST http://localhost:12000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Task",
    "description": "Test Description",
    "conversations": [
      {"content": "Conversation 1"},
      {"content": "Conversation 2"}
    ]
  }'
```

### List all tasks
```bash
curl http://localhost:12000/tasks/
```

### Get a specific task (replace 1 with your task ID)
```bash
curl http://localhost:12000/tasks/1
```

### Update a task
```bash
curl -X PUT http://localhost:12000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "description": "Updated Description"}'
```

### Delete a task
```bash
curl -X DELETE http://localhost:12000/tasks/1
```

### Create a conversation for a task
```bash
curl -X POST http://localhost:12000/tasks/1/conversations/ \
  -H "Content-Type: application/json" \
  -d '{"content": "New conversation"}'
```

### Get all conversations for a task
```bash
curl http://localhost:12000/tasks/1/conversations/
```

### Update a conversation (replace 1 with conversation ID)
```bash
curl -X PUT http://localhost:12000/conversations/1 \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated conversation"}'
```

### View logs (to monitor background processing and concurrency)
```bash
docker-compose logs -f
```

### Stop all services
```bash
docker-compose down
```