"""
Cloud Storage Tasks
Celery tasks for cloud storage operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.celery import celery_app


@celery_app.task
async def sync_file_to_cloud(
    file_path: str,
    provider: str,
    remote_path: str,
    user_id: str,
    sync_direction: str = "upload",
    delete_local: bool = False
) -> Dict[str, Any]:
    """
    Sync file to cloud storage provider.

    Args:
        file_path: Local file path
        provider: Cloud storage provider (google_drive, dropbox)
        remote_path: Remote file path
        user_id: User ID for authentication
        sync_direction: Direction of sync (upload, download, bidirectional)
        delete_local: Whether to delete local file after upload

    Returns:
        Dict containing sync status
    """
    try:
        from app.services.cloud_storage_integration_service import CloudStorageIntegrationService
        from app.db.session import SessionLocal
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize cloud storage service
            storage_service = CloudStorageIntegrationService(db)
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = file_path.split('/')[-1]
            
            # Upload file to cloud storage
            result = await storage_service.upload_file(
                provider=provider,
                file_content=file_content,
                filename=filename,
                folder_path=remote_path,
                user_id=user_id
            )
            
            if result.get("success") and delete_local:
                import os
                os.remove(file_path)
            
            return {
                "status": "completed",
                "file_path": file_path,
                "provider": provider,
                "remote_path": remote_path,
                "file_id": result.get("file_id"),
                "file_url": result.get("file_url"),
                "deleted_local": delete_local and result.get("success"),
                "synced_at": datetime.utcnow().isoformat(),
                "result": result
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "file_path": file_path,
            "provider": provider,
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def backup_files_to_cloud(
    files: List[Dict[str, str]],
    provider: str,
    backup_folder: str,
    user_id: str,
    compress: bool = True
) -> Dict[str, Any]:
    """
    Backup multiple files to cloud storage.

    Args:
        files: List of file dictionaries with 'path' and 'name' keys
        provider: Cloud storage provider
        backup_folder: Remote backup folder path
        user_id: User ID for authentication
        compress: Whether to compress files before backup

    Returns:
        Dict containing backup status
    """
    try:
        from app.services.cloud_storage_integration_service import CloudStorageIntegrationService
        from app.db.session import SessionLocal
        import zipfile
        import tempfile
        import os
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize cloud storage service
            storage_service = CloudStorageIntegrationService(db)
            
            backup_results = []
            
            if compress and len(files) > 1:
                # Create compressed archive
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for file_info in files:
                            file_path = file_info.get('path')
                            file_name = file_info.get('name', os.path.basename(file_path))
                            
                            if os.path.exists(file_path):
                                zipf.write(file_path, file_name)
                    
                    # Upload compressed archive
                    with open(temp_zip.name, 'rb') as f:
                        archive_content = f.read()
                    
                    archive_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
                    
                    result = await storage_service.upload_file(
                        provider=provider,
                        file_content=archive_content,
                        filename=archive_name,
                        folder_path=backup_folder,
                        user_id=user_id
                    )
                    
                    backup_results.append({
                        "type": "archive",
                        "filename": archive_name,
                        "file_count": len(files),
                        "result": result
                    })
                    
                    # Clean up temp file
                    os.unlink(temp_zip.name)
            else:
                # Upload files individually
                for file_info in files:
                    file_path = file_info.get('path')
                    file_name = file_info.get('name', os.path.basename(file_path))
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        result = await storage_service.upload_file(
                            provider=provider,
                            file_content=file_content,
                            filename=file_name,
                            folder_path=backup_folder,
                            user_id=user_id
                        )
                        
                        backup_results.append({
                            "type": "individual",
                            "filename": file_name,
                            "file_path": file_path,
                            "result": result
                        })
            
            successful_backups = sum(1 for r in backup_results if r.get("result", {}).get("success"))
            
            return {
                "status": "completed",
                "provider": provider,
                "backup_folder": backup_folder,
                "files_processed": len(files),
                "successful_backups": successful_backups,
                "compressed": compress and len(files) > 1,
                "backup_results": backup_results,
                "backed_up_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "provider": provider,
            "backup_folder": backup_folder,
            "files_count": len(files),
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def cleanup_old_cloud_files(
    provider: str,
    folder_path: str,
    days_old: int,
    user_id: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Cleanup old files from cloud storage.

    Args:
        provider: Cloud storage provider
        folder_path: Folder path to cleanup
        days_old: Delete files older than this many days
        user_id: User ID for authentication
        dry_run: If True, only list files to be deleted without deleting

    Returns:
        Dict containing cleanup status
    """
    try:
        from app.services.cloud_storage_integration_service import CloudStorageIntegrationService
        from app.db.session import SessionLocal
        from datetime import datetime, timedelta
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize cloud storage service
            storage_service = CloudStorageIntegrationService(db)
            
            # List files in folder
            list_result = await storage_service.list_files(
                provider=provider,
                folder_id=folder_path,
                limit=1000,  # Process in batches for large folders
                user_id=user_id
            )
            
            if not list_result.get("success"):
                return {
                    "status": "failed",
                    "error": "Failed to list files",
                    "provider": provider,
                    "folder_path": folder_path,
                    "failed_at": datetime.utcnow().isoformat(),
                }
            
            files = list_result.get("files", [])
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            old_files = []
            for file_info in files:
                file_date = file_info.get("modified_time") or file_info.get("created_time")
                if file_date and datetime.fromisoformat(file_date.replace('Z', '+00:00')) < cutoff_date:
                    old_files.append(file_info)
            
            deletion_results = []
            
            if not dry_run:
                # Delete old files
                for file_info in old_files:
                    file_id = file_info.get("id")
                    if file_id:
                        delete_result = await storage_service.delete_file(
                            provider=provider,
                            file_id=file_id,
                            user_id=user_id
                        )
                        
                        deletion_results.append({
                            "file_id": file_id,
                            "filename": file_info.get("name"),
                            "deleted": delete_result.get("success", False),
                            "error": delete_result.get("error")
                        })
            
            successful_deletions = sum(1 for r in deletion_results if r.get("deleted"))
            
            return {
                "status": "completed",
                "provider": provider,
                "folder_path": folder_path,
                "days_old": days_old,
                "dry_run": dry_run,
                "total_files": len(files),
                "old_files_found": len(old_files),
                "files_deleted": successful_deletions if not dry_run else 0,
                "old_files": [f.get("name") for f in old_files] if dry_run else [],
                "deletion_results": deletion_results,
                "cleaned_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "provider": provider,
            "folder_path": folder_path,
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def sync_folder_to_cloud(
    local_folder: str,
    provider: str,
    remote_folder: str,
    user_id: str,
    sync_direction: str = "upload",
    exclude_patterns: List[str] = None
) -> Dict[str, Any]:
    """
    Sync entire folder to cloud storage.

    Args:
        local_folder: Local folder path
        provider: Cloud storage provider
        remote_folder: Remote folder path
        user_id: User ID for authentication
        sync_direction: Direction of sync (upload, download, bidirectional)
        exclude_patterns: List of patterns to exclude (e.g., '*.tmp', '.git/*')

    Returns:
        Dict containing sync status
    """
    try:
        from app.services.cloud_storage_integration_service import CloudStorageIntegrationService
        from app.db.session import SessionLocal
        import os
        import fnmatch
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize cloud storage service
            storage_service = CloudStorageIntegrationService(db)
            
            exclude_patterns = exclude_patterns or []
            sync_results = []
            
            # Walk through local folder
            for root, dirs, files in os.walk(local_folder):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, local_folder)
                    
                    # Check if file should be excluded
                    should_exclude = False
                    for pattern in exclude_patterns:
                        if fnmatch.fnmatch(relative_path, pattern):
                            should_exclude = True
                            break
                    
                    if should_exclude:
                        continue
                    
                    # Upload file
                    with open(local_file_path, 'rb') as f:
                        file_content = f.read()
                    
                    remote_file_path = f"{remote_folder.rstrip('/')}/{relative_path}".replace(os.sep, '/')
                    folder_path = '/'.join(remote_file_path.split('/')[:-1])
                    
                    result = await storage_service.upload_file(
                        provider=provider,
                        file_content=file_content,
                        filename=file,
                        folder_path=folder_path,
                        user_id=user_id
                    )
                    
                    sync_results.append({
                        "local_path": local_file_path,
                        "remote_path": remote_file_path,
                        "filename": file,
                        "success": result.get("success", False),
                        "file_id": result.get("file_id"),
                        "error": result.get("error")
                    })
            
            successful_syncs = sum(1 for r in sync_results if r.get("success"))
            
            return {
                "status": "completed",
                "local_folder": local_folder,
                "provider": provider,
                "remote_folder": remote_folder,
                "sync_direction": sync_direction,
                "total_files": len(sync_results),
                "successful_syncs": successful_syncs,
                "failed_syncs": len(sync_results) - successful_syncs,
                "exclude_patterns": exclude_patterns,
                "sync_results": sync_results,
                "synced_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "local_folder": local_folder,
            "provider": provider,
            "remote_folder": remote_folder,
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def download_file_from_cloud(
    provider: str,
    file_id: str,
    local_path: str,
    user_id: str,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Download file from cloud storage.

    Args:
        provider: Cloud storage provider
        file_id: Remote file ID
        local_path: Local file path to save
        user_id: User ID for authentication
        overwrite: Whether to overwrite existing local file

    Returns:
        Dict containing download status
    """
    try:
        from app.services.cloud_storage_integration_service import CloudStorageIntegrationService
        from app.db.session import SessionLocal
        import os
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Check if local file exists
            if os.path.exists(local_path) and not overwrite:
                return {
                    "status": "skipped",
                    "reason": "File exists and overwrite is False",
                    "provider": provider,
                    "file_id": file_id,
                    "local_path": local_path,
                    "skipped_at": datetime.utcnow().isoformat(),
                }
            
            # Initialize cloud storage service
            storage_service = CloudStorageIntegrationService(db)
            
            # Download file
            result = await storage_service.download_file(
                provider=provider,
                file_id=file_id,
                user_id=user_id
            )
            
            if not result.get("success"):
                return {
                    "status": "failed",
                    "error": result.get("error", "Download failed"),
                    "provider": provider,
                    "file_id": file_id,
                    "failed_at": datetime.utcnow().isoformat(),
                }
            
            # Create local directory if it doesn't exist
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Save file locally
            file_content = result.get("content")
            if file_content:
                with open(local_path, 'wb') as f:
                    f.write(file_content)
            else:
                # If content is not returned directly, use download URL
                download_url = result.get("download_url")
                if download_url:
                    import requests
                    response = requests.get(download_url)
                    response.raise_for_status()
                    
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                else:
                    raise Exception("No file content or download URL provided")
            
            return {
                "status": "completed",
                "provider": provider,
                "file_id": file_id,
                "local_path": local_path,
                "filename": result.get("filename"),
                "file_size": result.get("size"),
                "overwritten": os.path.exists(local_path) and overwrite,
                "downloaded_at": datetime.utcnow().isoformat(),
                "result": result
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "provider": provider,
            "file_id": file_id,
            "local_path": local_path,
            "failed_at": datetime.utcnow().isoformat(),
        }