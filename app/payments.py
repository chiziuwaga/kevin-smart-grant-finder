"""
Stripe subscription management for grant finder platform.
Handles subscription creation, webhooks, customer management, and usage tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, Subscription, SubscriptionStatus
from config.settings import get_settings
from services.resend_client import get_resend_client

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripePaymentService:
    """Service for managing Stripe subscriptions and payments."""

    def __init__(self):
        self.stripe_secret_key = settings.STRIPE_SECRET_KEY
        self.stripe_webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        self.stripe_price_id = settings.STRIPE_PRICE_ID
        self.frontend_url = settings.FRONTEND_URL

        if not self.stripe_secret_key:
            logger.warning("STRIPE_SECRET_KEY not set. Stripe functionality will be disabled.")

        stripe.api_key = self.stripe_secret_key

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.Customer:
        """
        Create a Stripe customer.

        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata

        Returns:
            Stripe Customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise

    async def create_checkout_session(
        self,
        db: AsyncSession,
        user: User,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for $35/month subscription with 14-day trial.

        Args:
            db: Database session
            user: User object
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after canceled payment

        Returns:
            Dictionary with session ID and URL
        """
        try:
            # Get or create Stripe customer
            stripe_customer_id = await self._get_or_create_customer(db, user)

            # Set default URLs if not provided
            if not success_url:
                success_url = f"{self.frontend_url}/dashboard?payment=success"
            if not cancel_url:
                cancel_url = f"{self.frontend_url}/pricing?payment=canceled"

            # Create checkout session with 14-day trial
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": self.stripe_price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                subscription_data={
                    "trial_period_days": 14,
                    "metadata": {
                        "user_id": str(user.id),
                        "auth0_id": user.auth0_id,
                    }
                },
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(user.id),
                metadata={
                    "user_id": str(user.id),
                    "auth0_id": user.auth0_id,
                }
            )

            logger.info(f"Created checkout session {session.id} for user {user.email}")

            return {
                "sessionId": session.id,
                "url": session.url
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {str(e)}")
            raise

    async def create_customer_portal_session(
        self,
        db: AsyncSession,
        user: User,
        return_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a Stripe customer portal session for managing subscription.

        Args:
            db: Database session
            user: User object
            return_url: URL to return to after portal session

        Returns:
            Dictionary with portal URL
        """
        try:
            # Get user's subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            subscription = result.scalar_one_or_none()

            if not subscription or not subscription.stripe_customer_id:
                raise ValueError("No Stripe customer found for user")

            if not return_url:
                return_url = f"{self.frontend_url}/dashboard"

            # Create portal session
            portal_session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=return_url,
            )

            logger.info(f"Created portal session for user {user.email}")

            return {
                "url": portal_session.url
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {str(e)}")
            raise

    async def cancel_subscription(
        self,
        db: AsyncSession,
        user: User,
        cancel_immediately: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a user's subscription.

        Args:
            db: Database session
            user: User object
            cancel_immediately: If True, cancel immediately; otherwise at period end

        Returns:
            Updated subscription details
        """
        try:
            # Get user's subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            subscription = result.scalar_one_or_none()

            if not subscription or not subscription.stripe_subscription_id:
                raise ValueError("No active subscription found")

            # Cancel the subscription in Stripe
            if cancel_immediately:
                canceled_sub = stripe.Subscription.cancel(
                    subscription.stripe_subscription_id
                )
            else:
                canceled_sub = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )

            # Update database
            subscription.cancel_at_period_end = not cancel_immediately
            if cancel_immediately:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
                user.subscription_status = SubscriptionStatus.CANCELED
            else:
                subscription.canceled_at = datetime.utcnow()

            await db.commit()
            await db.refresh(subscription)

            logger.info(f"Canceled subscription for user {user.email} (immediate: {cancel_immediately})")

            return subscription.to_dict()

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            await db.rollback()
            raise

    async def reactivate_subscription(
        self,
        db: AsyncSession,
        user: User
    ) -> Dict[str, Any]:
        """
        Reactivate a canceled subscription (before period end).

        Args:
            db: Database session
            user: User object

        Returns:
            Updated subscription details
        """
        try:
            # Get user's subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            subscription = result.scalar_one_or_none()

            if not subscription or not subscription.stripe_subscription_id:
                raise ValueError("No subscription found")

            # Reactivate in Stripe
            reactivated_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )

            # Update database
            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            subscription.status = SubscriptionStatus.ACTIVE
            user.subscription_status = SubscriptionStatus.ACTIVE

            await db.commit()
            await db.refresh(subscription)

            logger.info(f"Reactivated subscription for user {user.email}")

            return subscription.to_dict()

        except stripe.error.StripeError as e:
            logger.error(f"Failed to reactivate subscription: {str(e)}")
            await db.rollback()
            raise

    async def handle_webhook_event(
        self,
        db: AsyncSession,
        payload: bytes,
        signature: str
    ) -> Dict[str, str]:
        """
        Handle Stripe webhook events.

        Args:
            db: Database session
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            Status dictionary
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.stripe_webhook_secret
            )
        except ValueError:
            logger.error("Invalid webhook payload")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            raise ValueError("Invalid signature")

        # Handle the event
        event_type = event["type"]
        data_object = event["data"]["object"]

        logger.info(f"Processing webhook event: {event_type}")

        try:
            if event_type == "customer.subscription.created":
                await self._handle_subscription_created(db, data_object)

            elif event_type == "customer.subscription.updated":
                await self._handle_subscription_updated(db, data_object)

            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(db, data_object)

            elif event_type == "customer.subscription.trial_will_end":
                await self._handle_trial_will_end(db, data_object)

            elif event_type == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(db, data_object)

            elif event_type == "invoice.payment_failed":
                await self._handle_payment_failed(db, data_object)

            else:
                logger.info(f"Unhandled event type: {event_type}")

            return {"status": "success", "event_type": event_type}

        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {str(e)}")
            await db.rollback()
            raise

    async def _get_or_create_customer(
        self,
        db: AsyncSession,
        user: User
    ) -> str:
        """Get existing or create new Stripe customer for user."""
        # Check if user has a subscription with customer ID
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = result.scalar_one_or_none()

        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        # Create new customer
        customer = await self.create_customer(
            email=user.email,
            name=user.full_name,
            metadata={
                "user_id": str(user.id),
                "auth0_id": user.auth0_id
            }
        )

        # Create or update subscription record
        if not subscription:
            subscription = Subscription(
                user_id=user.id,
                stripe_customer_id=customer.id,
                status=SubscriptionStatus.INCOMPLETE
            )
            db.add(subscription)
        else:
            subscription.stripe_customer_id = customer.id

        await db.commit()

        return customer.id

    async def _handle_subscription_created(
        self,
        db: AsyncSession,
        subscription_data: Dict[str, Any]
    ):
        """Handle subscription.created webhook."""
        stripe_sub_id = subscription_data["id"]
        stripe_customer_id = subscription_data["customer"]
        status = subscription_data["status"]

        # Get user from customer ID
        user = await self._get_user_from_customer(db, stripe_customer_id)
        if not user:
            logger.error(f"User not found for customer {stripe_customer_id}")
            return

        # Get or create subscription record
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            subscription = Subscription(user_id=user.id)
            db.add(subscription)

        # Update subscription details
        subscription.stripe_customer_id = stripe_customer_id
        subscription.stripe_subscription_id = stripe_sub_id
        subscription.status = self._map_stripe_status(status)
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data["current_period_end"]
        )

        # Update user
        user.subscription_status = subscription.status

        # Set trial limits if in trial
        if status == "trialing":
            user.subscription_tier = "trial"
            user.searches_limit = 5
            user.applications_limit = 0
            user.searches_used = 0
            user.applications_used = 0
        else:
            user.subscription_tier = "basic"
            user.searches_limit = 50
            user.applications_limit = 20
            user.searches_used = 0
            user.applications_used = 0

            # Send subscription confirmation email for active subscriptions
            try:
                resend = get_resend_client()
                await resend.send_subscription_confirmation_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    plan_name="Basic",
                    amount=3500  # $35.00 in cents
                )
                logger.info(f"Subscription confirmation email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send subscription confirmation email to {user.email}: {e}")

        await db.commit()
        logger.info(f"Created subscription {stripe_sub_id} for user {user.email}")

    async def _handle_subscription_updated(
        self,
        db: AsyncSession,
        subscription_data: Dict[str, Any]
    ):
        """Handle subscription.updated webhook."""
        stripe_sub_id = subscription_data["id"]
        status = subscription_data["status"]

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription {stripe_sub_id} not found in database")
            return

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error(f"User not found for subscription {stripe_sub_id}")
            return

        # Update subscription
        old_status = subscription.status
        subscription.status = self._map_stripe_status(status)
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data["current_period_end"]
        )
        subscription.cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)

        # Update user status
        user.subscription_status = subscription.status

        # Update limits based on status change
        if old_status == SubscriptionStatus.TRIALING and status == "active":
            # Trial ended, upgrade to full access
            user.subscription_tier = "basic"
            user.searches_limit = 50
            user.applications_limit = 20
            user.searches_used = 0
            user.applications_used = 0
            logger.info(f"User {user.email} upgraded from trial to active subscription")

            # Send subscription confirmation email
            try:
                resend = get_resend_client()
                await resend.send_subscription_confirmation_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    plan_name="Basic",
                    amount=3500  # $35.00 in cents
                )
                logger.info(f"Subscription confirmation email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send subscription confirmation email to {user.email}: {e}")

        await db.commit()
        logger.info(f"Updated subscription {stripe_sub_id} status: {old_status} -> {subscription.status}")

    async def _handle_subscription_deleted(
        self,
        db: AsyncSession,
        subscription_data: Dict[str, Any]
    ):
        """Handle subscription.deleted webhook."""
        stripe_sub_id = subscription_data["id"]

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription {stripe_sub_id} not found in database")
            return

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error(f"User not found for subscription {stripe_sub_id}")
            return

        # Update to canceled status
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.utcnow()
        user.subscription_status = SubscriptionStatus.CANCELED
        user.subscription_tier = "free"
        user.searches_limit = 0
        user.applications_limit = 0

        await db.commit()
        logger.info(f"Deleted subscription {stripe_sub_id} for user {user.email}")

    async def _handle_trial_will_end(
        self,
        db: AsyncSession,
        subscription_data: Dict[str, Any]
    ):
        """Handle subscription.trial_will_end webhook (3 days before trial ends)."""
        stripe_sub_id = subscription_data["id"]

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription {stripe_sub_id} not found in database")
            return

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user:
            logger.info(f"Trial will end soon for user {user.email}")
            # TODO: Send email notification about trial ending

        await db.commit()

    async def _handle_payment_succeeded(
        self,
        db: AsyncSession,
        invoice_data: Dict[str, Any]
    ):
        """Handle invoice.payment_succeeded webhook."""
        stripe_sub_id = invoice_data.get("subscription")

        if not stripe_sub_id:
            return

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription {stripe_sub_id} not found in database")
            return

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error(f"User not found for subscription {stripe_sub_id}")
            return

        # Reset usage counters for new billing period
        user.searches_used = 0
        user.applications_used = 0
        user.usage_period_start = datetime.utcnow()
        user.usage_period_end = subscription.current_period_end

        # Ensure active status
        if subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.ACTIVE
            user.subscription_status = SubscriptionStatus.ACTIVE

        await db.commit()
        logger.info(f"Payment succeeded for user {user.email}, usage reset")

    async def _handle_payment_failed(
        self,
        db: AsyncSession,
        invoice_data: Dict[str, Any]
    ):
        """Handle invoice.payment_failed webhook."""
        stripe_sub_id = invoice_data.get("subscription")

        if not stripe_sub_id:
            return

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription {stripe_sub_id} not found in database")
            return

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error(f"User not found for subscription {stripe_sub_id}")
            return

        # Update to past_due status
        subscription.status = SubscriptionStatus.PAST_DUE
        user.subscription_status = SubscriptionStatus.PAST_DUE

        await db.commit()
        logger.warning(f"Payment failed for user {user.email}, status: past_due")
        # TODO: Send email notification about payment failure

    async def _get_user_from_customer(
        self,
        db: AsyncSession,
        stripe_customer_id: str
    ) -> Optional[User]:
        """Get user from Stripe customer ID."""
        result = await db.execute(
            select(User)
            .join(Subscription)
            .where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        return result.scalar_one_or_none()

    def _map_stripe_status(self, stripe_status: str) -> SubscriptionStatus:
        """Map Stripe subscription status to our SubscriptionStatus enum."""
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "canceled": SubscriptionStatus.CANCELED,
            "past_due": SubscriptionStatus.PAST_DUE,
            "trialing": SubscriptionStatus.TRIALING,
            "incomplete": SubscriptionStatus.INCOMPLETE,
            "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
            "unpaid": SubscriptionStatus.UNPAID,
        }
        return status_map.get(stripe_status, SubscriptionStatus.INCOMPLETE)


# Singleton instance
_payment_service: Optional[StripePaymentService] = None


def get_payment_service() -> StripePaymentService:
    """Get singleton payment service instance."""
    global _payment_service
    if _payment_service is None:
        _payment_service = StripePaymentService()
    return _payment_service
