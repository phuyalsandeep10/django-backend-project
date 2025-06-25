from fastapi import APIRouter, Depends, HTTPException
from src.common.dependencies import get_current_user,get_bearer_token,update_user_cache
from src.config.database import get_session, Session
from .dto import OrganizationDto, OrganizationRoleDto
from src.common.base_repository import BaseRepository
from .models import Organization, OrganizationMember, OrganizationRole
from src.modules.auth.models import User
from sqlalchemy.orm import selectinload

router = APIRouter()

@router.get("")
def get_organizations(user=Depends(get_current_user),session: Session = Depends(get_session)):
    """
    Get the list of organizations the user belongs to.
    """
    repo = BaseRepository(Organization, session)
    organizations = repo.get_all(
    joins=[OrganizationMember],
    filters=[OrganizationMember.user_id == user.id],
    options=[selectinload(Organization.members)])


    if not organizations:
        raise HTTPException(status_code=404, detail="No organizations found")
    return organizations

@router.post("")
def create_organization(body:OrganizationDto, user=Depends(get_current_user), session:Session = Depends(get_session),token:str=Depends(get_bearer_token)):
    """
    Create a new organization.
    """
    organization_repo = BaseRepository(Organization,session=session)
    print("logged user",user)

    organization = organization_repo.find_one({
        "name": body.name
    })

    if organization:
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    
    organization = organization_repo.create(
        {
            "name": body.name,
            "description": body.description,
            "slug": body.name.lower().replace(" ", "-"),  # Simple slug generation
            "logo": body.logo,
            "website": body.website
        }
    )


    organization_member_repo = BaseRepository(OrganizationMember,session=session)

    organization_member_repo.create({
        "organization_id":organization.id,
        "user_id":user.id,
        "is_owner":True
    })
    if 'organization_id' not in user.attributes:
        user_repo = BaseRepository(User, session=session)
        user = user_repo.update(user.id, {"attributes": {"organization_id": organization.id}})

        update_user_cache(token, user)


    
    return organization


@router.put("/{organization_id}")
def update_organization(organization_id: int, body: OrganizationDto, user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Update an existing organization.
    """
    organization_repo = BaseRepository(Organization, session=session)
    organization = organization_repo.findById(organization_id)
    organization_member_repo = BaseRepository(OrganizationMember, session=session)
    organization_member = organization_member_repo.find_one({
        "organization_id": organization_id,
        "user_id": user.id
    })

    if not organization_member:
        raise HTTPException(status_code=403, detail="You do not have permission to update this organization")

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    if organization.name != body.name:
        existing_org = organization_repo.find_one({"name": body.name})
        if existing_org:
            raise HTTPException(status_code=400, detail="Organization with this name already exists")

    record = organization_repo.update(organization_id, {
        "name": body.name,
        "description": body.description,
        "slug": body.name.lower().replace(" ", "-"),  # Simple slug generation
        "logo": body.logo,
        "website": body.website
    })

    return record


@router.put("/{organization_id}/set")
def set_organization(organization_id: int, user=Depends(get_current_user),token:str=Depends(get_bearer_token), session: Session = Depends(get_session)):
    """
    Set an existing organization.
    """
    organization_repo = BaseRepository(Organization, session=session)
    organization = organization_repo.findById(organization_id)

    user = BaseRepository(User, session=session).update(user.id,{"attributes":{"organization_id":organization_id}})

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    update_user_cache(token, user)

    return {"message": "Organization set successfully"}
    




@router.post('/roles')
def create_role(body: OrganizationRoleDto, user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Create a new role for an organization.
    """

    organization_id = user.attributes.get("organization_id")

  
    # Create the role (assuming you have a Role model and repository)
    role_repo = BaseRepository(OrganizationRole, session=session)
    role = role_repo.find_one({
        "name": body.name,
        "organization_id": organization_id
    })

    if role:
        raise HTTPException(status_code=400, detail="Role with this name already exists in your organization")

    role = role_repo.create({
        "name": body.name,
        "description": body.description,
        "organization_id": organization_id,
        "identifier": body.name.lower().replace(" ", "-")  # Simple identifier generation
    })

    return role

@router.put('/roles/{role_id}')
def update_role(role_id:int,body:OrganizationRoleDto,user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Update an existing role for an organization.
    """
    organization_id = user.attributes.get("organization_id")
    role_repo = BaseRepository(OrganizationRole, session=session)

    role = role_repo.findById(role_id)

    if not role or role.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Role not found in your organization")

    role = role_repo.update(role.id,{
        "name": body.name,
        "description": body.description,
    })

    

    return role

@router.get('/roles')
def get_roles(user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Get all roles for the user's organization.
    """
    organization_id = user.attributes.get("organization_id")
    role_repo = BaseRepository(OrganizationRole, session=session)
    
    roles = role_repo.get_all([
        OrganizationRole.organization_id == organization_id
    ])

    return roles

@router.delete('/{role_id}/roles')
def delete_role(role_id: int, user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Delete a role from the organization.
    """
    organization_id = user.attributes.get("organization_id")
    print("organization_id",organization_id)
    role_repo = BaseRepository(OrganizationRole, session=session)
    
    role = role_repo.findById(role_id)

    if not role or role.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Role not found in your organization")

    role_repo.delete(role_id)
    
    return {"message": "Role deleted successfully"}






    
    
