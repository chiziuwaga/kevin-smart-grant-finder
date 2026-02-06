"""
API routes for business profile management with document uploads.
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import mimetypes  # For file type validation by extension
import bleach  # For HTML sanitization (XSS prevention)

from app.auth import get_current_user
from database.session import get_db
from database.models import User, BusinessProfile
from services.application_rag import get_rag_service

logger = logging.getLogger(__name__)


def sanitize_text_input(text: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """
    Sanitize user text input to prevent XSS attacks.
    Removes all HTML tags and attributes.

    Args:
        text: Input text to sanitize
        max_length: Optional maximum length to enforce

    Returns:
        Sanitized text or None if input is None
    """
    if not text:
        return text

    # Strip all HTML tags for text inputs (we don't allow any HTML)
    sanitized = bleach.clean(text, tags=[], strip=True)

    # Enforce max length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized

router = APIRouter(tags=["Business Profile"])


@router.get("/")
async def get_business_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's business profile.

    Returns:
        Business profile data or null if not created yet
    """
    try:
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return {"data": None, "message": "No business profile found"}

        return {
            "data": profile.to_dict(),
            "message": "Business profile retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error fetching business profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch business profile")


@router.post("/")
async def create_or_update_business_profile(
    business_name: str = Form(...),
    mission_statement: Optional[str] = Form(None),
    service_description: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    target_sectors: Optional[str] = Form(None),  # JSON string
    revenue_range: Optional[str] = Form(None),
    years_in_operation: Optional[int] = Form(None),
    geographic_focus: Optional[str] = Form(None),
    team_size: Optional[int] = Form(None),
    narrative_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update business profile.

    Args:
        business_name: Required business name
        mission_statement: Optional mission statement
        service_description: Optional service description
        website_url: Optional website URL
        target_sectors: JSON string array of target sectors
        revenue_range: Optional revenue range (e.g., "100k-500k")
        years_in_operation: Optional years in operation
        geographic_focus: Optional geographic focus
        team_size: Optional team size
        narrative_text: Optional narrative text (max 2000 chars)

    Returns:
        Created or updated business profile
    """
    try:
        # Sanitize all text inputs to prevent XSS
        business_name = sanitize_text_input(business_name, max_length=255)
        mission_statement = sanitize_text_input(mission_statement, max_length=1000)
        service_description = sanitize_text_input(service_description, max_length=2000)
        website_url = sanitize_text_input(website_url, max_length=500)
        revenue_range = sanitize_text_input(revenue_range, max_length=100)
        geographic_focus = sanitize_text_input(geographic_focus, max_length=500)
        narrative_text = sanitize_text_input(narrative_text, max_length=2000)

        # Validate required fields after sanitization
        if not business_name or len(business_name.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Business name is required"
            )

        # Parse target sectors JSON
        import json
        sectors_list = None
        if target_sectors:
            try:
                sectors_list = json.loads(target_sectors)
                # Sanitize each sector string
                if isinstance(sectors_list, list):
                    sectors_list = [sanitize_text_input(s, max_length=100) for s in sectors_list if s]
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid target_sectors JSON")

        # Check if profile exists
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            # Update existing profile
            profile.business_name = business_name
            profile.mission_statement = mission_statement
            profile.service_description = service_description
            profile.website_url = website_url
            profile.target_sectors = sectors_list
            profile.revenue_range = revenue_range
            profile.years_in_operation = years_in_operation
            profile.geographic_focus = geographic_focus
            profile.team_size = team_size
            profile.narrative_text = narrative_text
            profile.updated_at = datetime.utcnow()

            action = "updated"
        else:
            # Create new profile
            profile = BusinessProfile(
                user_id=current_user.id,
                business_name=business_name,
                mission_statement=mission_statement,
                service_description=service_description,
                website_url=website_url,
                target_sectors=sectors_list,
                revenue_range=revenue_range,
                years_in_operation=years_in_operation,
                geographic_focus=geographic_focus,
                team_size=team_size,
                narrative_text=narrative_text
            )
            db.add(profile)
            action = "created"

        await db.commit()
        await db.refresh(profile)

        # Generate embeddings for RAG if narrative provided
        if narrative_text:
            try:
                rag_service = get_rag_service()
                await rag_service.generate_and_store_embeddings(
                    db=db,
                    user_id=current_user.id,
                    business_profile_id=profile.id
                )
                logger.info(f"Generated embeddings for business profile {profile.id}")
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {str(e)}")
                # Don't fail the request if embeddings fail

        return {
            "data": profile.to_dict(),
            "message": f"Business profile {action} successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating business profile: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save business profile")


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a supporting document (PDF, DOCX, TXT).
    Max 10MB total across all documents.

    Args:
        file: Document file to upload

    Returns:
        Document metadata
    """
    try:
        # Check if profile exists
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Business profile must be created before uploading documents"
            )

        # Read file first for content validation
        contents = await file.read()
        file_size = len(contents)

        # Validate file type by extension
        allowed_extensions = [".pdf", ".docx", ".txt"]

        # Check file extension
        if file.filename:
            ext = f".{file.filename.split('.')[-1].lower()}"
            if ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file extension. Only .pdf, .docx, and .txt files are allowed"
                )

        # Check size limit (10MB = 10485760 bytes)
        max_size = 10485760
        current_size = profile.documents_total_size_bytes or 0

        if current_size + file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Total document size would exceed 10MB limit. Current: {current_size / 1048576:.2f}MB, File: {file_size / 1048576:.2f}MB"
            )

        # For demo, we'll store metadata only
        # In production, upload to S3, GCS, or similar
        import hashlib
        file_hash = hashlib.md5(contents).hexdigest()

        # Add document metadata
        if not profile.uploaded_documents:
            profile.uploaded_documents = []

        document_metadata = {
            "filename": file.filename,
            "size": file_size,
            "content_type": file.content_type,
            "hash": file_hash,
            "uploaded_at": datetime.utcnow().isoformat(),
            "url": f"/api/documents/{file_hash}"  # Placeholder
        }

        # Ensure it's a list and append
        docs = profile.uploaded_documents if isinstance(profile.uploaded_documents, list) else []
        docs.append(document_metadata)
        profile.uploaded_documents = docs

        # Update total size
        profile.documents_total_size_bytes = current_size + file_size

        await db.commit()
        await db.refresh(profile)

        logger.info(f"Document uploaded for user {current_user.id}: {file.filename}")

        return {
            "data": document_metadata,
            "message": "Document uploaded successfully",
            "total_size_mb": profile.documents_total_size_bytes / 1048576
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upload document")


@router.delete("/documents/{file_hash}")
async def delete_document(
    file_hash: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document by its hash.

    Args:
        file_hash: MD5 hash of the document

    Returns:
        Success message
    """
    try:
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile or not profile.uploaded_documents:
            raise HTTPException(status_code=404, detail="Document not found")

        # Find and remove document
        docs = profile.uploaded_documents
        document_found = None
        new_docs = []

        for doc in docs:
            if doc.get("hash") == file_hash:
                document_found = doc
            else:
                new_docs.append(doc)

        if not document_found:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update profile
        profile.uploaded_documents = new_docs
        profile.documents_total_size_bytes = sum(doc.get("size", 0) for doc in new_docs)

        await db.commit()

        logger.info(f"Document deleted for user {current_user.id}: {document_found.get('filename')}")

        return {
            "message": "Document deleted successfully",
            "deleted_file": document_found.get("filename")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all uploaded documents for the current user.

    Returns:
        List of document metadata
    """
    try:
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return {"data": [], "total_size_mb": 0}

        docs = profile.uploaded_documents or []
        total_size = profile.documents_total_size_bytes or 0

        return {
            "data": docs,
            "total_size_mb": total_size / 1048576,
            "count": len(docs)
        }

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list documents")
