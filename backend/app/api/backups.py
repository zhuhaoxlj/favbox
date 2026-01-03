"""
Backup API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.backup_service import BackupService
from app.schemas.backup import (
    CreateBackupRequest,
    BookmarkBackupResponse,
    RestoreBackupRequest,
)
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.post(
    "", response_model=BookmarkBackupResponse, status_code=status.HTTP_201_CREATED
)
async def create_backup(
    request: CreateBackupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建书签备份快照

    保存当前所有书签的状态，用于AI处理前的备份
    """
    try:
        backup = await BackupService.create_backup(
            db=db,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
        )
        return backup
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}",
        )


@router.get("", response_model=list[BookmarkBackupResponse])
async def list_backups(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的所有备份列表
    """
    backups = await BackupService.get_user_backups(
        db=db, user_id=current_user.id, limit=limit
    )
    return backups


@router.get("/{backup_id}", response_model=BookmarkBackupResponse)
async def get_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取特定备份的详细信息
    """
    backup = await BackupService.get_backup(
        db=db, backup_id=backup_id, user_id=current_user.id
    )

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found"
        )

    return backup


@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除备份
    """
    deleted = await BackupService.delete_backup(
        db=db, backup_id=backup_id, user_id=current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found"
        )

    return None


@router.post("/restore", status_code=status.HTTP_200_OK)
async def restore_backup(
    request: RestoreBackupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    从备份还原书签

    - merge_mode=false: 完全覆盖现有书签
    - merge_mode=true: 合并模式，保留现有书签
    """
    try:
        result = await BackupService.restore_backup(
            db=db,
            backup_id=request.backup_id,
            user_id=current_user.id,
            merge_mode=request.merge_mode,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}",
        )
