# FastAPI Error Resolution Implementation Checklist

## Immediate Action Items (Priority 1)

### 1. Global Exception Handler (30 minutes)

```python
# Add to app/main.py after existing imports
from fastapi.exceptions import RequestValidationError
import uuid
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.error(f"Unhandled error {error_id}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again later."
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_id = str(uuid.uuid4())
    logger.warning(f"Validation error {error_id}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "error_id": error_id,
            "details": exc.errors(),
            "message": "Please check your request data format."
        }
    )
```

### 2. Defensive Database Operations (45 minutes)

Add to `app/crud.py`:

```python
def safe_parse_json(json_field, default=None):
    """Safely parse JSON field with default fallback"""
    if json_field is None:
        return default
    try:
        if isinstance(json_field, (dict, list)):
            return json_field
        return json.loads(json_field) if json_field else default
    except (json.JSONDecodeError, TypeError):
        return default

def safe_getattr(obj, attr, default=None):
    """Safely get attribute with None check"""
    if obj is None:
        return default
    return getattr(obj, attr, default)
```

### 3. Enhanced Logging Configuration (15 minutes)

Update `config/logging_config.py`:

```python
# Add structured error logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d"
        }
    },
    "handlers": {
        "error_file": {
            "class": "logging.FileHandler",
            "filename": "logs/errors.log",
            "formatter": "detailed",
            "level": "ERROR"
        }
    },
    "loggers": {
        "": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": True
        }
    }
}
```

## Critical Bug Fixes (Priority 2)

### 4. Fix AttributeError in Grant Conversion (30 minutes)

Update the `convert_db_grant_to_enriched` function in `app/crud.py`:

```python
def convert_db_grant_to_enriched(grant_model: DBGrant) -> EnrichedGrant:
    """Convert database model to Pydantic model with defensive programming"""
    if not grant_model:
        raise ValueError("Grant model cannot be None")

    # Safe extraction with None checks
    research_scores = None
    compliance_scores = None

    # Handle analyses relationship safely
    if hasattr(grant_model, 'analyses') and grant_model.analyses:
        try:
            latest_analysis = max(grant_model.analyses, key=lambda a: a.created_at or datetime.min)
            research_scores = ResearchContextScores(
                sector_relevance=safe_getattr(latest_analysis, 'sector_relevance_score'),
                geographic_relevance=safe_getattr(latest_analysis, 'geographic_relevance_score'),
                operational_alignment=safe_getattr(latest_analysis, 'operational_alignment_score')
            )
        except (AttributeError, ValueError) as e:
            logger.warning(f"Error processing analysis data: {e}")

    # Safe JSON parsing
    keywords = safe_parse_json(grant_model.keywords_json, [])
    categories_project = safe_parse_json(grant_model.categories_project_json, [])

    return EnrichedGrant(
        id=str(grant_model.id),
        title=grant_model.title or "Untitled Grant",
        description=grant_model.description or "",
        funding_amount=safe_getattr(grant_model, 'funding_amount'),
        deadline=safe_getattr(grant_model, 'deadline'),
        eligibility_criteria=safe_getattr(grant_model, 'eligibility_summary_llm'),
        category=safe_getattr(grant_model, 'identified_sector'),
        source_url=safe_getattr(grant_model, 'source_url'),
        source_name=safe_getattr(grant_model, 'source_name'),
        # ... rest of fields with safe_getattr
    )
```

### 5. Frontend Error Handling Enhancement (30 minutes)

Update frontend error handling in `frontend/src/api/apiClient.ts`:

```typescript
// Enhanced error handling with retry logic
const handleApiError = (error: any, endpoint: string): never => {
  console.error(`API Error in ${endpoint}:`, error);

  if (error.response?.status === 422) {
    const validationError = new Error(
      error.response.data?.message ||
        'Invalid request data. Please check your input.'
    );
    validationError.name = 'ValidationError';
    throw validationError;
  }

  if (error.response?.status === 500) {
    const serverError = new Error(
      'Server error occurred. Please try again in a moment.'
    );
    serverError.name = 'ServerError';
    throw serverError;
  }

  throw new Error(error.message || 'An unexpected error occurred');
};

// Add retry logic for failed requests
const apiClientWithRetry = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

apiClientWithRetry.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // Retry logic for 500 errors (max 2 retries)
    if (error.response?.status === 500 && config && !config._retry) {
      config._retry = true;
      config._retryCount = (config._retryCount || 0) + 1;

      if (config._retryCount <= 2) {
        await new Promise((resolve) =>
          setTimeout(resolve, 1000 * config._retryCount)
        );
        return apiClientWithRetry(config);
      }
    }

    return Promise.reject(error);
  }
);
```

## Database Improvements (Priority 3)

### 6. Connection Pool Configuration (15 minutes)

Update `database/session.py`:

```python
def create_database_engine():
    """Create database engine with improved connection pooling"""
    settings = get_settings()

    return create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug,
        connect_args={
            "server_settings": {
                "application_name": "kevin-grant-finder",
            }
        }
    )
```

### 7. Database Session Error Handling (20 minutes)

Update `app/dependencies.py`:

```python
async def get_db_session():
    """Enhanced database session dependency with error handling"""
    if not services.db_sessionmaker:
        logger.error("Database sessionmaker not initialized")
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )

    session = None
    try:
        session = services.db_sessionmaker()
        yield session
        await session.commit()
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(f"Database session error: {str(e)}", exc_info=True)

        # Specific error handling
        if "connection" in str(e).lower():
            raise HTTPException(status_code=503, detail="Database connection error")
        else:
            raise HTTPException(status_code=500, detail="Database operation failed")
    finally:
        if session:
            await session.close()
```

## Testing and Validation (Priority 4)

### 8. Add Error Scenario Tests (45 minutes)

Create `tests/test_error_handling.py`:

```python
import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_500_error_handling(client: AsyncClient):
    """Test that 500 errors return proper error format"""
    with patch('app.crud.get_grants_list', side_effect=Exception("Test error")):
        response = await client.get("/api/grants")
        assert response.status_code == 500
        data = response.json()
        assert "error_id" in data
        assert "message" in data

@pytest.mark.asyncio
async def test_422_validation_error(client: AsyncClient):
    """Test validation error handling"""
    invalid_data = {"min_score": "invalid_score"}
    response = await client.post("/api/grants/search", json=invalid_data)
    assert response.status_code == 422
    data = response.json()
    assert "details" in data or "error" in data

@pytest.mark.asyncio
async def test_database_connection_error(client: AsyncClient):
    """Test database connection error handling"""
    with patch('app.dependencies.get_db_session', side_effect=Exception("Connection failed")):
        response = await client.get("/api/grants")
        assert response.status_code in [500, 503]
```

### 9. Health Check Endpoint Enhancement (20 minutes)

Update the health check in `app/router.py`:

```python
@api_router.get("/system/health-detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db_session)):
    """Comprehensive health check with error detection"""
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "unknown",
        "services": {},
        "errors": []
    }

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        result = await db.execute(text("SELECT COUNT(*) FROM grants"))
        grant_count = result.scalar()
        health_data["services"]["database"] = {
            "status": "healthy",
            "grant_count": grant_count
        }
    except Exception as e:
        health_data["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_data["errors"].append(f"Database: {str(e)}")

    # Overall status
    healthy_services = sum(1 for service in health_data["services"].values()
                          if service.get("status") == "healthy")
    total_services = len(health_data["services"])

    if healthy_services == total_services:
        health_data["status"] = "healthy"
    elif healthy_services > 0:
        health_data["status"] = "degraded"
    else:
        health_data["status"] = "unhealthy"

    status_code = 200 if health_data["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_data)
```

## Implementation Order

### Day 1 (2-3 hours)

1. ✅ Global Exception Handlers
2. ✅ Enhanced Logging Configuration
3. ✅ Basic Defensive Programming

### Day 2 (2-3 hours)

1. ✅ Database Session Error Handling
2. ✅ Connection Pool Configuration
3. ✅ Grant Conversion Bug Fixes

### Day 3 (2-3 hours)

1. ✅ Frontend Error Handling
2. ✅ Health Check Enhancement
3. ✅ Error Scenario Tests

### Day 4 (1-2 hours)

1. ✅ Integration Testing
2. ✅ Error Rate Monitoring
3. ✅ Documentation Updates

## Success Metrics

- **Zero 500 errors** in production after implementation
- **< 2% 422 errors** from validation issues
- **< 500ms average response time** for grant listings
- **> 99% uptime** for health checks

## Rollback Plan

If any implementation causes issues:

1. **Immediate**: Comment out the problematic code section
2. **Database**: Ensure all database changes are in try-catch blocks
3. **Frontend**: Maintain fallback error messages
4. **Logging**: Keep old logs until new system is validated

## Next Steps After Implementation

1. Monitor error logs for 48 hours
2. Analyze error patterns and frequencies
3. Optimize slow queries and operations
4. Implement additional caching if needed
5. Document lessons learned and update procedures
