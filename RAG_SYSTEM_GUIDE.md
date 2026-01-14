# RAG System Integration Guide

## Overview
This guide explains the RAG (Retrieval-Augmented Generation) system for business profile embeddings and AI-powered grant application generation.

## Components Created

### 1. `services/application_rag.py` - RAG Service (431 lines)
Manages vector embeddings for business profiles using Pinecone and DeepSeek.

**Key Features:**
- Business profile text chunking (500 chars/chunk with 50 char overlap)
- Embedding generation using DeepSeek API
- Vector storage in Pinecone with user namespace isolation
- Relevant context retrieval for grant applications
- Automatic embedding updates when profiles change
- 2000 character limit enforcement for narrative_text

**Main Methods:**
- `generate_and_store_embeddings()` - Create embeddings for business profile
- `retrieve_relevant_context()` - Get top-k relevant chunks for a grant query
- `update_embeddings()` - Refresh embeddings when profile changes
- `delete_user_embeddings()` - Clean up user data
- `get_embedding_stats()` - View embedding statistics

### 2. `tasks/application_generator.py` - Celery Task (606 lines)
Celery task for generating comprehensive grant applications.

**Key Features:**
- Async/await pattern for efficient execution
- RAG-powered context retrieval
- Six application sections generated:
  - Executive Summary (200-300 words)
  - Needs Statement (300-400 words)
  - Project Description (400-600 words)
  - Budget Narrative (300-400 words)
  - Organizational Capacity (300-400 words)
  - Impact Statement (300-400 words)
- Automatic usage tracking (applications_used counter)
- Email notifications via Resend
- Comprehensive error handling and retry logic
- Token usage tracking

### 3. `tasks/__init__.py` - Celery Configuration (30 lines)
Initializes Celery app with proper configuration.

**Configuration:**
- Broker: Redis (from REDIS_URL or CELERY_BROKER_URL)
- Backend: Redis (from REDIS_URL or CELERY_RESULT_BACKEND)
- Task timeout: 10 minutes (600s)
- Soft timeout: 9 minutes (540s)
- JSON serialization

## Setup Instructions

### 1. Environment Variables
Ensure these are set in your `.env` file:

```bash
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=grantcluster

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# Resend Email
RESEND_API_KEY=your_resend_api_key
FROM_EMAIL=noreply@grantfinder.com

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0  # Optional, defaults to REDIS_URL
CELERY_RESULT_BACKEND=redis://localhost:6379/0  # Optional, defaults to REDIS_URL
```

### 2. Install Dependencies

```bash
pip install pinecone-client celery redis resend
```

Add to `requirements.txt`:
```
pinecone-client>=3.0.0
celery>=5.3.0
redis>=5.0.0
resend>=0.8.0
```

### 3. Start Celery Worker

```bash
# From project root
celery -A tasks worker --loglevel=info
```

For Windows:
```bash
celery -A tasks worker --loglevel=info --pool=solo
```

### 4. Pinecone Index Setup

The index will be created automatically on first use, but you can create it manually:

```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="your_api_key")
pc.create_index(
    name="grantcluster",
    dimension=1536,  # DeepSeek embeddings dimension
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)
```

## Usage Examples

### 1. Generate Embeddings for Business Profile

```python
from services.application_rag import get_rag_service
from database.session import get_db

async def generate_embeddings_example():
    async with get_db() as db:
        rag_service = get_rag_service()

        result = await rag_service.generate_and_store_embeddings(
            db=db,
            user_id=1,
            business_profile_id=1
        )

        print(f"Created {result['chunks_created']} chunks")
        print(f"Stored {result['embeddings_stored']} embeddings")
```

### 2. Retrieve Relevant Context

```python
from services.application_rag import get_rag_service

async def retrieve_context_example():
    rag_service = get_rag_service()

    grant_query = "Technology innovation grants for small businesses"

    context_chunks = await rag_service.retrieve_relevant_context(
        user_id=1,
        query=grant_query,
        top_k=5
    )

    for chunk in context_chunks:
        print(f"Relevance: {chunk['score']:.2f}")
        print(f"Text: {chunk['text']}\n")
```

### 3. Generate Grant Application (Celery Task)

```python
from tasks.application_generator import generate_grant_application

# Trigger async task
task = generate_grant_application.delay(
    user_id=1,
    grant_id=123,
    business_profile_id=1
)

# Check task status
print(f"Task ID: {task.id}")
print(f"Status: {task.status}")

# Get result (blocking)
result = task.get(timeout=600)
print(f"Application ID: {result['application_id']}")
print(f"Tokens used: {result['tokens_used']}")
```

### 4. Update Embeddings When Profile Changes

```python
from services.application_rag import get_rag_service

async def update_embeddings_example():
    async with get_db() as db:
        rag_service = get_rag_service()

        # User updated their profile
        result = await rag_service.update_embeddings(
            db=db,
            user_id=1,
            business_profile_id=1
        )

        print(f"Update successful: {result['success']}")
```

## API Integration

### FastAPI Endpoint Example

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from tasks.application_generator import generate_grant_application
from database.session import get_db
from database.models import User

router = APIRouter()

@router.post("/applications/generate")
async def generate_application_endpoint(
    grant_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate grant application using RAG."""

    # Check usage limits
    if user.applications_used >= user.applications_limit:
        raise HTTPException(
            status_code=403,
            detail="Monthly application limit reached"
        )

    # Get business profile
    profile = user.business_profile
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Business profile required"
        )

    # Generate embeddings if not exists
    if not profile.embeddings_generated_at:
        from services.application_rag import get_rag_service
        rag_service = get_rag_service()
        await rag_service.generate_and_store_embeddings(
            db=db,
            user_id=user.id,
            business_profile_id=profile.id
        )

    # Trigger Celery task
    task = generate_grant_application.delay(
        user_id=user.id,
        grant_id=grant_id,
        business_profile_id=profile.id
    )

    return {
        "message": "Application generation started",
        "task_id": task.id,
        "status": "processing"
    }
```

## Database Schema Integration

The system uses these existing models from `database/models.py`:

### BusinessProfile
- `narrative_text` - Long-form business description (max 2000 chars)
- `vector_embeddings_id` - Pinecone namespace reference
- `embeddings_generated_at` - Timestamp of last embedding generation

### GeneratedApplication
- `generated_content` - Full application text
- `sections` - JSON with individual sections
- `status` - ApplicationGenerationStatus enum
- `model_used` - AI model identifier
- `generation_time_seconds` - Processing time
- `tokens_used` - Token consumption tracking

### User
- `applications_used` - Counter for usage tracking
- `applications_limit` - Monthly limit

## Error Handling

### Common Errors and Solutions

1. **Pinecone API Key Missing**
   - Error: "Pinecone API key not configured"
   - Solution: Set PINECONE_API_KEY in .env

2. **Narrative Text Too Long**
   - Error: "Narrative text exceeds 2000 chars"
   - Solution: Automatically truncated with warning logged

3. **No Embeddings Generated**
   - Error: "No text content to embed"
   - Solution: Ensure business profile has content

4. **Task Timeout**
   - Error: Task exceeds 10 minute limit
   - Solution: Check DeepSeek API performance, reduce top_k

5. **Usage Limit Reached**
   - Error: "Monthly application limit reached"
   - Solution: Upgrade subscription or wait for reset

## Performance Considerations

### Embedding Generation
- Time: ~2-5 seconds for typical business profile
- Tokens: ~1000-3000 tokens depending on profile length
- Chunks: Typically 3-8 chunks per profile

### Application Generation
- Time: ~30-60 seconds for complete application
- Tokens: ~5000-8000 tokens for all six sections
- Cost: ~$0.05-0.10 per application (DeepSeek pricing)

### Scaling
- Celery workers can be scaled horizontally
- Pinecone supports millions of vectors
- Redis can handle thousands of tasks per second

## Monitoring

### Celery Monitoring

```bash
# View active tasks
celery -A tasks inspect active

# View registered tasks
celery -A tasks inspect registered

# View stats
celery -A tasks inspect stats
```

### Logging

All components use Python's logging module:

```python
import logging

# Set log level
logging.basicConfig(level=logging.INFO)

# View RAG logs
logger = logging.getLogger('services.application_rag')
logger.setLevel(logging.DEBUG)
```

### Pinecone Stats

```python
from services.application_rag import get_rag_service

async def check_stats():
    rag_service = get_rag_service()
    stats = await rag_service.get_embedding_stats(user_id=1)
    print(f"Vectors: {stats['vector_count']}")
    print(f"Has embeddings: {stats['has_embeddings']}")
```

## Testing

### Unit Tests

```python
import pytest
from services.application_rag import ApplicationRAGService

@pytest.mark.asyncio
async def test_text_chunking():
    rag_service = ApplicationRAGService()

    text = "Lorem ipsum " * 100
    chunks = rag_service._chunk_text(text, chunk_size=100)

    assert len(chunks) > 1
    assert all(len(chunk) <= 150 for chunk in chunks)  # Including overlap

@pytest.mark.asyncio
async def test_generate_embeddings(db_session):
    rag_service = ApplicationRAGService()

    result = await rag_service.generate_and_store_embeddings(
        db=db_session,
        user_id=1,
        business_profile_id=1
    )

    assert result['success'] == True
    assert result['chunks_created'] > 0
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_application_generation(db_session):
    from tasks.application_generator import _generate_application_async

    result = await _generate_application_async(
        user_id=1,
        grant_id=1,
        business_profile_id=1
    )

    assert result['success'] == True
    assert 'application_id' in result
    assert result['sections_generated'] == 6
```

## Security Considerations

1. **User Namespace Isolation**: Each user's embeddings are stored in a separate Pinecone namespace
2. **Access Control**: All operations require user_id, enforcing row-level security
3. **API Keys**: All API keys should be stored in environment variables, never in code
4. **Data Privacy**: Embeddings contain semantic information about business profiles
5. **Rate Limiting**: Implement rate limiting on application generation endpoints

## Maintenance

### Regular Tasks

1. **Monitor Pinecone Usage**
   - Check vector count
   - Monitor query performance
   - Review storage costs

2. **Clean Up Old Embeddings**
   - Delete embeddings for deleted users
   - Archive inactive user data

3. **Update Models**
   - Monitor DeepSeek API updates
   - Test new embedding models
   - Regenerate embeddings if model changes

4. **Review Generated Applications**
   - Collect user feedback
   - Improve prompts based on results
   - A/B test different generation strategies

## Future Enhancements

1. **Multi-Language Support**: Generate applications in multiple languages
2. **Template Customization**: Allow users to customize section templates
3. **Collaborative Editing**: Real-time collaborative editing of generated applications
4. **Version History**: Track changes and revisions to applications
5. **PDF Export**: Export applications as formatted PDFs
6. **Grant Matching Score**: Show how well business profile matches grant requirements
7. **Feedback Loop**: Use awarded/rejected applications to improve generation

## Support

For issues or questions:
1. Check logs: `tail -f logs/celery.log`
2. Review Celery task status: `celery -A tasks inspect active`
3. Check Pinecone dashboard for vector stats
4. Monitor DeepSeek API usage and quotas
5. Review email delivery in Resend dashboard

## License
Proprietary - Grant Finder Platform
