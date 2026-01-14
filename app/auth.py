"""
Auth0 JWT authentication and user management.
Handles JWT token verification, user creation, and authentication dependencies.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

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

# Get settings
settings = Settings()


class Auth0Config:
    """Auth0 configuration from environment variables."""

    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.api_audience = settings.AUTH0_API_AUDIENCE
        self.algorithms = settings.AUTH0_ALGORITHMS or ["RS256"]
        self.issuer = f"https://{self.domain}/"

    @property
    def jwks_url(self):
        return f"https://{self.domain}/.well-known/jwks.json"


auth0_config = Auth0Config()


class JWTVerifier:
    """Verifies Auth0 JWT tokens."""

    def __init__(self):
        self.config = auth0_config
        self._jwks_client = None

    def get_jwks_client(self):
        """Get or create JWKS client for token verification."""
        if self._jwks_client is None:
            from jose import jwk
            import requests

            # Fetch JWKS
            response = requests.get(self.config.jwks_url)
            response.raise_for_status()
            self._jwks_client = response.json()

        return self._jwks_client

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode Auth0 JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Decode without verification first to get the header
            unverified_header = jwt.get_unverified_header(token)

            # Get the signing key
            jwks = self.get_jwks_client()
            rsa_key = {}

            for key in jwks.get("keys", []):
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
                    break

            if not rsa_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate signing key"
                )

            # Verify and decode the token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=self.config.algorithms,
                audience=self.config.api_audience,
                issuer=self.config.issuer
            )

            return payload

        except JWTError as e:
            logger.error(f"JWT verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


jwt_verifier = JWTVerifier()


async def verify_auth0_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify Auth0 JWT token.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        Decoded token payload
    """
    token = credentials.credentials
    return jwt_verifier.verify_token(token)


async def get_or_create_user(
    db: AsyncSession,
    auth0_id: str,
    email: str,
    full_name: Optional[str] = None
) -> User:
    """
    Get existing user or create new user from Auth0 info.

    Args:
        db: Database session
        auth0_id: Auth0 user ID
        email: User email
        full_name: Optional full name

    Returns:
        User object
    """
    # Try to find existing user
    result = await db.execute(
        select(User).where(User.auth0_id == auth0_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        logger.info(f"Existing user logged in: {email}")
        return user

    # Create new user
    user = User(
        auth0_id=auth0_id,
        email=email,
        full_name=full_name,
        subscription_status=SubscriptionStatus.TRIALING,  # Start with trial
        subscription_tier="trial",
        searches_limit=5,  # 14-day trial with 5 searches
        applications_limit=0,  # No applications during trial
        searches_used=0,
        applications_used=0,
    )

    db.add(user)
    await db.flush()

    # Create default user settings
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

    # Send welcome email
    try:
        resend = get_resend_client()
        await resend.send_welcome_email(
            user_email=email,
            user_name=full_name or email.split('@')[0],
            trial_info={
                "searches": 5,
                "applications": 0,
                "duration_days": 14
            }
        )
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        # Don't fail user creation if email fails

    return user


async def get_current_user(
    token_payload: Dict[str, Any] = Depends(verify_auth0_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    Creates user on first login if not exists.

    Args:
        token_payload: Decoded JWT token payload
        db: Database session

    Returns:
        Current User object

    Raises:
        HTTPException: If user is not active
    """
    auth0_id = token_payload.get("sub")
    email = token_payload.get("email")
    name = token_payload.get("name")

    if not auth0_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Get or create user
    user = await get_or_create_user(db, auth0_id, email, name)

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active (alias for consistency).
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to ensure current user is an admin.

    Args:
        current_user: Current authenticated user

    Returns:
        Current admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def check_subscription_active(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to ensure user has an active subscription.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user with active subscription

    Raises:
        HTTPException: If subscription is not active
    """
    if current_user.subscription_status not in [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING
    ]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required"
        )

    return current_user


async def check_search_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to check if user has searches remaining.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Current user with searches available

    Raises:
        HTTPException: If search limit exceeded
    """
    if current_user.searches_used >= current_user.searches_limit:
        # Send limit reached email notification
        try:
            resend = get_resend_client()
            await resend.send_limit_reached_email(
                user_email=current_user.email,
                user_name=current_user.full_name or current_user.email.split('@')[0],
                limit_type="searches",
                limit_value=current_user.searches_limit
            )
            logger.info(f"Limit reached email sent to {current_user.email} for searches")
        except Exception as e:
            logger.error(f"Failed to send limit notification to {current_user.email}: {e}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly search limit ({current_user.searches_limit}) reached"
        )

    return current_user


async def check_application_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to check if user has application generations remaining.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Current user with applications available

    Raises:
        HTTPException: If application limit exceeded
    """
    if current_user.applications_used >= current_user.applications_limit:
        # Send limit reached email notification
        try:
            resend = get_resend_client()
            await resend.send_limit_reached_email(
                user_email=current_user.email,
                user_name=current_user.full_name or current_user.email.split('@')[0],
                limit_type="applications",
                limit_value=current_user.applications_limit
            )
            logger.info(f"Limit reached email sent to {current_user.email} for applications")
        except Exception as e:
            logger.error(f"Failed to send limit notification to {current_user.email}: {e}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly application limit ({current_user.applications_limit}) reached"
        )

    return current_user


# Optional token (for endpoints that work with or without auth)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise.
    Useful for endpoints that work differently based on authentication status.

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token_payload = jwt_verifier.verify_token(credentials.credentials)
        auth0_id = token_payload.get("sub")
        email = token_payload.get("email")
        name = token_payload.get("name")

        if not auth0_id or not email:
            return None

        user = await get_or_create_user(db, auth0_id, email, name)

        if not user.is_active:
            return None

        return user
    except Exception as e:
        logger.warning(f"Optional auth failed: {str(e)}")
        return None
