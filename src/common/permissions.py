
from src.modules.auth.models import User
from fastapi import Depends, HTTPException, status

from src.common.dependencies import get_current_user, get_session
from src.common.base_repository import BaseRepository
from src.modules.organizations.models import OrganizationMember
from sqlalchemy.orm import Session

def is_organization_owner(
    organization_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    member_repo = BaseRepository(OrganizationMember, session=session)
    member = member_repo.find_one({
        "organization_id": organization_id,
        "user_id": user.id,
        "is_owner": True
    })
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this organization."
        )
    return True