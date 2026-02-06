"""
API routes for AI-generated grant applications management.
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.auth import get_current_user, check_application_limit
from database.session import get_db
from database.models import User, GeneratedApplication, Grant, BusinessProfile, ApplicationGenerationStatus
from tasks.application_generator import generate_grant_application

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Applications"])


@router.get("/")
async def list_applications(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all generated applications for the current user.

    Args:
        status: Optional filter by status (draft, generated, edited, submitted, awarded, rejected)
        page: Page number (default 1)
        page_size: Items per page (default 20)

    Returns:
        Paginated list of applications
    """
    try:
        query = select(GeneratedApplication).where(
            GeneratedApplication.user_id == current_user.id
        )

        # Filter by status if provided
        if status:
            try:
                status_enum = ApplicationGenerationStatus(status.lower())
                query = query.where(GeneratedApplication.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        # Order by creation date (newest first)
        query = query.order_by(GeneratedApplication.created_at.desc())

        # Get total count
        count_query = select(func.count()).select_from(GeneratedApplication).where(
            GeneratedApplication.user_id == current_user.id
        )
        if status:
            count_query = count_query.where(GeneratedApplication.status == status_enum)

        from sqlalchemy import func
        result = await db.execute(count_query)
        total = result.scalar()

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        applications = result.scalars().all()

        return {
            "data": [app.to_dict() for app in applications],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing applications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list applications")


@router.get("/{application_id}")
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific application by ID.

    Args:
        application_id: Application ID

    Returns:
        Application data
    """
    try:
        result = await db.execute(
            select(GeneratedApplication).where(
                and_(
                    GeneratedApplication.id == application_id,
                    GeneratedApplication.user_id == current_user.id
                )
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Also load grant details
        grant_result = await db.execute(
            select(Grant).where(Grant.id == application.grant_id)
        )
        grant = grant_result.scalar_one_or_none()

        app_dict = application.to_dict()
        if grant:
            app_dict["grant"] = {
                "id": grant.id,
                "title": grant.title,
                "description": grant.description,
                "deadline": grant.deadline.isoformat() if grant.deadline else None,
                "funding_amount_display": grant.funding_amount_display
            }

        return {"data": app_dict}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching application: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch application")


@router.post("/generate")
async def create_application(
    grant_id: int = Body(..., embed=True),
    current_user: User = Depends(check_application_limit),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new application for a grant using AI and RAG.
    This is an async task - returns task ID immediately.

    Args:
        grant_id: Grant ID to generate application for

    Returns:
        Task ID for tracking generation progress
    """
    try:
        # Check if grant exists
        grant_result = await db.execute(
            select(Grant).where(Grant.id == grant_id)
        )
        grant = grant_result.scalar_one_or_none()

        if not grant:
            raise HTTPException(status_code=404, detail="Grant not found")

        # Check if user has business profile
        profile_result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=400,
                detail="Business profile must be created before generating applications"
            )

        # Check if application already exists for this grant
        existing_result = await db.execute(
            select(GeneratedApplication).where(
                and_(
                    GeneratedApplication.user_id == current_user.id,
                    GeneratedApplication.grant_id == grant_id
                )
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            return {
                "message": "Application already exists for this grant",
                "application_id": existing.id,
                "status": "exists"
            }

        # Queue Celery task for generation
        task = generate_grant_application.delay(
            user_id=current_user.id,
            grant_id=grant_id,
            business_profile_id=profile.id
        )

        logger.info(f"Application generation queued for user {current_user.id}, grant {grant_id}, task {task.id}")

        return {
            "message": "Application generation started",
            "task_id": task.id,
            "status": "processing",
            "estimated_time_seconds": 60
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create application")


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check the status of an application generation task.

    Args:
        task_id: Celery task ID

    Returns:
        Task status and result if completed
    """
    try:
        from celery.result import AsyncResult
        task = AsyncResult(task_id)

        if task.ready():
            if task.successful():
                result = task.get()
                return {
                    "status": "completed",
                    "result": result
                }
            else:
                return {
                    "status": "failed",
                    "error": str(task.info)
                }
        else:
            return {
                "status": "processing",
                "progress": task.info if isinstance(task.info, dict) else {}
            }

    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check task status")


@router.put("/{application_id}")
async def update_application(
    application_id: int,
    generated_content: Optional[str] = Body(None),
    sections: Optional[dict] = Body(None),
    status: Optional[str] = Body(None),
    feedback_notes: Optional[str] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an application (edit content, change status, add notes).

    Args:
        application_id: Application ID
        generated_content: Optional full content update
        sections: Optional sections update
        status: Optional status update
        feedback_notes: Optional feedback notes

    Returns:
        Updated application
    """
    try:
        result = await db.execute(
            select(GeneratedApplication).where(
                and_(
                    GeneratedApplication.id == application_id,
                    GeneratedApplication.user_id == current_user.id
                )
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Update fields
        if generated_content is not None:
            application.generated_content = generated_content
            application.last_edited = datetime.utcnow()

        if sections is not None:
            application.sections = sections
            application.last_edited = datetime.utcnow()

        if status is not None:
            try:
                status_enum = ApplicationGenerationStatus(status.lower())
                application.status = status_enum
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        if feedback_notes is not None:
            application.feedback_notes = feedback_notes

        await db.commit()
        await db.refresh(application)

        logger.info(f"Application {application_id} updated by user {current_user.id}")

        return {
            "data": application.to_dict(),
            "message": "Application updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating application: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update application")


@router.post("/{application_id}/regenerate-section")
async def regenerate_section(
    application_id: int,
    section_name: str = Body(..., embed=True),
    feedback: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate a specific section of an application with optional feedback.

    Args:
        application_id: Application ID
        section_name: Section to regenerate (executive_summary, needs_statement, etc.)
        feedback: Optional feedback for improvement

    Returns:
        Updated section content
    """
    try:
        result = await db.execute(
            select(GeneratedApplication).where(
                and_(
                    GeneratedApplication.id == application_id,
                    GeneratedApplication.user_id == current_user.id
                )
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        valid_sections = [
            "executive_summary",
            "needs_statement",
            "project_description",
            "budget_narrative",
            "organizational_capacity",
            "impact_statement"
        ]

        if section_name not in valid_sections:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid section. Must be one of: {', '.join(valid_sections)}"
            )

        # TODO: Implement section regeneration with DeepSeek
        # For now, return a placeholder
        logger.info(f"Section regeneration requested: {section_name} for application {application_id}")

        return {
            "message": "Section regeneration feature coming soon",
            "section_name": section_name,
            "status": "pending_implementation"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating section: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to regenerate section")


@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an application.

    Args:
        application_id: Application ID

    Returns:
        Success message
    """
    try:
        result = await db.execute(
            select(GeneratedApplication).where(
                and_(
                    GeneratedApplication.id == application_id,
                    GeneratedApplication.user_id == current_user.id
                )
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        await db.delete(application)
        await db.commit()

        logger.info(f"Application {application_id} deleted by user {current_user.id}")

        return {"message": "Application deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting application: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete application")


@router.post("/{application_id}/export")
async def export_application(
    application_id: int,
    format: str = Body("pdf", embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export application as PDF or DOCX (placeholder).

    Args:
        application_id: Application ID
        format: Export format (pdf or docx)

    Returns:
        Download URL or file
    """
    try:
        result = await db.execute(
            select(GeneratedApplication).where(
                and_(
                    GeneratedApplication.id == application_id,
                    GeneratedApplication.user_id == current_user.id
                )
            )
        )
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        if format not in ["pdf", "docx"]:
            raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'docx'")

        # TODO: Implement PDF/DOCX generation
        logger.info(f"Export requested: {format} for application {application_id}")

        return {
            "message": "Export feature coming soon",
            "format": format,
            "status": "pending_implementation"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting application: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export application")
