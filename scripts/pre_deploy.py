#!/usr/bin/env python3
"""
Pre-deploy health check for Render.
Verifies environment, database connectivity, and required configuration.
Run before alembic migrations: python scripts/pre_deploy.py && alembic upgrade head
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pre_deploy")

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
]

RECOMMENDED_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "RESEND_API_KEY",
    "REDIS_URL",
    "JWT_SECRET_KEY",
]


def check_env_vars():
    """Check required and recommended environment variables."""
    missing_required = []
    missing_recommended = []

    for var in REQUIRED_ENV_VARS:
        val = os.getenv(var)
        if not val:
            missing_required.append(var)
        else:
            # Mask the value for logging
            masked = val[:8] + "..." if len(val) > 8 else "***"
            logger.info(f"  {var} = {masked}")

    for var in RECOMMENDED_ENV_VARS:
        val = os.getenv(var)
        if not val:
            missing_recommended.append(var)
        else:
            masked = val[:8] + "..." if len(val) > 8 else "***"
            logger.info(f"  {var} = {masked}")

    if missing_required:
        logger.error(f"MISSING REQUIRED env vars: {', '.join(missing_required)}")
        logger.error("These must be set in the Render dashboard under Environment.")
        return False

    if missing_recommended:
        logger.warning(f"Missing recommended env vars: {', '.join(missing_recommended)}")
        logger.warning("Some features will be degraded without these.")

    return True


def check_database():
    """Test database connectivity using DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set - cannot check database")
        return False

    # Convert to sync driver for this check
    sync_url = db_url
    if "postgresql+asyncpg://" in sync_url:
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")
    elif "postgres://" in sync_url:
        sync_url = sync_url.replace("postgres://", "postgresql://")

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(sync_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("  Database connection: OK")

            # Check pgvector extension
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            if result.fetchone():
                logger.info("  pgvector extension: ENABLED")
            else:
                logger.warning("  pgvector extension: NOT FOUND (will be created by migration)")

        engine.dispose()
        return True

    except Exception as e:
        logger.error(f"  Database connection FAILED: {e}")
        return False


def check_redis():
    """Test Redis connectivity."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not set - Celery tasks will not work")
        return True  # Not blocking

    try:
        import redis
        r = redis.from_url(redis_url, socket_timeout=5)
        r.ping()
        logger.info("  Redis connection: OK")
        return True
    except Exception as e:
        logger.warning(f"  Redis connection failed: {e} (non-blocking)")
        return True  # Non-blocking


def check_frontend_build():
    """Check if frontend is built."""
    build_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "build")
    if os.path.exists(os.path.join(build_path, "index.html")):
        logger.info("  Frontend build: OK")
        return True
    else:
        logger.warning("  Frontend build: NOT FOUND (will be built during deploy)")
        return True  # Non-blocking - buildCommand handles this


def main():
    logger.info("=" * 60)
    logger.info("PRE-DEPLOY HEALTH CHECK")
    logger.info("=" * 60)

    all_ok = True

    logger.info("\n[1/4] Checking environment variables...")
    if not check_env_vars():
        all_ok = False

    logger.info("\n[2/4] Checking database connectivity...")
    if not check_database():
        all_ok = False

    logger.info("\n[3/4] Checking Redis connectivity...")
    check_redis()

    logger.info("\n[4/4] Checking frontend build...")
    check_frontend_build()

    logger.info("\n" + "=" * 60)
    if all_ok:
        logger.info("PRE-DEPLOY CHECK PASSED - proceeding with migration")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("PRE-DEPLOY CHECK FAILED - fix issues above before deploying")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
