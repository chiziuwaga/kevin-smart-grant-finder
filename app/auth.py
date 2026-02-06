"""
Simple email/password JWT authentication.
Replaces Auth0 with self-hosted JWT tokens signed with HS256.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, UserSettings, SubscriptionStatus
from database.session import get_db
from config.settings import Settings
from services.resend_client import get_resend_client

logger = logging.getLogger(__name__)
security = HTTPBearer()

settings = Settings()

# JWT configuration
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = 30


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, email: str) -> str:
    """Create a short-lived access token."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token."""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

async def get_or_create_user(
    db: AsyncSession,
    email: str,
    full_name: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> User:
    """Get existing user by email or create a new one."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        return user

    # Create new user
    user = User(
        auth0_id=f"local|{email}",  # Compat placeholder
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        subscription_status=SubscriptionStatus.TRIALING,
        subscription_tier="trial",
        searches_limit=5,
        applications_limit=0,
        searches_used=0,
        applications_used=0,
    )
    db.add(user)
    await db.flush()

    # Default settings
    user_settings = UserSettings(
        user_id=user.id,
        email_notifications=True,
        deadline_reminders=True,
        minimum_score=0.7,
        notify_categories=[],
    )
    db.add(user_settings)
    await db.commit()
    await db.refresh(user)

    logger.info(f"New user created: {email} (trial)")

    # Send welcome email (best-effort)
    try:
        resend = get_resend_client()
        await resend.send_welcome_email(
            user_email=email,
            user_name=full_name or email.split("@")[0],
            trial_info={"searches": 5, "applications": 0, "duration_days": 14},
        )
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")

    return user


# ---------------------------------------------------------------------------
# FastAPI dependencies — same signatures as before so nothing else changes
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify Bearer token and return the current user."""
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias for consistency."""
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def check_subscription_active(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user has an active subscription."""
    if current_user.subscription_status not in [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
    ]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
        )
    return current_user


async def check_search_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check if user has searches remaining."""
    if current_user.searches_used >= current_user.searches_limit:
        try:
            resend = get_resend_client()
            await resend.send_limit_reached_email(
                user_email=current_user.email,
                user_name=current_user.full_name or current_user.email.split("@")[0],
                limit_type="searches",
                limit_value=current_user.searches_limit,
            )
        except Exception as e:
            logger.error(f"Failed to send limit notification: {e}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly search limit ({current_user.searches_limit}) reached",
        )
    return current_user


async def check_application_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check if user has application generations remaining."""
    if current_user.applications_used >= current_user.applications_limit:
        try:
            resend = get_resend_client()
            await resend.send_limit_reached_email(
                user_email=current_user.email,
                user_name=current_user.full_name or current_user.email.split("@")[0],
                limit_type="applications",
                limit_value=current_user.applications_limit,
            )
        except Exception as e:
            logger.error(f"Failed to send limit notification: {e}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly application limit ({current_user.applications_limit}) reached",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None
