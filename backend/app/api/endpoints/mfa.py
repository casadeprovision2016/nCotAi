"""
Multi-Factor Authentication (MFA) endpoints
"""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.core.auth import get_current_user
from app.core.security import (
    generate_backup_codes,
    generate_mfa_secret,
    generate_qr_code_image,
    hash_backup_codes,
    verify_backup_code,
    verify_totp_code,
)
from app.models.user import User
from app.services.mfa_service import MFAService

router = APIRouter()


# Pydantic models
class MFASetupRequest(BaseModel):
    password: str  # Current password for verification


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    code: str


class MFAEnableRequest(BaseModel):
    code: str
    backup_codes_confirmed: bool = True


class MFADisableRequest(BaseModel):
    password: str
    code: str


class MFARecoveryRequest(BaseModel):
    backup_code: str


class MFARegenerateCodesRequest(BaseModel):
    code: str


@router.get("/status")
async def get_mfa_status(current_user: User = Depends(get_current_user)):
    """Get current MFA status for user."""
    return {
        "enabled": current_user.mfa_enabled,
        "has_backup_codes": bool(current_user.backup_codes),
        "setup_required": not current_user.mfa_enabled,
    }


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: MFASetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiate MFA setup process."""

    mfa_service = MFAService(db)

    try:
        # Verify current password
        if not mfa_service.verify_password(current_user, request.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta"
            )

        # Generate MFA secret and QR code
        secret = generate_mfa_secret()
        qr_code = generate_qr_code_image(secret, current_user.email, "COTAI")

        # Generate backup codes
        backup_codes = generate_backup_codes()

        # Store temporary secret (not enabled yet)
        current_user.mfa_secret = secret
        db.commit()

        return MFASetupResponse(
            secret=secret, qr_code=qr_code, backup_codes=backup_codes
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao configurar MFA: {str(e)}",
        )


@router.post("/verify")
async def verify_mfa_code(
    request: MFAVerifyRequest, current_user: User = Depends(get_current_user)
):
    """Verify MFA code during setup."""

    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA não foi configurado. Execute /setup primeiro.",
        )

    # Verify TOTP code
    is_valid = verify_totp_code(current_user.mfa_secret, request.code)

    return {
        "valid": is_valid,
        "message": "Código válido" if is_valid else "Código inválido",
    }


@router.post("/enable")
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable MFA for user after verification."""

    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="MFA já está habilitado"
        )

    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA não foi configurado. Execute /setup primeiro.",
        )

    # Verify TOTP code
    if not verify_totp_code(current_user.mfa_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Código MFA inválido"
        )

    try:
        # Generate and store backup codes
        backup_codes = generate_backup_codes()
        hashed_codes = hash_backup_codes(backup_codes)

        # Enable MFA
        current_user.mfa_enabled = True
        current_user.backup_codes = json.dumps(hashed_codes)

        db.commit()

        # Log security event
        mfa_service = MFAService(db)
        await mfa_service.log_security_event(
            user_id=current_user.id, action="MFA_ENABLED", details={"method": "TOTP"}
        )

        return {"message": "MFA habilitado com sucesso", "backup_codes": backup_codes}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao habilitar MFA: {str(e)}",
        )


@router.post("/disable")
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable MFA for user."""

    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="MFA não está habilitado"
        )

    mfa_service = MFAService(db)

    try:
        # Verify current password
        if not mfa_service.verify_password(current_user, request.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta"
            )

        # Verify MFA code
        if not verify_totp_code(current_user.mfa_secret, request.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Código MFA inválido"
            )

        # Disable MFA
        current_user.mfa_enabled = False
        current_user.mfa_secret = None
        current_user.backup_codes = None

        db.commit()

        # Log security event
        await mfa_service.log_security_event(
            user_id=current_user.id, action="MFA_DISABLED", details={"method": "manual"}
        )

        return {"message": "MFA desabilitado com sucesso"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao desabilitar MFA: {str(e)}",
        )


@router.post("/recovery")
async def recover_with_backup_code(
    request: MFARecoveryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recover access using backup code."""

    if not current_user.mfa_enabled or not current_user.backup_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA não está configurado ou não há códigos de backup",
        )

    try:
        # Load backup codes
        hashed_codes = json.loads(current_user.backup_codes)

        # Verify backup code
        if not verify_backup_code(request.backup_code, hashed_codes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de backup inválido",
            )

        # Remove used backup code
        for i, hashed_code in enumerate(hashed_codes):
            normalized_code = request.backup_code.replace("-", "").upper()
            if mfa_service.verify_password_hash(normalized_code, hashed_code):
                hashed_codes.pop(i)
                break

        # Update backup codes
        current_user.backup_codes = json.dumps(hashed_codes)
        db.commit()

        # Log security event
        mfa_service = MFAService(db)
        await mfa_service.log_security_event(
            user_id=current_user.id,
            action="MFA_BACKUP_CODE_USED",
            details={"remaining_codes": len(hashed_codes)},
        )

        return {
            "message": "Acesso recuperado com sucesso",
            "remaining_codes": len(hashed_codes),
            "warning": "Considere gerar novos códigos de backup"
            if len(hashed_codes) < 3
            else None,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na recuperação: {str(e)}",
        )


@router.post("/regenerate-codes")
async def regenerate_backup_codes(
    request: MFARegenerateCodesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate backup codes."""

    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="MFA não está habilitado"
        )

    # Verify MFA code
    if not verify_totp_code(current_user.mfa_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Código MFA inválido"
        )

    try:
        # Generate new backup codes
        backup_codes = generate_backup_codes()
        hashed_codes = hash_backup_codes(backup_codes)

        # Store new codes
        current_user.backup_codes = json.dumps(hashed_codes)
        db.commit()

        # Log security event
        mfa_service = MFAService(db)
        await mfa_service.log_security_event(
            user_id=current_user.id,
            action="MFA_BACKUP_CODES_REGENERATED",
            details={"codes_count": len(backup_codes)},
        )

        return {
            "message": "Códigos de backup regenerados com sucesso",
            "backup_codes": backup_codes,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao regenerar códigos: {str(e)}",
        )


@router.get("/backup-codes/count")
async def get_backup_codes_count(current_user: User = Depends(get_current_user)):
    """Get remaining backup codes count."""

    if not current_user.mfa_enabled or not current_user.backup_codes:
        return {"count": 0}

    try:
        hashed_codes = json.loads(current_user.backup_codes)
        return {"count": len(hashed_codes), "warning": len(hashed_codes) < 3}
    except:
        return {"count": 0}
