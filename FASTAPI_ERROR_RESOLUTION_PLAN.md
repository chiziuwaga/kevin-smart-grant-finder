# FastAPI 500/422 Error Resolution Plan

## Executive Summary

This document provides a comprehensive step-by-step plan to diagnose, understand, and permanently resolve recurring FastAPI 500 (Internal Server Error) and 422 (Unprocessable Entity) errors in the Kevin Smart Grant Finder application.

## Table of Contents

1. [Error Analysis and Common Causes](#error-analysis-and-common-causes)
2. [Immediate Diagnostic Steps](#immediate-diagnostic-steps)
3. [First-Order Fixes](#first-order-fixes)
4. [Second-Order Improvements](#second-order-improvements)
5. [Third-Order Preventive Measures](#third-order-preventive-measures)
6. [Implementation Timeline](#implementation-timeline)
7. [Monitoring and Validation](#monitoring-and-validation)

---

## Error Analysis and Common Causes

### 500 Internal Server Error Sources

Based on the codebase analysis, the primary sources of 500 errors are:

1. **AttributeError: 'NoneType' object has no attribute 'X'**

   - Accessing properties on uninitialized database objects
   - Missing relationships between Grant and Analysis models
   - Unhandled None values in scoring calculations

2. **Database Connection Issues**

   - Session lifecycle management problems
   - Connection pool exhaustion
   - Async session handling errors

3. **Pydantic Model Conversion Errors**

   - Converting SQLAlchemy models to Pydantic schemas
   - Missing fields during model mapping
   - Type conversion failures

4. **Service Dependency Failures**
   - Uninitialized Perplexity/Pinecone clients
   - Missing environment variables
   - External API timeouts

### 422 Unprocessable Entity Sources

1. **Schema Validation Failures**

   - Frontend sending data that doesn't match expected schemas
   - Required fields missing from requests
   - Invalid data types (string vs int, etc.)

2. **Date Format Mismatches**

   - Frontend sending dates in different formats
   - Timezone handling inconsistencies

3. **Enum Value Mismatches**
   - Status values not matching defined enums
   - Case sensitivity issues

---

## Immediate Diagnostic Steps

### Step 1: Enhanced Error Logging and Monitoring

```python
# Add to app/main.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback
import uuid

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    error_id = str(uuid.uuid4())

    # Log the full error with context
    logger.error(
        f"Unhandled error {error_id} in {request.method} {request.url}",
        extra={
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )

    # Return user-friendly error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again later.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler"""
    error_id = str(uuid.uuid4())

    logger.warning(
        f"HTTP error {error_id} in {request.method} {request.url}: {exc.status_code} - {exc.detail}",
        extra={
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "error_id": error_id,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handler for 422 errors"""
    error_id = str(uuid.uuid4())

    # Extract detailed validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })

    logger.warning(
        f"Validation error {error_id} in {request.method} {request.url}",
        extra={
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "validation_errors": validation_errors,
            "body": exc.body
        }
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "error_id": error_id,
            "details": validation_errors,
            "message": "The request data is invalid. Please check the specified fields.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Step 2: Database Health Monitoring

```python
# Add to app/router.py
@api_router.get("/system/database-health")
async def check_database_health(db: AsyncSession = Depends(get_db_session)):
    """Comprehensive database health check"""
    health_info = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "unknown",
        "checks": {}
    }

    try:
        # Test basic connectivity
        await db.execute(text("SELECT 1"))
        health_info["checks"]["connectivity"] = "ok"

        # Check table existence
        tables_to_check = ["grants", "analyses", "search_runs", "user_settings"]
        for table in tables_to_check:
            try:
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                health_info["checks"][f"table_{table}"] = {"status": "ok", "count": count}
            except Exception as e:
                health_info["checks"][f"table_{table}"] = {"status": "error", "error": str(e)}

        # Check for orphaned records
        try:
            result = await db.execute(text("""
                SELECT COUNT(*) FROM grants g
                LEFT JOIN analyses a ON g.id = a.grant_id
                WHERE a.grant_id IS NULL
            """))
            orphaned_grants = result.scalar()
            health_info["checks"]["data_integrity"] = {
                "status": "warning" if orphaned_grants > 0 else "ok",
                "orphaned_grants": orphaned_grants
            }
        except Exception as e:
            health_info["checks"]["data_integrity"] = {"status": "error", "error": str(e)}

        health_info["status"] = "healthy"
        return health_info

    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["error"] = str(e)
        raise HTTPException(status_code=503, detail=health_info)
```

### Step 3: Request/Response Validation Middleware

```python
# Add to app/main.py
@app.middleware("http")
async def validate_request_middleware(request: Request, call_next):
    """Middleware to validate and log requests"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # Add request ID to logger context
    request.state.request_id = request_id

    try:
        # Log incoming request
        logger.info(
            f"Request {request_id}: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type")
            }
        )

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Response {request_id}: {response.status_code} in {duration:.3f}s",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration
            }
        )

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request {request_id} failed after {duration:.3f}s: {str(e)}",
            extra={
                "request_id": request_id,
                "duration": duration,
                "error": str(e)
            },
            exc_info=True
        )
        raise
```

---

## First-Order Fixes

### Fix 1: Defensive Database Operations

**Problem**: AttributeError when accessing properties on None objects

**Solution**: Add null checks and default values

```python
# Update app/crud.py
async def get_grant_by_id(db: AsyncSession, grant_id: int) -> Optional[EnrichedGrant]:
    """Get a single grant by ID with defensive programming"""
    try:
        query = select(DBGrant).options(selectinload(DBGrant.analyses)).where(DBGrant.id == grant_id)
        result = await db.execute(query)
        grant_model = result.scalar_one_or_none()

        if not grant_model:
            return None

        # Defensive conversion with null checks
        return convert_db_grant_to_enriched(grant_model)

    except Exception as e:
        logger.error(f"Error fetching grant {grant_id}: {str(e)}", exc_info=True)
        raise

def convert_db_grant_to_enriched(grant_model: DBGrant) -> EnrichedGrant:
    """Convert database model to Pydantic model with defensive programming"""
    try:
        # Safely extract analysis data
        research_scores = None
        compliance_scores = None

        if grant_model.analyses:
            # Take the most recent analysis
            latest_analysis = max(grant_model.analyses, key=lambda a: a.created_at or datetime.min)

            research_scores = ResearchContextScores(
                sector_relevance=getattr(latest_analysis, 'sector_relevance_score', None),
                geographic_relevance=getattr(latest_analysis, 'geographic_relevance_score', None),
                operational_alignment=getattr(latest_analysis, 'operational_alignment_score', None)
            )

            compliance_scores = ComplianceScores(
                business_logic_alignment=getattr(latest_analysis, 'business_logic_alignment_score', None),
                feasibility_score=getattr(latest_analysis, 'feasibility_score', None),
                strategic_synergy=getattr(latest_analysis, 'strategic_synergy_score', None),
                final_weighted_score=getattr(latest_analysis, 'final_score', None)
            )

        # Safely parse JSON fields
        keywords = []
        categories_project = []
        specific_location_mentions = []

        try:
            if grant_model.keywords_json:
                keywords = grant_model.keywords_json if isinstance(grant_model.keywords_json, list) else []
        except (TypeError, ValueError):
            keywords = []

        try:
            if grant_model.categories_project_json:
                categories_project = grant_model.categories_project_json if isinstance(grant_model.categories_project_json, list) else []
        except (TypeError, ValueError):
            categories_project = []

        try:
            if grant_model.specific_location_mentions_json:
                specific_location_mentions = grant_model.specific_location_mentions_json if isinstance(grant_model.specific_location_mentions_json, list) else []
        except (TypeError, ValueError):
            specific_location_mentions = []

        # Create EnrichedGrant with safe defaults
        return EnrichedGrant(
            id=str(grant_model.id),
            title=grant_model.title or "Untitled Grant",
            description=grant_model.description or "No description available",

            # Funding information
            funding_amount=grant_model.funding_amount,
            funding_amount_min=grant_model.funding_amount_min,
            funding_amount_max=grant_model.funding_amount_max,
            funding_amount_exact=grant_model.funding_amount_exact,
            funding_amount_display=grant_model.funding_amount_display,

            # Dates
            deadline=grant_model.deadline,
            deadline_date=grant_model.deadline_date,
            application_open_date=grant_model.application_open_date,

            # Basic fields
            eligibility_criteria=grant_model.eligibility_summary_llm,
            category=grant_model.identified_sector,
            source_url=grant_model.source_url,
            source_name=grant_model.source_name,

            # Enhanced fields
            grant_id_external=grant_model.grant_id_external,
            summary_llm=grant_model.summary_llm,
            eligibility_summary_llm=grant_model.eligibility_summary_llm,
            funder_name=grant_model.funder_name,

            # Lists and complex objects
            keywords=keywords,
            categories_project=categories_project,
            specific_location_mentions=specific_location_mentions,

            # Source details
            source_details=GrantSourceDetails(
                source_name=grant_model.source_name,
                source_url=grant_model.source_url,
                retrieved_at=grant_model.retrieved_at
            ) if grant_model.source_name or grant_model.source_url else None,

            # Contextual information
            identified_sector=grant_model.identified_sector,
            identified_sub_sector=grant_model.identified_sub_sector,
            geographic_scope=grant_model.geographic_scope,

            # Scores
            research_scores=research_scores,
            compliance_scores=compliance_scores,
            overall_composite_score=grant_model.overall_composite_score,
            feasibility_score=grant_model.feasibility_score,

            # JSON fields with safe parsing
            compliance_summary=safe_parse_json(grant_model.compliance_summary_json),
            risk_assessment=safe_parse_json(grant_model.risk_assessment_json),
            raw_source_data=safe_parse_json(grant_model.raw_source_data_json),
            enrichment_log=safe_parse_json(grant_model.enrichment_log_json, default=[])
        )

    except Exception as e:
        logger.error(f"Error converting grant model to enriched: {str(e)}", exc_info=True)
        raise

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
```

### Fix 2: Enhanced Schema Validation

**Problem**: 422 errors from frontend data not matching schemas

**Solution**: Add flexible schemas with better validation

```python
# Update app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Union

class FlexibleGrantSearchFilters(BaseModel):
    """Flexible search filters that handle various input formats"""
    search_text: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    category: Optional[str] = None
    funding_min: Optional[Union[int, float]] = None
    funding_max: Optional[Union[int, float]] = None
    deadline_before: Optional[Union[str, datetime]] = None
    deadline_after: Optional[Union[str, datetime]] = None
    geographic_scope: Optional[str] = None

    @validator('deadline_before', 'deadline_after', pre=True)
    def parse_deadline(cls, v):
        """Parse deadline from various formats"""
        if v is None:
            return None

        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Try different date formats
            for fmt in [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue

            # If no format matches, try ISO format
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")

        raise ValueError(f"Cannot parse date from {type(v)}: {v}")

    @validator('min_score', 'max_score')
    def validate_scores(cls, v):
        """Validate score ranges"""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Scores must be between 0.0 and 1.0")
        return v

class CreateSearchRunRequest(BaseModel):
    """Request model for creating search runs"""
    search_query: Optional[str] = None
    search_filters: Optional[Dict[str, Any]] = None
    run_type: Optional[str] = Field("manual", regex="^(manual|automated|scheduled)$")

    @validator('search_filters', pre=True)
    def validate_search_filters(cls, v):
        """Validate search filters"""
        if v is None:
            return {}

        if not isinstance(v, dict):
            raise ValueError("search_filters must be a dictionary")

        return v
```

### Fix 3: Connection Pool and Session Management

**Problem**: Database connection issues causing 500 errors

**Solution**: Improve connection management

```python
# Update database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

def create_engine_with_retry():
    """Create database engine with proper connection pooling"""
    database_url = get_settings().database_url

    # Enhanced connection pool settings
    engine = create_async_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,  # Number of connections to keep persistently
        max_overflow=20,  # Additional connections that can be created
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=get_settings().debug,  # Log SQL queries in debug mode
        connect_args={
            "server_settings": {
                "application_name": "kevin-grant-finder",
            }
        }
    )

    return engine

# Update app/dependencies.py
async def get_db_session():
    """Dependency to get database session with proper error handling"""
    if not services.db_sessionmaker:
        logger.error("Database sessionmaker not initialized")
        raise HTTPException(
            status_code=503,
            detail="Database not available. Please try again later."
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
        raise HTTPException(
            status_code=500,
            detail="Database operation failed. Please try again."
        )
    finally:
        if session:
            await session.close()
```

---

## Second-Order Improvements

### Improvement 1: Request/Response Caching

```python
# Add caching to reduce database load
from functools import lru_cache
import redis
import json

class CacheManager:
    def __init__(self):
        self.redis_client = None
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
        except Exception as e:
            logger.warning(f"Redis not available: {e}")

    async def get_cached_grants(self, cache_key: str) -> Optional[List[Dict]]:
        """Get cached grants data"""
        if not self.redis_client:
            return None

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")

        return None

    async def cache_grants(self, cache_key: str, data: List[Dict], ttl: int = 300):
        """Cache grants data"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
```

### Improvement 2: API Rate Limiting

```python
# Add rate limiting to prevent abuse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add to endpoints
@api_router.get("/grants")
@limiter.limit("30/minute")  # 30 requests per minute
async def list_grants(request: Request, ...):
    # existing code
```

### Improvement 3: Background Task Processing

```python
# Add background tasks for heavy operations
from fastapi import BackgroundTasks

async def process_grant_analysis_background(grant_id: int):
    """Process grant analysis in background"""
    try:
        # Heavy analysis operations
        async with services.db_sessionmaker() as session:
            grant = await crud.get_grant_by_id(session, grant_id)
            if grant:
                # Perform analysis
                await crud.analyze_grant(session, grant)
    except Exception as e:
        logger.error(f"Background analysis failed for grant {grant_id}: {e}")

@api_router.post("/grants/{grant_id}/analyze")
async def trigger_grant_analysis(
    grant_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Trigger grant analysis as background task"""
    # Add background task
    background_tasks.add_task(process_grant_analysis_background, grant_id)

    return {"message": "Analysis started", "grant_id": grant_id}
```

---

## Third-Order Preventive Measures

### Measure 1: Comprehensive Testing Framework

```python
# tests/test_error_scenarios.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_grant_with_missing_data(client: AsyncClient):
    """Test handling of grants with missing data"""
    # Create grant with minimal data
    response = await client.get("/api/grants/999999")  # Non-existent ID
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert "error_id" in data

@pytest.mark.asyncio
async def test_invalid_search_filters(client: AsyncClient):
    """Test handling of invalid search filters"""
    invalid_filters = {
        "min_score": "invalid",  # Should be float
        "deadline_before": "not-a-date"  # Should be valid date
    }

    response = await client.post("/api/grants/search", json=invalid_filters)
    assert response.status_code == 422

    data = response.json()
    assert "validation_errors" in data or "details" in data

@pytest.mark.asyncio
async def test_database_connection_failure(client: AsyncClient, monkeypatch):
    """Test handling of database connection failures"""
    # Mock database failure
    async def mock_get_db_session():
        raise Exception("Database connection failed")

    monkeypatch.setattr("app.dependencies.get_db_session", mock_get_db_session)

    response = await client.get("/api/grants")
    assert response.status_code == 500

    data = response.json()
    assert "error_id" in data
```

### Measure 2: Performance Monitoring

```python
# Add performance monitoring
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def monitor_performance(operation_name: str):
    """Context manager for monitoring operation performance"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if duration > 1.0:  # Log slow operations
            logger.warning(
                f"Slow operation detected: {operation_name} took {duration:.2f}s",
                extra={
                    "operation": operation_name,
                    "duration": duration,
                    "performance_alert": True
                }
            )

# Usage in endpoints
@api_router.get("/grants")
async def list_grants(...):
    async with monitor_performance("list_grants"):
        # existing code
```

### Measure 3: Health Check Automation

```python
# Add automated health checks
import asyncio
from datetime import timedelta

class HealthMonitor:
    def __init__(self):
        self.last_check = None
        self.health_status = "unknown"

    async def run_periodic_health_checks(self):
        """Run health checks every 5 minutes"""
        while True:
            try:
                await self.perform_health_check()
                await asyncio.sleep(300)  # 5 minutes
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute on error

    async def perform_health_check(self):
        """Perform comprehensive health check"""
        checks = {
            "database": await self.check_database(),
            "external_apis": await self.check_external_apis(),
            "disk_space": await self.check_disk_space(),
            "memory": await self.check_memory_usage()
        }

        self.last_check = datetime.utcnow()
        self.health_status = "healthy" if all(checks.values()) else "degraded"

        # Alert on failures
        failed_checks = [k for k, v in checks.items() if not v]
        if failed_checks:
            logger.error(f"Health check failures: {failed_checks}")

# Start health monitor on app startup
@app.on_event("startup")
async def start_health_monitor():
    health_monitor = HealthMonitor()
    asyncio.create_task(health_monitor.run_periodic_health_checks())
```

---

## Implementation Timeline

### Phase 1 (Week 1): Immediate Fixes

- [ ] Implement global exception handlers
- [ ] Add defensive database operations
- [ ] Enhance schema validation
- [ ] Improve connection pool settings

### Phase 2 (Week 2): Error Prevention

- [ ] Add request/response caching
- [ ] Implement rate limiting
- [ ] Add background task processing
- [ ] Enhance logging and monitoring

### Phase 3 (Week 3): Long-term Stability

- [ ] Comprehensive testing framework
- [ ] Performance monitoring
- [ ] Automated health checks
- [ ] Documentation and training

### Phase 4 (Week 4): Validation and Optimization

- [ ] Load testing
- [ ] Error rate analysis
- [ ] Performance optimization
- [ ] Final documentation

---

## Monitoring and Validation

### Success Metrics

1. **Error Rate Reduction**: Target < 1% error rate
2. **Response Time**: Average < 500ms for grant listings
3. **Uptime**: > 99.5% availability
4. **User Experience**: Zero user-facing 500 errors

### Monitoring Tools

1. **Application Logs**: Structured logging with error IDs
2. **Performance Metrics**: Response times and throughput
3. **Error Tracking**: Detailed error analysis and trends
4. **Health Dashboards**: Real-time system status

### Validation Steps

1. Run comprehensive test suite
2. Perform load testing with realistic scenarios
3. Monitor error logs for patterns
4. Validate frontend error handling
5. Test recovery scenarios

---

## Conclusion

This plan provides a systematic approach to resolving FastAPI errors through:

1. **Immediate fixes** for current error sources
2. **Preventive measures** to avoid future errors
3. **Monitoring systems** to detect issues early
4. **Recovery mechanisms** to handle failures gracefully

By implementing these changes incrementally, the application will achieve high reliability and provide a robust user experience.
