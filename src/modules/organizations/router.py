from fastapi import APIRouter, Depends, HTTPException
from src.common.dependencies import get_current_user,get_bearer_token,update_user_cache
from src.config.database import get_session, Session
from .dto import OrganizationDto, OrganizationRoleDto, OrganizationInviteDto , PermissionDto, AssignPermissionDto

from src.models import Organization, OrganizationMember, OrganizationRole, OrganizationInvitation, OrganizationMemberRole, User
from src.modules.organizations.dto import AssignRoleDto
from src.common.models import Permission
from src.tasks import send_invitation_email
from src.enums import InvitationStatus


router = APIRouter()

@router.get("")
async def get_organizations(user=Depends(get_current_user),session: Session = Depends(get_session)):
    """
    Get the list of organizations the user belongs to.
    """
    return Organization.get_orgs_by_user_id(user_id=user.id)

@router.post("")
def create_organization(body:OrganizationDto, user=Depends(get_current_user),token:str=Depends(get_bearer_token)):
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
    user_attributes = user.attributes

    if not user_attributes:
        user_attributes = {}

    if 'organization_id' not in user_attributes:
       

        user = User.update(user.id,
                       attributes={
                           "organization_id":organization.id
                       })


        update_user_cache(token, user)
        


    
    return organization


@router.get('/{organization_id}/members')
def get_members(user=Depends(get_current_user)):
    organization_id = user.attributes.get('organization_id')
    members = OrganizationMember.filter({
        "organization_id": organization_id,
    })

    # For each member, fetch their roles
    result = []
    for member in members:
        # Get all member_role entries for this member
        member_roles = OrganizationMemberRole.filter({
            "member_id": member.id
        })
        # Get role names
        roles = []
        for mr in member_roles:
            role = OrganizationRole.get(mr.role_id)
            if role:
                roles.append({"id": role.id, "name": role.name})
        # Add roles to member dict
        member_dict = member.dict() if hasattr(member, "dict") else dict(member)
        member_dict["roles"] = roles
        result.append(member_dict)
    return result

@router.put("/{organization_id}")
def update_organization(organization_id: int, body: OrganizationDto, user=Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Update an existing organization.
    """
    organization = Organization.get(organization_id)

    organization_member = OrganizationMember.find_one({
        "organization_id": organization_id,
        "user_id": user.id
    })

    if not organization_member:
        raise HTTPException(status_code=403, detail="You do not have permission to update this organization")

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    if organization.name != body.name:
        existing_org = Organization.find_one({"name": {
            "value":body.name,
            "mode":"insensitive"
        }})
        if existing_org:
            raise HTTPException(status_code=400, detail="Organization with this name already exists")

    record = Organization.update(
        organization_id, 
        name= body.name,
        description= body.description,
        slug=body.name.lower().replace(" ", "-"),  # Simple slug generation
        logo= body.logo,
        website= body.website
    )

    return record


    




@router.put("/{organization_id}/set")
def set_organization(organization_id: int, user=Depends(get_current_user),token:str=Depends(get_bearer_token)):
    """
    Set an existing organization.
    """

    organization = Organization.get(organization_id)

    user = User.update(user.id,
                       attributes={
                           "organization_id":organization_id
                       })

 

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    update_user_cache(token, user)

    return {"message": "Organization set successfully"}
    


@router.post('/roles')
def create_role(body: OrganizationRoleDto, user=Depends(get_current_user)):
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
    
    permissions = []
    if body.permissions:
        permissions = list(set(body.permissions))

        

    
    return OrganizationRole.create(
        name=body.name,
        organization_id=organization_id,
        identifier=body.name.lower().replace(' ','-'),
        description=body.description,
        permissions=permissions
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
    

    role = OrganizationRole.get(role_id)

    if not role or role.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Role not found in your organization")
    

    permissions = []
    if body.permissions:
        permissions = list(set(body.permissions))


    role = OrganizationRole.update(role.id,name=body.name,permissions=permissions, description=body.description)

    return role

@router.get('/roles')
def get_roles(user=Depends(get_current_user)):
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


    role = OrganizationRole.get(role_id)

    if not role or role.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Role not found in your organization")

    OrganizationRole.delete(role_id)
    
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

    send_invitation_email.delay(email=body.email)
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
    
    return OrganizationInvitation.update(invitation.id,status=InvitationStatus.REJECTED) 


@router.post('/invitation/{invitation_id}/accept')
def accept_invitation(invitation_id:int,user=Depends(get_current_user),session=Depends(get_session)):

    invitation = OrganizationInvitation.get(invitation_id)

    if user.email !=invitation.email:
        raise HTTPException(403,"Don't have authorization")
    
    if not invitation:
        raise HTTPException(404,"Not found")
    
    OrganizationInvitation.update(invitation.id,status=InvitationStatus.ACCEPTED)


    member = OrganizationMember.find_one({
        "organization_id":invitation.organization_id,
        "user_id":user.id
    })

    if not member:
        member = OrganizationMember.create(organization_id=invitation.organization_id,user_id=user.id)



    for role_id in invitation.role_ids:
        OrganizationMemberRole.create(role_id=role_id,member_id=member.id)
    
    return {"message":"Successfully approved"}

@router.post('/roles-assign')
def assign_role(body:AssignRoleDto, user=Depends(get_current_user)):

    organization_id = user.attributes.get('organization_id')
    member = OrganizationMember.find_one(where={
        "organization_id":organization_id,
        "user_id":body.user_id
    })

    if not member:
        raise HTTPException(400,"Organization Member not found")

    member_role = OrganizationMemberRole.find_one(where={
        "member_id":member.id,
        "role_id":body.role_id
    })

    if not member_role:
        OrganizationMemberRole.create(role_id=body.role_id,member_id=member.id)

    return {"message":"Successfully assign"}




@router.post('/remove-assign-role')
def remove_assign_role(body:AssignRoleDto,user=Depends(get_current_user)):
    organization_id = user.attributes.get('organization_id')

    member = OrganizationMember.find_one(where={
        "organization_id":organization_id,
        "user_id":body.user_id
    })

    if not member:
        raise HTTPException(400,"Organization Member not found")
    
    member_role = OrganizationMemberRole.find_one({
        "member_id":member.id,
        "role_id":body.role_id
    })

    if not member_role:
        raise HTTPException(400,'Role not found') 
    
    OrganizationMemberRole.delete(member_role.id)
    return {"message":"Successfully remove role"}


@router.get('/permissions')
def get_permissions(user=Depends(get_current_user)):
    return Permission.filter()



