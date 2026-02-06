"""
Resend email client for notifications and communications.
Replaces Telegram bot with professional email notifications.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import resend

from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class ResendEmailClient:
    """
    Client for sending emails via Resend API.
    Handles all notifications:
    - Grant alerts
    - Application generation notifications
    - Subscription confirmations
    - Usage warnings
    - Monthly reports
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Resend client.

        Args:
            api_key: Optional API key (defaults to settings)
        """
        self.api_key = api_key or settings.RESEND_API_KEY
        self.from_email = settings.FROM_EMAIL
        self.frontend_url = settings.FRONTEND_URL.rstrip('/')

        if not self.api_key:
            logger.warning("Resend API key not configured")
        else:
            resend.api_key = self.api_key

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an email via Resend.

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional)
            reply_to: Reply-to email address (optional)
            **kwargs: Additional Resend parameters

        Returns:
            Response dict from Resend API

        Raises:
            Exception: If email send fails
        """
        try:
            params = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            }

            if text:
                params["text"] = text

            if reply_to:
                params["reply_to"] = reply_to

            params.update(kwargs)

            response = resend.Emails.send(params)

            logger.info(f"Email sent to {to}: {subject}")
            return response

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            raise

    async def send_grant_alert(
        self,
        user_email: str,
        user_name: str,
        grants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send email alert about new high-relevance grants.

        Args:
            user_email: User's email address
            user_name: User's name
            grants: List of grant dicts with details

        Returns:
            Email send response
        """
        subject = f"🎯 {len(grants)} New Grant{'s' if len(grants) > 1 else ''} Found!"

        # Build grant list HTML
        grants_html = ""
        for grant in grants[:10]:  # Limit to 10 grants per email
            grants_html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-left: 4px solid #2563eb;">
                <h3 style="margin: 0 0 10px 0; color: #1e293b;">{grant.get('title', 'Untitled Grant')}</h3>
                <p style="margin: 5px 0; color: #64748b;">
                    <strong>Funding:</strong> {grant.get('funding_amount_display', 'Not specified')}<br>
                    <strong>Deadline:</strong> {grant.get('deadline', 'Not specified')}<br>
                    <strong>Relevance Score:</strong> {int(grant.get('overall_composite_score', 0) * 100)}%
                </p>
                <p style="margin: 10px 0 0 0; color: #475569;">{grant.get('summary_llm', grant.get('description', ''))[:200]}...</p>
                {f'<a href="{grant.get("source_url")}" style="color: #2563eb; text-decoration: none;">View Details →</a>' if grant.get('source_url') else ''}
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #334155; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1e293b; margin-bottom: 10px;">New Grants Found!</h1>
                <p style="color: #64748b; margin: 0;">We found {len(grants)} grant opportunit{'ies' if len(grants) > 1 else 'y'} matching your profile</p>
            </div>

            <p>Hi {user_name},</p>

            <p>Great news! We've discovered new grant opportunities that match your business profile and interests.</p>

            {grants_html}

            {f'<p style="margin-top: 20px; color: #64748b; font-size: 14px;"><em>Showing {min(10, len(grants))} of {len(grants)} grants found. <a href="{self.frontend_url}/grants" style="color: #2563eb;">View all in your dashboard →</a></em></p>' if len(grants) > 10 else ''}

            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; color: #64748b; font-size: 14px;">
                    You're receiving this email because you have grant alerts enabled.<br>
                    <a href="{self.frontend_url}/settings" style="color: #2563eb;">Manage email preferences</a>
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        New Grants Found!

        Hi {user_name},

        We found {len(grants)} grant opportunit{'ies' if len(grants) > 1 else 'y'} matching your profile:

        """

        for grant in grants[:10]:
            text += f"""
            {grant.get('title', 'Untitled')}
            Funding: {grant.get('funding_amount_display', 'Not specified')}
            Deadline: {grant.get('deadline', 'Not specified')}
            Relevance: {int(grant.get('overall_composite_score', 0) * 100)}%

            """

        return await self.send_email(user_email, subject, html, text)

    async def send_subscription_welcome(
        self,
        user_email: str,
        user_name: str,
        plan_name: str,
        searches_limit: int,
        applications_limit: int
    ) -> Dict[str, Any]:
        """
        Send welcome email after subscription.

        Args:
            user_email: User's email
            user_name: User's name
            plan_name: Subscription plan name
            searches_limit: Monthly search limit
            applications_limit: Monthly application limit

        Returns:
            Email send response
        """
        subject = f"Welcome to Grant Finder {plan_name.title()} Plan! 🎉"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #334155; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1e293b;">Welcome to Grant Finder!</h1>
            </div>

            <p>Hi {user_name},</p>

            <p>Thank you for subscribing to Grant Finder! Your {plan_name.title()} plan is now active.</p>

            <div style="margin: 25px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <h3 style="margin: 0 0 15px 0; color: #1e293b;">Your Plan Includes:</h3>
                <ul style="margin: 0; padding-left: 20px; color: #475569;">
                    <li>{searches_limit} grant searches per month</li>
                    <li>{applications_limit} AI-generated applications per month</li>
                    <li>Automated grant monitoring</li>
                    <li>Email notifications for new grants</li>
                    <li>Priority customer support</li>
                </ul>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{self.frontend_url}/dashboard" style="display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">Start Finding Grants</a>
            </div>

            <p><strong>Getting Started:</strong></p>
            <ol style="color: #475569;">
                <li>Complete your business profile (required for best results)</li>
                <li>Set your grant preferences and search criteria</li>
                <li>Run your first grant search</li>
                <li>Generate your first application</li>
            </ol>

            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; color: #64748b; font-size: 14px;">
                    Questions? <a href="{self.frontend_url}/support" style="color: #2563eb;">Contact support</a> |
                    <a href="{self.frontend_url}/docs" style="color: #2563eb;">View documentation</a>
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        Welcome to Grant Finder!

        Hi {user_name},

        Your {plan_name.title()} plan is now active!

        Your Plan Includes:
        - {searches_limit} grant searches/month
        - {applications_limit} AI applications/month
        - Automated monitoring
        - Email notifications

        Get started: {self.frontend_url}/dashboard
        """

        return await self.send_email(user_email, subject, html, text)

    async def send_usage_warning(
        self,
        user_email: str,
        user_name: str,
        resource_type: str,  # "searches" or "applications"
        used: int,
        limit: int,
        percentage: int
    ) -> Dict[str, Any]:
        """
        Send warning when approaching usage limit.

        Args:
            user_email: User's email
            user_name: User's name
            resource_type: Type of resource ("searches" or "applications")
            used: Amount used
            limit: Total limit
            percentage: Percentage used

        Returns:
            Email send response
        """
        subject = f"⚠️ {percentage}% of Your {resource_type.title()} Used"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #334155; max-width: 600px; margin: 0 auto; padding: 20px;">
            <p>Hi {user_name},</p>

            <p>This is a friendly reminder about your monthly usage:</p>

            <div style="margin: 25px 0; padding: 20px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                <h3 style="margin: 0 0 10px 0; color: #92400e;">Usage Alert</h3>
                <p style="margin: 0; color: #78350f;">You've used <strong>{used} of {limit}</strong> {resource_type} this month ({percentage}% of your limit).</p>
            </div>

            <p>Your usage will reset at the start of your next billing cycle.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{self.frontend_url}/settings/billing" style="display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">View Usage & Billing</a>
            </div>
        </body>
        </html>
        """

        text = f"""
        Usage Alert

        Hi {user_name},

        You've used {used} of {limit} {resource_type} this month ({percentage}%).

        View your usage: {self.frontend_url}/settings/billing
        """

        return await self.send_email(user_email, subject, html, text)

    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        trial_info: dict
    ) -> Dict[str, Any]:
        """
        Send welcome email to new user with trial information.

        Args:
            user_email: User's email address
            user_name: User's name
            trial_info: Dict with trial details (searches, applications, duration_days)

        Returns:
            Email send response
        """
        subject = "Welcome to Grant Finder! 🎉"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 24px; color: #1e293b; }}
                .info-box {{ background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; margin: 24px 0; border-radius: 8px; }}
                .info-box h3 {{ margin: 0 0 12px 0; color: #1e293b; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; margin: 16px 0; border-radius: 6px; font-weight: 600; }}
                ul {{ list-style: none; padding-left: 0; }}
                ul li {{ padding: 8px 0; border-bottom: 1px solid #E0E0E0; color: #475569; }}
                ul li:last-child {{ border-bottom: none; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to Grant Finder, {user_name}!</h1>
                <p>Your account has been created and your <strong>{trial_info.get('duration_days', 14)}-day free trial</strong> has started.</p>

                <div class="info-box">
                    <h3>Your Trial Includes:</h3>
                    <ul>
                        <li><strong>{trial_info.get('searches', 5)} Grant Searches</strong> - AI-powered grant discovery</li>
                        <li><strong>{trial_info.get('applications', 0)} Applications</strong> - Upgrade for AI application generation</li>
                        <li>Email notifications for high-priority grants</li>
                        <li>Full platform access</li>
                    </ul>
                </div>

                <p>Ready to find grants?</p>
                <a href="{settings.FRONTEND_URL}/dashboard" class="button">Go to Dashboard</a>

                <div class="footer">
                    <p>Questions? Reply to this email or visit our help center.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Welcome to Grant Finder, {user_name}!

        Your {trial_info.get('duration_days', 14)}-day free trial has started with:
        - {trial_info.get('searches', 5)} Grant Searches
        - AI-powered grant discovery
        - Email notifications

        Get started: {settings.FRONTEND_URL}/dashboard
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            html=html,
            text=plain
        )

    async def send_limit_reached_email(
        self,
        user_email: str,
        user_name: str,
        limit_type: str,
        limit_value: int
    ) -> Dict[str, Any]:
        """
        Send email when user reaches usage limit.

        Args:
            user_email: User's email address
            user_name: User's name
            limit_type: Type of limit ("searches" or "applications")
            limit_value: The limit value reached

        Returns:
            Email send response
        """
        subject = f"⚠️ {limit_type.capitalize()} Limit Reached"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 24px; color: #1e293b; }}
                .warning {{ background: #FFF3CD; border: 1px solid #FFE69C; padding: 16px; margin: 24px 0; border-radius: 8px; border-left: 4px solid #f59e0b; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                ul {{ color: #475569; margin: 16px 0; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Usage Limit Reached</h1>
                <div class="warning">
                    <strong>Hi {user_name},</strong><br>
                    You've used all {limit_value} of your monthly {limit_type}.
                </div>
                <p>To continue using Grant Finder, please upgrade your subscription:</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{settings.FRONTEND_URL}/settings" class="button">Upgrade Now</a>
                </div>
                <p><strong>Our Basic plan ($15/month) includes:</strong></p>
                <ul>
                    <li>50 Grant Searches per month</li>
                    <li>20 AI-Generated Applications per month</li>
                    <li>Automated grant discovery</li>
                    <li>Priority support</li>
                </ul>
                <div class="footer">
                    <p>Questions? Contact us at {self.from_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Usage Limit Reached

        Hi {user_name},

        You've used all {limit_value} of your monthly {limit_type}.

        To continue using Grant Finder, upgrade to our Basic plan ($15/month):
        - 50 Grant Searches/month
        - 20 AI-Generated Applications/month
        - Automated grant discovery
        - Priority support

        Upgrade now: {settings.FRONTEND_URL}/settings
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            html=html,
            text=plain
        )

    async def send_application_complete_email(
        self,
        user_email: str,
        user_name: str,
        grant_title: str,
        application_id: int
    ) -> Dict[str, Any]:
        """
        Send email when AI application generation completes.

        Args:
            user_email: User's email address
            user_name: User's name
            grant_title: Title of the grant
            application_id: ID of generated application

        Returns:
            Email send response
        """
        subject = f"✅ Application Ready: {grant_title}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 24px; color: #1e293b; }}
                .success {{ background: #D4EDDA; border: 1px solid #C3E6CB; padding: 16px; margin: 24px 0; border-radius: 8px; border-left: 4px solid #10b981; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                ul {{ color: #475569; margin: 16px 0; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your Application is Ready!</h1>
                <div class="success">
                    <strong>Hi {user_name},</strong><br>
                    We've generated your application for: <strong>{grant_title}</strong>
                </div>
                <p><strong>Your AI-generated application includes:</strong></p>
                <ul>
                    <li>Executive Summary</li>
                    <li>Needs Statement</li>
                    <li>Project Description</li>
                    <li>Budget Narrative</li>
                    <li>Organizational Capacity</li>
                    <li>Impact Statement</li>
                </ul>
                <p>Review and edit your application:</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{settings.FRONTEND_URL}/applications/{application_id}" class="button">View Application</a>
                </div>
                <div class="footer">
                    <p>Need help? Contact support at {self.from_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Your Application is Ready!

        Hi {user_name},

        We've generated your application for: {grant_title}

        Your application includes:
        - Executive Summary
        - Needs Statement
        - Project Description
        - Budget Narrative
        - Organizational Capacity
        - Impact Statement

        Review and edit: {settings.FRONTEND_URL}/applications/{application_id}
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            html=html,
            text=plain
        )

    async def send_search_complete_email(
        self,
        user_email: str,
        user_name: str,
        grants_found: int,
        high_priority: int,
        duration_seconds: float,
        searches_remaining: int,
    ) -> Dict[str, Any]:
        """
        Send summary email after a grant search run completes.

        Args:
            user_email: User's email address
            user_name: User's name
            grants_found: Total grants discovered
            high_priority: Number of high-priority grants
            duration_seconds: How long the search took
            searches_remaining: Searches left this month

        Returns:
            Email send response
        """
        subject = f"Search Complete: {grants_found} Grant{'s' if grants_found != 1 else ''} Found"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 16px; color: #1e293b; }}
                .stats {{ display: flex; gap: 16px; margin: 24px 0; }}
                .stat-box {{ flex: 1; background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; text-align: center; }}
                .stat-value {{ font-size: 28px; font-weight: 700; color: #1A1A1A; }}
                .stat-label {{ font-size: 13px; color: #666; margin-top: 4px; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; font-weight: 600; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Grant Search Complete</h1>
                <p>Hi {user_name}, your latest grant search has finished.</p>

                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0;">
                    <tr>
                        <td style="background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; text-align: center; width: 33%;">
                            <div style="font-size: 28px; font-weight: 700; color: #1A1A1A;">{grants_found}</div>
                            <div style="font-size: 13px; color: #666; margin-top: 4px;">Grants Found</div>
                        </td>
                        <td style="background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; text-align: center; width: 33%;">
                            <div style="font-size: 28px; font-weight: 700; color: {'#10b981' if high_priority > 0 else '#1A1A1A'};">{high_priority}</div>
                            <div style="font-size: 13px; color: #666; margin-top: 4px;">High Priority</div>
                        </td>
                        <td style="background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; text-align: center; width: 33%;">
                            <div style="font-size: 28px; font-weight: 700; color: #1A1A1A;">{searches_remaining}</div>
                            <div style="font-size: 13px; color: #666; margin-top: 4px;">Searches Left</div>
                        </td>
                    </tr>
                </table>

                <p style="color: #666; font-size: 14px;">Search completed in {duration_seconds:.1f} seconds.</p>

                <div style="text-align: center; margin: 24px 0;">
                    <a href="{self.frontend_url}/grants" class="button">View Results in Dashboard</a>
                </div>

                <div class="footer">
                    <p>
                        You're receiving this because you have search notifications enabled.<br>
                        <a href="{self.frontend_url}/settings" style="color: #2563eb;">Manage preferences</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Grant Search Complete

        Hi {user_name},

        Your search found {grants_found} grants ({high_priority} high-priority).
        Completed in {duration_seconds:.1f}s. You have {searches_remaining} searches remaining.

        View results: {self.frontend_url}/grants
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            html=html,
            text=plain
        )

    async def send_subscription_confirmation_email(
        self,
        user_email: str,
        user_name: str,
        plan_name: str,
        amount: float
    ) -> Dict[str, Any]:
        """
        Send subscription confirmation email.

        Args:
            user_email: User's email address
            user_name: User's name
            plan_name: Name of subscription plan
            amount: Amount in cents

        Returns:
            Email send response
        """
        subject = "✅ Subscription Confirmed"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 24px; color: #1e293b; }}
                .success {{ background: #D4EDDA; border: 1px solid #C3E6CB; padding: 16px; margin: 24px 0; border-radius: 8px; border-left: 4px solid #10b981; }}
                .info-row {{ padding: 8px 0; border-bottom: 1px solid #e2e8f0; }}
                .info-row:last-child {{ border-bottom: none; }}
                ul {{ color: #475569; margin: 16px 0; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
                a {{ color: #2563eb; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to Grant Finder {plan_name}!</h1>
                <div class="success">
                    <strong>Hi {user_name},</strong><br>
                    Your subscription has been activated.
                </div>
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 24px 0;">
                    <div class="info-row">
                        <strong>Plan:</strong> {plan_name}
                    </div>
                    <div class="info-row">
                        <strong>Amount:</strong> ${amount/100:.2f}/month
                    </div>
                </div>
                <p><strong>Your monthly limits have been reset to:</strong></p>
                <ul>
                    <li>50 Grant Searches</li>
                    <li>20 AI-Generated Applications</li>
                </ul>
                <p>Manage your subscription in <a href="{settings.FRONTEND_URL}/settings">Settings</a></p>
                <div class="footer">
                    <p>Questions? Contact us at {self.from_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Welcome to Grant Finder {plan_name}!

        Hi {user_name},

        Your subscription has been activated.

        Plan: {plan_name}
        Amount: ${amount/100:.2f}/month

        Your monthly limits:
        - 50 Grant Searches
        - 20 AI-Generated Applications

        Manage subscription: {settings.FRONTEND_URL}/settings
        """

        return await self.send_email(
            to=user_email,
            subject=subject,
            html=html,
            text=plain
        )


    async def send_weekly_report_email(
        self,
        user_email: str,
        user_name: str,
        searches_this_week: int,
        applications_generated: int,
        searches_remaining: int,
        applications_remaining: int,
    ) -> Dict[str, Any]:
        """Send weekly activity report - money finder while you sleep."""
        subject = f"Your Weekly Grant Report - {searches_this_week} searches, {applications_generated} applications"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 16px; color: #1e293b; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; font-weight: 600; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your Weekly Grant Report</h1>
                <p>Hi {user_name}, here's what your money finder did this week:</p>
                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0;">
                    <tr>
                        <td style="background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; text-align: center; width: 50%;">
                            <div style="font-size: 28px; font-weight: 700;">{searches_this_week}</div>
                            <div style="font-size: 13px; color: #666;">Searches Run</div>
                        </td>
                        <td style="background: #FAFAFA; border: 1px solid #E0E0E0; padding: 16px; text-align: center; width: 50%;">
                            <div style="font-size: 28px; font-weight: 700;">{applications_generated}</div>
                            <div style="font-size: 13px; color: #666;">Applications Generated</div>
                        </td>
                    </tr>
                </table>
                <p style="color: #666; font-size: 14px;">
                    Remaining this month: {searches_remaining} searches, {applications_remaining} applications
                </p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{self.frontend_url}/grants" class="button">View Your Grants</a>
                </div>
                <div class="footer">
                    <p>Money finder for your business, while you sleep.</p>
                    <p><a href="{self.frontend_url}/settings" style="color: #2563eb;">Manage preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Weekly Grant Report

        Hi {user_name}, here's what your money finder did this week:

        Searches Run: {searches_this_week}
        Applications Generated: {applications_generated}
        Remaining: {searches_remaining} searches, {applications_remaining} applications

        View grants: {self.frontend_url}/grants
        """

        return await self.send_email(to=user_email, subject=subject, html=html, text=plain)

    async def send_trial_ending_email(
        self,
        user_email: str,
        user_name: str,
        days_remaining: int,
    ) -> Dict[str, Any]:
        """Send trial expiration warning."""
        subject = f"Your trial ends in {days_remaining} day{'s' if days_remaining != 1 else ''}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 24px; font-weight: 700; color: #1e293b; }}
                .warning {{ background: #FFF3CD; border: 1px solid #FFECB5; padding: 16px; margin: 24px 0; border-radius: 8px; border-left: 4px solid #fbbf24; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; font-weight: 600; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your Trial is Ending Soon</h1>
                <div class="warning">
                    <strong>Hi {user_name},</strong><br>
                    Your free trial ends in <strong>{days_remaining} day{'s' if days_remaining != 1 else ''}</strong>.
                </div>
                <p>Don't lose access to your money finder! Upgrade to keep:</p>
                <ul>
                    <li>50 grant searches per month</li>
                    <li>20 AI-generated applications</li>
                    <li>Automated grant discovery</li>
                    <li>Semantic matching to your business profile</li>
                </ul>
                <p><strong>Just $15/month</strong> - less than a single grant application fee.</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{self.frontend_url}/settings" class="button">Upgrade Now</a>
                </div>
                <div class="footer">
                    <p>Questions? Reply to this email or contact {self.from_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Your Trial is Ending Soon

        Hi {user_name},

        Your free trial ends in {days_remaining} day{'s' if days_remaining != 1 else ''}.

        Upgrade to keep access to 50 searches/month, 20 AI applications, and automated discovery.
        Just $15/month.

        Upgrade: {self.frontend_url}/settings
        """

        return await self.send_email(to=user_email, subject=subject, html=html, text=plain)

    async def send_payment_failed_email(
        self,
        user_email: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """Send payment failure notification."""
        subject = "Action Required: Payment Failed"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 24px; font-weight: 700; color: #1e293b; }}
                .alert {{ background: #F8D7DA; border: 1px solid #F5C2C7; padding: 16px; margin: 24px 0; border-radius: 8px; border-left: 4px solid #ef4444; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; font-weight: 600; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Payment Failed</h1>
                <div class="alert">
                    <strong>Hi {user_name},</strong><br>
                    We were unable to process your latest payment. Your account may be limited until this is resolved.
                </div>
                <p>Please update your payment method to continue using Grant Finder:</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{self.frontend_url}/settings" class="button">Update Payment Method</a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    If you believe this is an error, please contact us at {self.from_email}.
                </p>
                <div class="footer">
                    <p>We'll retry the payment automatically in a few days.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Payment Failed

        Hi {user_name},

        We were unable to process your latest payment.
        Please update your payment method: {self.frontend_url}/settings

        If this is an error, contact us at {self.from_email}.
        """

        return await self.send_email(to=user_email, subject=subject, html=html, text=plain)

    async def send_trial_expiration_reminder_email(
        self,
        user_email: str,
        user_name: str,
        days_remaining: int,
    ) -> Dict[str, Any]:
        """Send countdown reminder as trial approaches expiration."""
        subject = f"Reminder: {days_remaining} day{'s' if days_remaining != 1 else ''} left in your trial"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ font-size: 24px; font-weight: 700; color: #1e293b; }}
                .countdown {{ text-align: center; margin: 24px 0; padding: 24px; background: #f8f9fa; border-radius: 8px; }}
                .countdown-number {{ font-size: 48px; font-weight: 700; color: #1a1a1a; }}
                .button {{ display: inline-block; background: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; font-weight: 600; }}
                .footer {{ color: #666; font-size: 14px; margin-top: 32px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your Trial is Almost Over</h1>
                <p>Hi {user_name},</p>
                <div class="countdown">
                    <div class="countdown-number">{days_remaining}</div>
                    <div style="font-size: 14px; color: #666;">day{'s' if days_remaining != 1 else ''} remaining</div>
                </div>
                <p>Your money finder has been working while you sleep. Keep it going for just <strong>$15/month</strong>.</p>
                <div style="text-align: center; margin: 24px 0;">
                    <a href="{self.frontend_url}/settings" class="button">Subscribe Now</a>
                </div>
                <div class="footer">
                    <p>Money finder for your business, while you sleep.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain = f"""
        Your Trial is Almost Over

        Hi {user_name},

        You have {days_remaining} day{'s' if days_remaining != 1 else ''} left in your trial.
        Keep your money finder running for just $15/month.

        Subscribe: {self.frontend_url}/settings
        """

        return await self.send_email(to=user_email, subject=subject, html=html, text=plain)


# Singleton instance
_resend_client = None


def get_resend_client() -> ResendEmailClient:
    """Get or create Resend client singleton."""
    global _resend_client
    if _resend_client is None:
        _resend_client = ResendEmailClient()
    return _resend_client
