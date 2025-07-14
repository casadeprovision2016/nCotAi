"""
Team Notifications Tasks
Celery tasks for team notification automation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.celery import celery_app


@celery_app.task
async def send_team_notification(
    provider: str,
    channel_id: str,
    message: str,
    user_id: str,
    message_type: str = "text",
    title: Optional[str] = None,
    color: Optional[str] = None,
    fields: Optional[List[Dict[str, str]]] = None,
    buttons: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Send notification to team channel.

    Args:
        provider: Team notification provider (slack, teams)
        channel_id: Channel ID to send message to
        message: Message content
        user_id: User ID for authentication
        message_type: Type of message (text, rich, card)
        title: Message title for rich messages
        color: Message color for rich messages
        fields: Additional fields for rich messages
        buttons: Action buttons for rich messages

    Returns:
        Dict containing send status
    """
    try:
        from app.services.team_notifications_integration_service import TeamNotificationsIntegrationService
        from app.db.session import SessionLocal
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize team notifications service
            team_service = TeamNotificationsIntegrationService(db)
            
            if message_type == "rich" and title:
                # Send rich message
                result = await team_service.send_rich_message(
                    provider=provider,
                    channel_id=channel_id,
                    title=title,
                    message=message,
                    color=color,
                    fields=fields,
                    buttons=buttons,
                    user_id=user_id
                )
            else:
                # Send text message
                result = await team_service.send_message(
                    provider=provider,
                    channel_id=channel_id,
                    message=message,
                    user_id=user_id
                )
            
            if result.get("success"):
                return {
                    "status": "sent",
                    "provider": provider,
                    "channel_id": channel_id,
                    "message_type": message_type,
                    "message_id": result.get("message_id"),
                    "timestamp": result.get("timestamp"),
                    "sent_at": datetime.utcnow().isoformat(),
                    "result": result
                }
            else:
                return {
                    "status": "failed",
                    "error": result.get("error", "Unknown error"),
                    "provider": provider,
                    "channel_id": channel_id,
                    "failed_at": datetime.utcnow().isoformat(),
                }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "provider": provider,
            "channel_id": channel_id,
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def send_workflow_notification(
    workflow_type: str,
    data: Dict[str, Any],
    channels: List[Dict[str, str]],
    user_id: str
) -> Dict[str, Any]:
    """
    Send workflow-specific notification to multiple channels.

    Args:
        workflow_type: Type of workflow (tender_alert, deadline_reminder, status_update)
        data: Workflow data
        channels: List of channel configurations with provider and channel_id
        user_id: User ID for authentication

    Returns:
        Dict containing send status for all channels
    """
    try:
        from app.services.team_notifications_integration_service import TeamNotificationsIntegrationService
        from app.db.session import SessionLocal
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize team notifications service
            team_service = TeamNotificationsIntegrationService(db)
            
            notification_results = []
            
            for channel_config in channels:
                provider = channel_config.get("provider")
                channel_id = channel_config.get("channel_id")
                
                if not provider or not channel_id:
                    notification_results.append({
                        "provider": provider,
                        "channel_id": channel_id,
                        "status": "failed",
                        "error": "Missing provider or channel_id"
                    })
                    continue
                
                # Send workflow notification
                result = await team_service.send_workflow_notification(
                    provider=provider,
                    workflow_type=workflow_type,
                    channel_id=channel_id,
                    data=data,
                    user_id=user_id
                )
                
                notification_results.append({
                    "provider": provider,
                    "channel_id": channel_id,
                    "status": "sent" if result.get("success") else "failed",
                    "message_id": result.get("message_id"),
                    "error": result.get("error"),
                    "result": result
                })
            
            successful_notifications = sum(1 for r in notification_results if r.get("status") == "sent")
            
            return {
                "status": "completed",
                "workflow_type": workflow_type,
                "channels_targeted": len(channels),
                "successful_notifications": successful_notifications,
                "failed_notifications": len(channels) - successful_notifications,
                "notification_results": notification_results,
                "sent_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "workflow_type": workflow_type,
            "channels_count": len(channels),
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def create_project_channels(
    project_id: str,
    project_name: str,
    providers: List[str],
    members: List[str],
    user_id: str
) -> Dict[str, Any]:
    """
    Create dedicated channels for a project across multiple platforms.

    Args:
        project_id: Project ID
        project_name: Project name
        providers: List of providers to create channels in
        members: List of team member IDs to add to channels
        user_id: User ID for authentication

    Returns:
        Dict containing channel creation status
    """
    try:
        from app.services.team_notifications_integration_service import TeamNotificationsIntegrationService
        from app.db.session import SessionLocal
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize team notifications service
            team_service = TeamNotificationsIntegrationService(db)
            
            channel_results = []
            
            for provider in providers:
                # Create channel name (lowercase, no spaces)
                channel_name = f"cotai-{project_name.lower().replace(' ', '-')}-{project_id[:8]}"
                description = f"COTAI project channel for {project_name}"
                
                # Create channel
                result = await team_service.create_channel(
                    provider=provider,
                    channel_name=channel_name,
                    description=description,
                    is_private=False,
                    members=members,
                    user_id=user_id
                )
                
                if result.get("success"):
                    # Send welcome message to new channel
                    welcome_message = f"🎉 Welcome to the {project_name} project channel!\n\nThis channel will be used for project updates, notifications, and team collaboration."
                    
                    welcome_result = await team_service.send_message(
                        provider=provider,
                        channel_id=result.get("channel_id"),
                        message=welcome_message,
                        user_id=user_id
                    )
                    
                    channel_results.append({
                        "provider": provider,
                        "status": "created",
                        "channel_id": result.get("channel_id"),
                        "channel_name": channel_name,
                        "channel_url": result.get("channel_url"),
                        "welcome_sent": welcome_result.get("success", False),
                        "result": result
                    })
                else:
                    channel_results.append({
                        "provider": provider,
                        "status": "failed",
                        "channel_name": channel_name,
                        "error": result.get("error"),
                        "result": result
                    })
            
            successful_channels = sum(1 for r in channel_results if r.get("status") == "created")
            
            return {
                "status": "completed",
                "project_id": project_id,
                "project_name": project_name,
                "providers_targeted": len(providers),
                "successful_channels": successful_channels,
                "failed_channels": len(providers) - successful_channels,
                "channel_results": channel_results,
                "created_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "project_id": project_id,
            "project_name": project_name,
            "providers_count": len(providers),
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def send_file_to_channels(
    file_url: str,
    filename: str,
    channels: List[Dict[str, str]],
    user_id: str,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send file to multiple team channels.

    Args:
        file_url: URL of file to send
        filename: Name of the file
        channels: List of channel configurations with provider and channel_id
        user_id: User ID for authentication
        comment: Optional comment to accompany the file

    Returns:
        Dict containing send status for all channels
    """
    try:
        from app.services.team_notifications_integration_service import TeamNotificationsIntegrationService
        from app.db.session import SessionLocal
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize team notifications service
            team_service = TeamNotificationsIntegrationService(db)
            
            file_results = []
            
            for channel_config in channels:
                provider = channel_config.get("provider")
                channel_id = channel_config.get("channel_id")
                
                if not provider or not channel_id:
                    file_results.append({
                        "provider": provider,
                        "channel_id": channel_id,
                        "status": "failed",
                        "error": "Missing provider or channel_id"
                    })
                    continue
                
                # Send file to channel
                result = await team_service.send_file(
                    provider=provider,
                    channel_id=channel_id,
                    file_url=file_url,
                    filename=filename,
                    comment=comment,
                    user_id=user_id
                )
                
                file_results.append({
                    "provider": provider,
                    "channel_id": channel_id,
                    "status": "sent" if result.get("success") else "failed",
                    "file_id": result.get("file_id"),
                    "error": result.get("error"),
                    "result": result
                })
            
            successful_sends = sum(1 for r in file_results if r.get("status") == "sent")
            
            return {
                "status": "completed",
                "filename": filename,
                "file_url": file_url,
                "channels_targeted": len(channels),
                "successful_sends": successful_sends,
                "failed_sends": len(channels) - successful_sends,
                "file_results": file_results,
                "sent_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "filename": filename,
            "channels_count": len(channels),
            "failed_at": datetime.utcnow().isoformat(),
        }


@celery_app.task
async def send_daily_team_digest(
    team_channels: Dict[str, List[Dict[str, str]]],
    user_id: str
) -> Dict[str, Any]:
    """
    Send daily digest to team channels.

    Args:
        team_channels: Dict mapping digest type to list of channel configurations
        user_id: User ID for authentication

    Returns:
        Dict containing digest send status
    """
    try:
        from app.services.team_notifications_integration_service import TeamNotificationsIntegrationService
        from app.db.session import SessionLocal
        from datetime import datetime, timedelta
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Initialize team notifications service
            team_service = TeamNotificationsIntegrationService(db)
            
            # Generate digest content (this would typically query the database)
            yesterday = datetime.utcnow() - timedelta(days=1)
            digest_data = {
                "date": yesterday.strftime("%Y-%m-%d"),
                "new_tenders": 5,  # Placeholder data
                "deadlines_approaching": 3,
                "quotations_completed": 8,
                "team_activity": 15,
                "top_opportunities": [
                    {"title": "Construção de escola", "value": "R$ 2.5M", "deadline": "15 dias"},
                    {"title": "Fornecimento de equipamentos", "value": "R$ 800K", "deadline": "8 dias"},
                    {"title": "Serviços de consultoria", "value": "R$ 300K", "deadline": "12 dias"},
                ]
            }
            
            digest_results = []
            
            # Send digest to different types of channels
            for digest_type, channels in team_channels.items():
                for channel_config in channels:
                    provider = channel_config.get("provider")
                    channel_id = channel_config.get("channel_id")
                    
                    if not provider or not channel_id:
                        digest_results.append({
                            "digest_type": digest_type,
                            "provider": provider,
                            "channel_id": channel_id,
                            "status": "failed",
                            "error": "Missing provider or channel_id"
                        })
                        continue
                    
                    # Format digest message based on type
                    if digest_type == "executive":
                        title = "📊 COTAI - Resumo Executivo Diário"
                        message = f"""**Resumo do dia {digest_data['date']}**

🔍 **Novas licitações identificadas:** {digest_data['new_tenders']}
⏰ **Prazos se aproximando:** {digest_data['deadlines_approaching']}
✅ **Cotações finalizadas:** {digest_data['quotations_completed']}
👥 **Atividade da equipe:** {digest_data['team_activity']} ações

**🎯 Top 3 Oportunidades:**"""
                        
                        for i, opp in enumerate(digest_data['top_opportunities'], 1):
                            message += f"\n{i}. {opp['title']} - {opp['value']} (prazo: {opp['deadline']})"
                    
                    elif digest_type == "operational":
                        title = "⚙️ COTAI - Resumo Operacional"
                        message = f"""**Atividades do dia {digest_data['date']}**

📋 Licitações processadas: {digest_data['new_tenders']}
🔄 Cotações em andamento: {digest_data['quotations_completed']}
⚠️ Alertas de prazo: {digest_data['deadlines_approaching']}

Acesse o sistema para mais detalhes."""
                    
                    else:  # general
                        title = "📈 COTAI - Resumo Diário"
                        message = f"""**Resumo do dia {digest_data['date']}**

Hoje foram identificadas {digest_data['new_tenders']} novas oportunidades e finalizadas {digest_data['quotations_completed']} cotações.

{digest_data['deadlines_approaching']} prazos estão se aproximando - verifique sua agenda!"""
                    
                    # Send digest
                    result = await team_service.send_rich_message(
                        provider=provider,
                        channel_id=channel_id,
                        title=title,
                        message=message,
                        color="#2E8B57",  # Sea green
                        user_id=user_id
                    )
                    
                    digest_results.append({
                        "digest_type": digest_type,
                        "provider": provider,
                        "channel_id": channel_id,
                        "status": "sent" if result.get("success") else "failed",
                        "message_id": result.get("message_id"),
                        "error": result.get("error"),
                        "result": result
                    })
            
            successful_digests = sum(1 for r in digest_results if r.get("status") == "sent")
            total_channels = sum(len(channels) for channels in team_channels.values())
            
            return {
                "status": "completed",
                "digest_date": digest_data['date'],
                "total_channels": total_channels,
                "successful_digests": successful_digests,
                "failed_digests": total_channels - successful_digests,
                "digest_data": digest_data,
                "digest_results": digest_results,
                "sent_at": datetime.utcnow().isoformat(),
            }
                
        finally:
            db.close()

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "failed_at": datetime.utcnow().isoformat(),
        }