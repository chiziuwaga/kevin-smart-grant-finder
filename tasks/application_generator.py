"""
Celery task for AI-powered grant application generation using RAG.
Generates comprehensive grant applications tailored to business profiles.
"""

import logging
import asyncio
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from config.settings import Settings
from database.models import (
    User,
    BusinessProfile,
    Grant,
    GeneratedApplication,
    ApplicationGenerationStatus
)
from services.application_rag import get_rag_service
from services.deepseek_client import get_deepseek_client
from services.resend_client import get_resend_client

logger = logging.getLogger(__name__)
settings = Settings()

# Create async engine for database operations
engine = create_async_engine(settings.db_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class ApplicationGeneratorTask(Task):
    """Base task class for application generation with error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        logger.error(f"Exception info: {einfo}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} completed successfully")


@celery_app.task(
    bind=True,
    base=ApplicationGeneratorTask,
    name="tasks.generate_grant_application",
    max_retries=3,
    default_retry_delay=60
)
def generate_grant_application(
    self,
    user_id: int,
    grant_id: int,
    business_profile_id: int
) -> Dict[str, Any]:
    """
    Generate AI-powered grant application using RAG.

    Args:
        user_id: User ID
        grant_id: Grant ID
        business_profile_id: Business profile ID

    Returns:
        Dict with generation results
    """
    try:
        # Run async code in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            _generate_application_async(user_id, grant_id, business_profile_id)
        )

        return result

    except Exception as e:
        logger.error(f"Task failed for user {user_id}, grant {grant_id}: {str(e)}")
        # Retry on failure
        raise self.retry(exc=e)


async def _generate_application_async(
    user_id: int,
    grant_id: int,
    business_profile_id: int
) -> Dict[str, Any]:
    """
    Async implementation of application generation.

    Args:
        user_id: User ID
        grant_id: Grant ID
        business_profile_id: Business profile ID

    Returns:
        Generation results dict
    """
    start_time = time.time()
    tokens_used = 0

    async with AsyncSessionLocal() as db:
        try:
            # 1. Load grant details
            grant = await _load_grant(db, grant_id)
            if not grant:
                raise ValueError(f"Grant {grant_id} not found")

            # 2. Load user and business profile
            user = await _load_user(db, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            business_profile = await _load_business_profile(db, business_profile_id)
            if not business_profile:
                raise ValueError(f"Business profile {business_profile_id} not found")

            # 3. Query RAG system for relevant business context
            rag_service = get_rag_service()
            grant_description = _build_grant_query(grant)

            context_chunks = await rag_service.retrieve_relevant_context(
                user_id=user_id,
                query=grant_description,
                top_k=5
            )

            # 4. Build context from RAG results
            business_context = _build_business_context(context_chunks, business_profile)

            # 5. Generate application sections using DeepSeek
            deepseek_client = get_deepseek_client()

            sections = {}
            section_generators = {
                "executive_summary": _generate_executive_summary,
                "needs_statement": _generate_needs_statement,
                "project_description": _generate_project_description,
                "budget_narrative": _generate_budget_narrative,
                "organizational_capacity": _generate_organizational_capacity,
                "impact_statement": _generate_impact_statement
            }

            for section_name, generator_func in section_generators.items():
                try:
                    section_result = await generator_func(
                        deepseek_client=deepseek_client,
                        grant=grant,
                        business_context=business_context
                    )
                    sections[section_name] = section_result["content"]
                    tokens_used += section_result.get("tokens_used", 0)
                except Exception as e:
                    logger.error(f"Failed to generate {section_name}: {str(e)}")
                    sections[section_name] = f"[Generation failed: {str(e)}]"

            # 6. Combine into full application
            full_content = _format_full_application(sections, grant)

            # 7. Save to database
            application = GeneratedApplication(
                user_id=user_id,
                grant_id=grant_id,
                generated_content=full_content,
                sections=sections,
                status=ApplicationGenerationStatus.GENERATED,
                model_used="deepseek-chat",
                generation_time_seconds=time.time() - start_time,
                tokens_used=tokens_used
            )

            db.add(application)

            # 8. Update usage counter
            user.applications_used += 1
            await db.commit()
            await db.refresh(application)

            logger.info(f"Generated application {application.id} for user {user_id}")

            # 9. Send email notification
            try:
                resend_client = get_resend_client()
                await resend_client.send_application_complete_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    grant_title=grant.title,
                    application_id=application.id
                )
                logger.info(f"Application complete email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send email notification: {str(e)}")
                # Don't fail the entire task if email fails

            return {
                "success": True,
                "application_id": application.id,
                "grant_title": grant.title,
                "sections_generated": list(sections.keys()),
                "tokens_used": tokens_used,
                "generation_time": time.time() - start_time
            }

        except Exception as e:
            logger.error(f"Application generation failed: {str(e)}")
            await db.rollback()
            raise


async def _load_grant(db: AsyncSession, grant_id: int) -> Optional[Grant]:
    """Load grant from database."""
    result = await db.execute(
        select(Grant).where(Grant.id == grant_id)
    )
    return result.scalar_one_or_none()


async def _load_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Load user from database."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def _load_business_profile(db: AsyncSession, profile_id: int) -> Optional[BusinessProfile]:
    """Load business profile from database."""
    result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.id == profile_id)
    )
    return result.scalar_one_or_none()


def _build_grant_query(grant: Grant) -> str:
    """Build query text for RAG retrieval."""
    parts = [grant.title]

    if grant.description:
        parts.append(grant.description)

    if grant.summary_llm:
        parts.append(grant.summary_llm)

    if grant.eligibility_summary_llm:
        parts.append(grant.eligibility_summary_llm)

    return " ".join(parts)


def _build_business_context(context_chunks: list, business_profile: BusinessProfile) -> str:
    """Build comprehensive business context from RAG results and profile."""
    parts = []

    # Add RAG-retrieved chunks (most relevant)
    if context_chunks:
        parts.append("=== RELEVANT BUSINESS INFORMATION ===")
        for idx, chunk in enumerate(context_chunks, 1):
            parts.append(f"\n[Context {idx} - Relevance: {chunk.get('score', 0):.2f}]")
            parts.append(chunk.get("text", ""))

    # Add structured profile data
    parts.append("\n=== BUSINESS PROFILE ===")
    parts.append(f"Business Name: {business_profile.business_name}")

    if business_profile.mission_statement:
        parts.append(f"Mission: {business_profile.mission_statement}")

    if business_profile.service_description:
        parts.append(f"Services: {business_profile.service_description}")

    if business_profile.target_sectors:
        sectors = ", ".join(business_profile.target_sectors) if isinstance(business_profile.target_sectors, list) else str(business_profile.target_sectors)
        parts.append(f"Target Sectors: {sectors}")

    if business_profile.revenue_range:
        parts.append(f"Revenue: {business_profile.revenue_range}")

    if business_profile.years_in_operation:
        parts.append(f"Years in Operation: {business_profile.years_in_operation}")

    if business_profile.geographic_focus:
        parts.append(f"Geographic Focus: {business_profile.geographic_focus}")

    if business_profile.team_size:
        parts.append(f"Team Size: {business_profile.team_size}")

    return "\n".join(parts)


async def _generate_executive_summary(
    deepseek_client,
    grant: Grant,
    business_context: str
) -> Dict[str, Any]:
    """Generate executive summary section."""
    system_prompt = """You are an expert grant writer specializing in executive summaries.
    Write compelling, concise summaries that capture the essence of the proposal and why it matters."""

    user_prompt = f"""
    Write an executive summary for this grant application.

    GRANT INFORMATION:
    Title: {grant.title}
    Funder: {grant.funder_name or "N/A"}
    Funding Amount: {grant.funding_amount_display or "Not specified"}
    Description: {grant.description or grant.summary_llm or "N/A"}

    BUSINESS CONTEXT:
    {business_context}

    Write a compelling executive summary (200-300 words) that:
    1. Clearly states the project purpose and goals
    2. Highlights the organization's qualifications
    3. Explains the need being addressed
    4. Summarizes expected outcomes and impact
    5. Makes a strong case for funding

    Write in a professional, persuasive tone. Focus on impact and alignment with the grant's goals.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await deepseek_client.chat_completion(messages, temperature=0.7, max_tokens=800)

    return {
        "content": response["choices"][0]["message"]["content"],
        "tokens_used": response.get("usage", {}).get("total_tokens", 0)
    }


async def _generate_needs_statement(
    deepseek_client,
    grant: Grant,
    business_context: str
) -> Dict[str, Any]:
    """Generate needs statement section."""
    system_prompt = """You are an expert grant writer specializing in needs statements.
    Write compelling narratives that clearly articulate problems and justify funding."""

    user_prompt = f"""
    Write a needs statement for this grant application.

    GRANT INFORMATION:
    Title: {grant.title}
    Description: {grant.description or grant.summary_llm or "N/A"}
    Focus Area: {grant.identified_sector or "General"}

    BUSINESS CONTEXT:
    {business_context}

    Write a comprehensive needs statement (300-400 words) that:
    1. Clearly defines the problem or need
    2. Provides relevant data and evidence
    3. Explains who is affected and how
    4. Demonstrates urgency and importance
    5. Connects the need to your organization's mission

    Use specific examples and data where possible. Be compelling but factual.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await deepseek_client.chat_completion(messages, temperature=0.7, max_tokens=1000)

    return {
        "content": response["choices"][0]["message"]["content"],
        "tokens_used": response.get("usage", {}).get("total_tokens", 0)
    }


async def _generate_project_description(
    deepseek_client,
    grant: Grant,
    business_context: str
) -> Dict[str, Any]:
    """Generate project description section."""
    system_prompt = """You are an expert grant writer specializing in project descriptions.
    Write detailed, actionable project plans that demonstrate feasibility and impact."""

    user_prompt = f"""
    Write a project description for this grant application.

    GRANT INFORMATION:
    Title: {grant.title}
    Description: {grant.description or grant.summary_llm or "N/A"}
    Funding Amount: {grant.funding_amount_display or "Not specified"}

    BUSINESS CONTEXT:
    {business_context}

    Write a comprehensive project description (400-600 words) that:
    1. Describes project goals and objectives (SMART goals)
    2. Outlines activities and timeline
    3. Explains methodology and approach
    4. Details deliverables and milestones
    5. Describes staffing and resources
    6. Explains how success will be measured

    Be specific and detailed. Show that the project is well-planned and achievable.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await deepseek_client.chat_completion(messages, temperature=0.7, max_tokens=1500)

    return {
        "content": response["choices"][0]["message"]["content"],
        "tokens_used": response.get("usage", {}).get("total_tokens", 0)
    }


async def _generate_budget_narrative(
    deepseek_client,
    grant: Grant,
    business_context: str
) -> Dict[str, Any]:
    """Generate budget narrative section."""
    system_prompt = """You are an expert grant writer specializing in budget narratives.
    Write clear, justified budget explanations that demonstrate responsible financial planning."""

    user_prompt = f"""
    Write a budget narrative for this grant application.

    GRANT INFORMATION:
    Title: {grant.title}
    Funding Amount: {grant.funding_amount_display or "Not specified"}
    Description: {grant.description or grant.summary_llm or "N/A"}

    BUSINESS CONTEXT:
    {business_context}

    Write a budget narrative (300-400 words) that:
    1. Breaks down major budget categories (personnel, supplies, equipment, etc.)
    2. Justifies each expense
    3. Shows cost-effectiveness
    4. Explains any matching funds or in-kind contributions
    5. Demonstrates alignment with project goals

    Note: This is a narrative explanation. Actual budget numbers should be determined by the applicant.
    Focus on justifying categories and showing sound financial planning.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await deepseek_client.chat_completion(messages, temperature=0.7, max_tokens=1000)

    return {
        "content": response["choices"][0]["message"]["content"],
        "tokens_used": response.get("usage", {}).get("total_tokens", 0)
    }


async def _generate_organizational_capacity(
    deepseek_client,
    grant: Grant,
    business_context: str
) -> Dict[str, Any]:
    """Generate organizational capacity section."""
    system_prompt = """You are an expert grant writer specializing in organizational capacity statements.
    Write compelling narratives that demonstrate organizational qualifications and readiness."""

    user_prompt = f"""
    Write an organizational capacity statement for this grant application.

    GRANT INFORMATION:
    Title: {grant.title}
    Description: {grant.description or grant.summary_llm or "N/A"}

    BUSINESS CONTEXT:
    {business_context}

    Write an organizational capacity statement (300-400 words) that:
    1. Describes the organization's history and mission
    2. Highlights relevant experience and past successes
    3. Details qualified staff and leadership
    4. Explains organizational structure and governance
    5. Demonstrates financial stability and management
    6. Shows capacity to complete the proposed project

    Emphasize strengths and qualifications. Build confidence in the organization's ability to succeed.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await deepseek_client.chat_completion(messages, temperature=0.7, max_tokens=1000)

    return {
        "content": response["choices"][0]["message"]["content"],
        "tokens_used": response.get("usage", {}).get("total_tokens", 0)
    }


async def _generate_impact_statement(
    deepseek_client,
    grant: Grant,
    business_context: str
) -> Dict[str, Any]:
    """Generate impact statement section."""
    system_prompt = """You are an expert grant writer specializing in impact statements.
    Write compelling narratives about outcomes, benefits, and long-term change."""

    user_prompt = f"""
    Write an impact statement for this grant application.

    GRANT INFORMATION:
    Title: {grant.title}
    Description: {grant.description or grant.summary_llm or "N/A"}
    Focus Area: {grant.identified_sector or "General"}

    BUSINESS CONTEXT:
    {business_context}

    Write an impact statement (300-400 words) that:
    1. Describes expected short-term outcomes
    2. Explains long-term impact and sustainability
    3. Quantifies benefits where possible (people served, lives changed, etc.)
    4. Addresses broader community or systemic impact
    5. Explains evaluation and measurement methods
    6. Describes plans for sustainability beyond the grant period

    Be inspiring but realistic. Focus on measurable outcomes and lasting change.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await deepseek_client.chat_completion(messages, temperature=0.7, max_tokens=1000)

    return {
        "content": response["choices"][0]["message"]["content"],
        "tokens_used": response.get("usage", {}).get("total_tokens", 0)
    }


def _format_full_application(sections: Dict[str, str], grant: Grant) -> str:
    """Format all sections into a complete application document."""
    parts = []

    # Header
    parts.append("=" * 80)
    parts.append(f"GRANT APPLICATION")
    parts.append(f"Grant: {grant.title}")
    if grant.funder_name:
        parts.append(f"Funder: {grant.funder_name}")
    if grant.funding_amount_display:
        parts.append(f"Funding Amount: {grant.funding_amount_display}")
    parts.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    parts.append("=" * 80)
    parts.append("")

    # Sections
    section_titles = {
        "executive_summary": "EXECUTIVE SUMMARY",
        "needs_statement": "NEEDS STATEMENT",
        "project_description": "PROJECT DESCRIPTION",
        "budget_narrative": "BUDGET NARRATIVE",
        "organizational_capacity": "ORGANIZATIONAL CAPACITY",
        "impact_statement": "IMPACT STATEMENT"
    }

    for section_key, section_title in section_titles.items():
        if section_key in sections:
            parts.append("")
            parts.append("-" * 80)
            parts.append(section_title)
            parts.append("-" * 80)
            parts.append("")
            parts.append(sections[section_key])
            parts.append("")

    # Footer
    parts.append("")
    parts.append("=" * 80)
    parts.append("END OF APPLICATION")
    parts.append("=" * 80)

    return "\n".join(parts)
