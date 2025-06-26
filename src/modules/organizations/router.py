from fastapi import APIRouter, Depends, HTTPException
from src.common.dependencies import get_current_user,get_bearer_token,update_user_cache
from src.config.database import get_session, Session
from .dto import OrganizationDto, OrganizationRoleDto, OrganizationInviteDto, OrganizationInvitationApproveDto
from src.common.base_repository import BaseRepository
from .models import Organization, OrganizationMember, OrganizationRole, OrganizationInvitation
from src.modules.auth.models import User

router = APIRouter()

@router.get("")
async def get_organizations(user=Depends(get_current_user),session: Session = Depends(get_session)):
    """
    Get the list of organizations the user belongs to.
    """
    return Organization.get_orgs_by_user_id(user_id=user.id)

@router.post("")
def create_organization(body:OrganizationDto, user=Depends(get_current_user), session:Session = Depends(get_session),token:str=Depends(get_bearer_token)):
    """
    Create a new organization.
    """
    record = Organization.find_one(where={
        "name": {
            "mode":"insensitive",
            "value": body.name
        },
    
    })



    if record:
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    

    organization = Organization.create(
        name=body.name,
        description=body.description,
        slug=body.name.lower().replace(" ", "-"),  # Simple slug generation
        logo=body.logo,
        website=body.website
    )

    OrganizationMember.create(organization_id=organization.id,user_id=user.id,is_owner=True)


    if user.attributes and  'organization_id' not in user.attributes:
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
    record = OrganizationRole.find_one(
        where={
            "name":{
                "mode":"insensitive",
                "value":body.name
            },
            "organization_id":organization_id
        }

    )

    if record:
        raise HTTPException(400,"Duplicate record")
    
    return OrganizationRole.create(
        name=body.name,
        organization_id=organization_id,
        identifier=body.name.lower().replace(' ','-'),
        description=body.description
        )

@router.put('/roles/{role_id}')
def update_role(role_id:int,body:OrganizationRoleDto,user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Update an existing role for an organization.
    """

    organizationRole = OrganizationRole.get(role_id)
    organization_id = user.attributes.get("organization_id")

    if not organizationRole or organizationRole.organization_id != organization_id:
        raise HTTPException(status_code=404,detail="Not found")
    
    record = OrganizationRole.find_one(where={
        "name":{
            "value":body.name,
            "mode":"insensitive"
        }
    })

    if record and record.id != organizationRole.id:
        raise HTTPException(status_code=400,detail="Bad request")
    


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

    return OrganizationRole.filter(where={
        "organization_id":organization_id
    })


@router.delete('/{role_id}/roles')
def delete_role(role_id: int, user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Delete a role from the organization.
    """
    organization_id = user.attributes.get("organization_id")

    role_repo = BaseRepository(OrganizationRole, session=session)
    
    role = role_repo.findById(role_id)

    if not role or role.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Role not found in your organization")

    role_repo.delete(role_id)
    
    return {"message": "Role deleted successfully"}




@router.post('/invitation')
def invite_user(body:OrganizationInviteDto, user=Depends(get_current_user)):
    record = OrganizationInvitation.find_one(where={
        "email":body.email,
        "status":"pending"
    })
    organization_id = user.attributes.get('organization_id')

    if record:
        raise HTTPException(400,"Already invitation exist")
    
    if user.email ==body.email:
        raise HTTPException(403,f"you can't invite your self.")

    
    record = OrganizationInvitation.create(email=body.email,invited_by_id=user.id,status='pending',organization_id=organization_id, role_ids=body.role_ids)

    return record

@router.get('/invitation')
def get_invitations(user=Depends(get_current_user)):
    organization_id = user.attributes.get('organization_id')
    if not organization_id:
        raise HTTPException(403,'Not organization setup')
    
    return OrganizationInvitation.filter(where={
        "organization_id":organization_id
    })




@router.post('/invitation/{invitation_id}/reject')
def reject_invitation(invitation_id:int,user=Depends(get_current_user)):
    invitation = OrganizationInvitation.get(invitation_id)
    
    if not invitation:
        raise HTTPException(404,"Not found")
    
    return OrganizationInvitation.update(invitation.id,status='rejected')
    
@router.post('/invitation/{invitation_id}/accept')
def accept_invitation(invitation_id:int,user=Depends(get_current_user),session=Depends(get_session)):

    invitation = OrganizationInvitation.get(invitation_id)

    if user.email !=invitation.email:
        raise HTTPException(403,"Don't have authorization")


    
    if not invitation:
        raise HTTPException(404,"Not found")
    
    OrganizationInvitation.update(invitation.id,status='accepted')

    BaseRepository(User,session=session)

    for role_id in invitation.role_ids:
        OrganizationMember.create(role_id=role_id,user_id=user.id,organization_id=invitation.organization_id)
    
    return {"message":"Successfully approved"}
