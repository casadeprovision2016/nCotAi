"""
File upload and management endpoints
"""

import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.core.config import settings
from app.models.user import User

router = APIRouter()

# Ensure upload directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types and sizes
ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
    "rtf",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "tiff",
    "zip",
    "rar",
    "7z",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Check file extension
    if file.filename:
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a single file."""

    validate_file(file)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = file.filename.split(".")[-1].lower() if file.filename else "bin"
    filename = f"{file_id}.{file_extension}"

    # Create category subdirectory
    category_dir = UPLOAD_DIR / category
    category_dir.mkdir(exist_ok=True)

    file_path = category_dir / filename

    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Return file info
        return {
            "id": file_id,
            "filename": file.filename,
            "original_name": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "content_type": file.content_type,
            "category": category,
            "description": description,
            "uploaded_by": current_user.id,
            "url": f"/api/v1/files/download/{file_id}",
        }

    except Exception as e:
        # Clean up file if something went wrong
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}",
        )


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    category: str = Form(default="general"),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple files."""

    if len(files) > 10:  # Limit to 10 files at once
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many files. Maximum 10 files per request.",
        )

    uploaded_files = []
    errors = []

    for file in files:
        try:
            validate_file(file)

            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = (
                file.filename.split(".")[-1].lower() if file.filename else "bin"
            )
            filename = f"{file_id}.{file_extension}"

            # Create category subdirectory
            category_dir = UPLOAD_DIR / category
            category_dir.mkdir(exist_ok=True)

            file_path = category_dir / filename

            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            uploaded_files.append(
                {
                    "id": file_id,
                    "filename": file.filename,
                    "original_name": file.filename,
                    "file_path": str(file_path),
                    "file_size": len(content),
                    "content_type": file.content_type,
                    "category": category,
                    "description": description,
                    "uploaded_by": current_user.id,
                    "url": f"/api/v1/files/download/{file_id}",
                    "status": "success",
                }
            )

        except HTTPException as e:
            errors.append(
                {"filename": file.filename, "error": e.detail, "status": "error"}
            )
        except Exception as e:
            errors.append(
                {"filename": file.filename, "error": str(e), "status": "error"}
            )

    return {
        "uploaded_files": uploaded_files,
        "errors": errors,
        "total_uploaded": len(uploaded_files),
        "total_errors": len(errors),
    }


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Download a file by ID."""

    # Search for file in all category directories
    for category_dir in UPLOAD_DIR.iterdir():
        if category_dir.is_dir():
            for file_path in category_dir.glob(f"{file_id}.*"):
                if file_path.is_file():
                    from fastapi.responses import FileResponse

                    return FileResponse(
                        path=file_path,
                        filename=file_path.name,
                        media_type="application/octet-stream",
                    )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a file by ID."""

    # Search for file in all category directories
    for category_dir in UPLOAD_DIR.iterdir():
        if category_dir.is_dir():
            for file_path in category_dir.glob(f"{file_id}.*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        return {"message": "File deleted successfully"}
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error deleting file: {str(e)}",
                        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


@router.get("/list/{category}")
async def list_files_by_category(
    category: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """List files in a specific category."""

    category_dir = UPLOAD_DIR / category
    if not category_dir.exists():
        return {"files": [], "total": 0}

    files = []
    for file_path in category_dir.iterdir():
        if file_path.is_file():
            file_id = file_path.stem
            stat = file_path.stat()
            files.append(
                {
                    "id": file_id,
                    "filename": file_path.name,
                    "file_size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime,
                    "category": category,
                    "url": f"/api/v1/files/download/{file_id}",
                }
            )

    # Sort by creation time (newest first)
    files.sort(key=lambda x: x["created_at"], reverse=True)

    # Apply pagination
    total = len(files)
    files = files[skip : skip + limit]

    return {"files": files, "total": total, "skip": skip, "limit": limit}


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
):
    """List all file categories."""

    categories = []
    for category_dir in UPLOAD_DIR.iterdir():
        if category_dir.is_dir():
            file_count = len([f for f in category_dir.iterdir() if f.is_file()])
            categories.append({"name": category_dir.name, "file_count": file_count})

    return {"categories": categories}


@router.get("/stats")
async def get_file_stats(
    current_user: User = Depends(get_current_user),
):
    """Get file storage statistics."""

    total_files = 0
    total_size = 0
    categories = {}

    for category_dir in UPLOAD_DIR.iterdir():
        if category_dir.is_dir():
            category_files = 0
            category_size = 0

            for file_path in category_dir.iterdir():
                if file_path.is_file():
                    category_files += 1
                    category_size += file_path.stat().st_size

            total_files += category_files
            total_size += category_size

            categories[category_dir.name] = {
                "file_count": category_files,
                "total_size": category_size,
            }

    return {
        "total_files": total_files,
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "categories": categories,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
    }
