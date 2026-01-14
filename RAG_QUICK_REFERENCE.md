# RAG System Quick Reference

## File Locations

```
services/
  application_rag.py          # RAG service (431 lines)

tasks/
  __init__.py                 # Celery configuration (30 lines)
  application_generator.py    # Application generator task (606 lines)
```

## Key Classes & Functions

### ApplicationRAGService (`services/application_rag.py`)

```python
from services.application_rag import get_rag_service

rag_service = get_rag_service()
```

**Main Methods:**
- `generate_and_store_embeddings(db, user_id, business_profile_id)` - Create embeddings
- `retrieve_relevant_context(user_id, query, top_k=5)` - Get relevant chunks
- `update_embeddings(db, user_id, business_profile_id)` - Refresh embeddings
- `delete_user_embeddings(user_id)` - Clean up user data
- `get_embedding_stats(user_id)` - View statistics

### Celery Task (`tasks/application_generator.py`)

```python
from tasks.application_generator import generate_grant_application

# Trigger task
task = generate_grant_application.delay(
    user_id=1,
    grant_id=123,
    business_profile_id=1
)

# Check status
print(task.status)

# Get result (blocking)
result = task.get(timeout=600)
```

## Application Sections Generated

1. **Executive Summary** (200-300 words)
2. **Needs Statement** (300-400 words)
3. **Project Description** (400-600 words)
4. **Budget Narrative** (300-400 words)
5. **Organizational Capacity** (300-400 words)
6. **Impact Statement** (300-400 words)

## Configuration

### Environment Variables

```bash
# Required
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=grantcluster
DEEPSEEK_API_KEY=your_key
RESEND_API_KEY=your_key
REDIS_URL=redis://localhost:6379/0

# Optional
DEEPSEEK_API_BASE=https://api.deepseek.com
FROM_EMAIL=noreply@grantfinder.com
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Dependencies

```bash
pip install pinecone-client celery redis resend
```

## Starting Services

### Celery Worker

```bash
# Linux/Mac
celery -A tasks worker --loglevel=info

# Windows
celery -A tasks worker --loglevel=info --pool=solo
```

### Redis (if not running)

```bash
# Linux
redis-server

# Mac
brew services start redis

# Windows (WSL or download from Redis website)
```

## Common Operations

### 1. Generate Embeddings on Profile Creation

```python
from services.application_rag import get_rag_service

async def on_profile_created(db, user_id, profile_id):
    rag_service = get_rag_service()
    result = await rag_service.generate_and_store_embeddings(
        db=db,
        user_id=user_id,
        business_profile_id=profile_id
    )
    return result
```

### 2. Update Embeddings on Profile Edit

```python
async def on_profile_updated(db, user_id, profile_id):
    rag_service = get_rag_service()
    result = await rag_service.update_embeddings(
        db=db,
        user_id=user_id,
        business_profile_id=profile_id
    )
    return result
```

### 3. Generate Application

```python
from tasks.application_generator import generate_grant_application

def start_application_generation(user_id, grant_id, profile_id):
    task = generate_grant_application.delay(
        user_id=user_id,
        grant_id=grant_id,
        business_profile_id=profile_id
    )
    return {"task_id": str(task.id), "status": "processing"}
```

### 4. Check Task Status

```python
from celery.result import AsyncResult

def check_task_status(task_id):
    task = AsyncResult(task_id)
    return {
        "status": task.status,
        "ready": task.ready(),
        "successful": task.successful() if task.ready() else None
    }
```

### 5. Get Application Result

```python
from celery.result import AsyncResult

def get_application_result(task_id):
    task = AsyncResult(task_id)
    if task.ready():
        if task.successful():
            return task.result
        else:
            return {"error": str(task.info)}
    return {"status": "processing"}
```

## API Endpoint Template

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from tasks.application_generator import generate_grant_application

router = APIRouter(prefix="/api/applications", tags=["applications"])

@router.post("/generate/{grant_id}")
async def generate_application(
    grant_id: int,
    user = Depends(get_current_user),
    db = Depends(get_db)
):
    # Check limits
    if user.applications_used >= user.applications_limit:
        raise HTTPException(403, "Limit reached")

    # Check profile
    if not user.business_profile:
        raise HTTPException(400, "Profile required")

    # Ensure embeddings exist
    profile = user.business_profile
    if not profile.embeddings_generated_at:
        rag_service = get_rag_service()
        await rag_service.generate_and_store_embeddings(
            db, user.id, profile.id
        )

    # Start task
    task = generate_grant_application.delay(
        user_id=user.id,
        grant_id=grant_id,
        business_profile_id=profile.id
    )

    return {"task_id": task.id, "status": "processing"}

@router.get("/status/{task_id}")
async def get_generation_status(task_id: str):
    task = AsyncResult(task_id)
    return {
        "status": task.status,
        "ready": task.ready(),
        "result": task.result if task.ready() and task.successful() else None
    }
```

## Monitoring Commands

```bash
# View active tasks
celery -A tasks inspect active

# View registered tasks
celery -A tasks inspect registered

# View worker stats
celery -A tasks inspect stats

# Purge all tasks
celery -A tasks purge

# View task history
celery -A tasks events
```

## Troubleshooting

### Issue: "Pinecone API key not configured"
**Solution:** Set `PINECONE_API_KEY` in `.env`

### Issue: Task timeout
**Solution:** Increase timeout in `tasks/__init__.py`:
```python
task_time_limit=1200  # 20 minutes
```

### Issue: Embeddings not found
**Solution:** Generate embeddings first:
```python
await rag_service.generate_and_store_embeddings(db, user_id, profile_id)
```

### Issue: Usage limit reached
**Solution:** Check and update user limits:
```python
user.applications_limit = 50  # Increase limit
await db.commit()
```

### Issue: Email not sent
**Solution:** Check Resend API key and email configuration

## Performance Metrics

| Operation | Time | Tokens | Cost (est.) |
|-----------|------|--------|-------------|
| Generate embeddings | 2-5s | 1000-3000 | $0.001-0.003 |
| Retrieve context | <1s | 0 | $0 |
| Generate application | 30-60s | 5000-8000 | $0.05-0.10 |
| Update embeddings | 3-6s | 1000-3000 | $0.001-0.003 |

## Database Models Used

### BusinessProfile
- `narrative_text` (Text, max 2000 chars)
- `vector_embeddings_id` (String, Pinecone namespace)
- `embeddings_generated_at` (DateTime)

### GeneratedApplication
- `generated_content` (Text, full application)
- `sections` (JSON, individual sections)
- `status` (Enum, generation status)
- `tokens_used` (Integer)
- `generation_time_seconds` (Float)

### User
- `applications_used` (Integer, counter)
- `applications_limit` (Integer, monthly limit)

## Security Checklist

- [ ] User namespace isolation enabled
- [ ] API keys in environment variables
- [ ] User ID verified in all operations
- [ ] Rate limiting implemented
- [ ] Usage limits enforced
- [ ] Error messages don't expose sensitive data

## Testing Checklist

- [ ] Text chunking works correctly
- [ ] Embeddings generate successfully
- [ ] Context retrieval returns relevant results
- [ ] Application generation completes
- [ ] Email notifications send
- [ ] Usage counter increments
- [ ] Error handling works
- [ ] Task retries on failure

## Production Deployment

1. **Set environment variables** in production
2. **Start Celery workers**: `celery -A tasks worker -c 4 --loglevel=info`
3. **Monitor with Flower**: `celery -A tasks flower`
4. **Set up Redis persistence**
5. **Configure Pinecone production index**
6. **Enable logging to file**
7. **Set up monitoring alerts**
8. **Test with real data**

## Contact

For support, check:
- Logs: `tail -f logs/celery.log`
- Celery tasks: `celery -A tasks inspect active`
- Pinecone dashboard
- Resend dashboard
- DeepSeek API usage
