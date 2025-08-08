from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from sqlmodel import text

from src.common.dependencies import (
    get_bearer_token,
    get_current_user,
    update_user_cache,
)
from src.common.models import Permission
from src.enums import InvitationStatus
from src.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationMemberRole,
    OrganizationRole,
    User,
)

from src.db.config import async_session
from sqlmodel import select
from src.tasks import send_invitation_email
from src.common.utils import random_unique_key
from src.utils.response import CustomResponse as cr
from src.modules.staff_managemet.models import RolePermission
from src.modules.staff_managemet.models import Permissions

from .schema import (
    OrganizationSchema,
    OrganizationInviteSchema,
    AssignRoleSchema,
    CreateRoleOutSchema,
    UpdateRoleInfoSchema,
    CreateRoleSchema,
)

router = APIRouter()


@router.get("")
async def get_organizations(user=Depends(get_current_user)):
    """
    Get the list of organizations the user belongs to.
    """
    records = await Organization.get_orgs_by_user_id(user_id=user.id)
    data = [item.to_json() for item in records]
    return cr.success(data=data)


@router.post("")
async def create_organization(
    body: OrganizationSchema,
    user=Depends(get_current_user),
    token: str = Depends(get_bearer_token),
):
    """
    Create a new organization.
    """
    record = await Organization.find_one(
        where={
            "name": {"mode": "insensitive", "value": body.name},
        }
    )

    if record:
        raise HTTPException(
            status_code=400, detail="Organization with this name already exists"
        )
    slug = body.name.lower().replace(" ", "-")
    organization = await Organization.create(
        name=body.name,
        description=body.description,
        slug=slug,
        logo=body.logo,
        domain=body.domain,
        purpose=body.purpose,
        identifier=f"{slug}-{random_unique_key()}",
        owner_id=user.id,
    )

    await OrganizationMember.create(
        organization_id=organization.id, user_id=user.id, is_owner=True
    )
    user_attributes = user.attributes

    if not user_attributes:
        user_attributes = {}

    if "organization_id" not in user_attributes:

        user = await User.update(
            user.id, attributes={"organization_id": organization.id}
        )

        if not user:
            raise HTTPException(404, "Not found User")

        update_user_cache(token, user)

    return cr.success(data=organization.to_json())


@router.get("/{organization_id}/members")
async def get_members(user=Depends(get_current_user)):
    organization_id = user.attributes.get("organization_id")
    members = await OrganizationMember.filter(
        {
            "organization_id": organization_id,
        }
    )

    # For each member, fetch their roles
    result = []
    for member in members:
        # Get all member_role entries for this member
        member_roles = await OrganizationMemberRole.filter({"member_id": member.id})
        # Get role names
        roles = []
        for mr in member_roles:
            role = await OrganizationRole.get(mr.role_id)
            if role:
                roles.append({"id": role.id, "name": role.name})
        # Add roles to member dict
        member_dict = member.dict() if hasattr(member, "dict") else dict(member)
        member_dict["roles"] = roles
        result.append(member_dict)
    return cr.success(data=result)


@router.put("/{organization_id}")
async def update_organization(
    organization_id: int, body: OrganizationSchema, user=Depends(get_current_user)
):
    """
    Update an existing organization.
    """
    organization = await Organization.get(organization_id)

    organization_member = await OrganizationMember.find_one(
        {"organization_id": organization_id, "user_id": user.id}
    )

    if not organization_member:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this organization",
        )

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    if organization.name != body.name:
        existing_org = await Organization.find_one(
            {"name": {"value": body.name, "mode": "insensitive"}}
        )
        if existing_org:
            raise HTTPException(
                status_code=400, detail="Organization with this name already exists"
            )

    record = await Organization.update(
        organization_id,
        name=body.name,
        description=body.description,
        logo=body.logo,
        domain=body.domain,
    )

    return cr.success(data=record)


@router.put("/{organization_id}/set")
async def set_organization(
    organization_id: int,
    user=Depends(get_current_user),
    token: str = Depends(get_bearer_token),
):
    """
    Set an existing organization.
    """

    organization = await Organization.get(organization_id)

    user = await User.update(user.id, attributes={"organization_id": organization_id})

    if not user:
        raise HTTPException(404, "Not found User")

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    update_user_cache(token, user)

    return cr.success(data={"message": "Organization set successfully"})


# create Role
@router.post("/roles")
async def create_role(body: CreateRoleSchema, user=Depends(get_current_user)):
    """
    Create a New Role for an organization.
    """

    existing_role = await OrganizationRole.find_one(
        where={"name": {"mode": "insensitive", "value": body.name}}
    )

    if existing_role:
        raise HTTPException(status_code=400, detail="Role name already exists")

    role = await OrganizationRole.create(
        **body.model_dump(exclude={"permissions", "updated_at", "created_at"}),
        identifier=body.name.lower().replace(" ", "-"),
    )
    print("Role Created:", role)
    for perm in body.permissions:
        await RolePermission.create(
            role_id=role.id,
            **perm.model_dump(),
        )

    org = await Organization.find_one(where={"id": role.organization_id})

    return cr.success(data=org.to_json(CreateRoleOutSchema))


# UPadate role
@router.put("/roles/{role_id}")
async def update_role(
    role_id: int, body: UpdateRoleInfoSchema, user=Depends(get_current_user)
):
    """
    Update an existing role within the current tenant's organization.
    """
    role = await OrganizationRole.find_one(where={"id": role_id})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    existing = await OrganizationRole.find_one(
        where={"name": {"value": body.name, "mode": "insensitive"}}
    )
    if existing and existing.id != role.id:
        raise HTTPException(status_code=400, detail="Role name already exists")

    await OrganizationRole.update(
        role_id,
        **body.model_dump(exclude={"permissions"}),
        identifier=body.name.lower().replace(" ", "-"),
    )

    # Update permissions
    for perm in body.permissions:
        await RolePermission.update(
            where={"role_id": role.id, "permission_id": perm.permission_id},
            values={
                "is_changeable": perm.is_changeable,
                "is_deletable": perm.is_deletable,
                "is_viewable": perm.is_viewable,
            },
        )

    updated_role = await OrganizationRole.find_one(where={"id": role_id})

    return cr.success(data=updated_role.to_json(CreateRoleOutSchema))


# # Get All Roles
# @router.get("/roles")
# async def get_roles(user=Depends(get_current_user)):
#     """
#     Retrieve all the roles for the organization
#     """
#     roles = await OrganizationRole.filter()

#     results = []
#     for role in roles:
#         org = await Organization.get(role.organization_id)
#         role_data = {
#             "role_id": role.id,
#             "role_name": role.name,
#             "description": role.description,
#             "org_name": org.name,
#             "created_at": role.created_at.isoformat(),
#         }
#         results.append(CreateRoleOutSchema(**role_data))

#     return cr.success(data=[r.model_dump() for r in results])


@router.get("/roles")
async def get_roles(user=Depends(get_current_user)):
    roles = await OrganizationRole.filter()

    async with async_session() as session:
        query = text(
            """
            SELECT r.id AS role_id, COUNT(*) AS total_members
            FROM org_member_roles omr
            JOIN org_members m ON omr.member_id = m.id
            JOIN org_roles r ON omr.role_id = r.id
            GROUP BY r.id
        """
        )
        counts_result = await session.execute(query)
        counts_map = {row.role_id: row.total_members for row in counts_result}

    results = []
    for role in roles:
        org = await Organization.get(role.organization_id)
        role_data = {
            "role_id": role.id,
            "role_name": role.name,
            "description": role.description,
            "org_name": org.name,
            "created_at": role.created_at.isoformat(),
            "no_of_agents": counts_map.get(role.id, 0),
            "permission_summary": [],
        }
        results.append(CreateRoleOutSchema(**role_data))

    return cr.success(data=[r.model_dump() for r in results])


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, user=Depends(get_current_user)):
    """
    Soft delete a role from the organization (tenant-aware).
    """
    await OrganizationRole.soft_delete(where={"id": role_id})

    return cr.success(data={"message": "Role deletion successful"})


@router.post("/invitation")
async def invite_user(body: OrganizationInviteSchema, user=Depends(get_current_user)):
    record = await OrganizationInvitation.find_one(
        where={"email": body.email, "status": "pending"}
    )

    organization_id = user.attributes.get("organization_id")

    if record:
        raise HTTPException(400, "Already invitation exist")

    if user.email == body.email:
        raise HTTPException(403, "You can't invite yourself.")

    expires_at = datetime.utcnow() + timedelta(days=7)

    record = await OrganizationInvitation.create(
        email=body.email,
        invited_by_id=user.id,
        status="pending",
        organization_id=organization_id,
        role_ids=body.role_ids,
        token="",
        expires_at=expires_at,
    )

    send_invitation_email.delay(email=body.email)

    return cr.success(
        data=record.model_dump(
            exclude={"expires_at", "activity_at", "created_at", "updated_at"}
        )
    )


@router.get("/invitation")
async def get_invitations(user=Depends(get_current_user)):
    invitations = await OrganizationInvitation.filter()

    excluded_fields = {"expires_at", "activity_at", "created_at", "updated_at"}
    return cr.success(
        data=[inv.model_dump(exclude=excluded_fields) for inv in invitations]
    )


@router.post("/invitation/{invitation_id}/reject")
async def reject_invitation(invitation_id: int, user=Depends(get_current_user)):
    invitation = await OrganizationInvitation.get(invitation_id)

    if not invitation:
        raise HTTPException(404, "Not found")

    record = await OrganizationInvitation.update(
        invitation.id, status=InvitationStatus.REJECTED
    )
    return cr.success(data=record)


@router.post("/invitation/{invitation_id}/accept")
async def accept_invitation(invitation_id: int, user=Depends(get_current_user)):

    invitation = await OrganizationInvitation.get(invitation_id)
    if not invitation:
        raise HTTPException(404, "Not Found")

    if user.email != invitation.email:
        raise HTTPException(403, "Don't have authorization")

    if not invitation:
        raise HTTPException(404, "Not found")

    await OrganizationInvitation.update(invitation.id, status=InvitationStatus.ACCEPTED)

    member = await OrganizationMember.find_one(
        {"organization_id": invitation.organization_id, "user_id": user.id}
    )

    if not member:
        member = await OrganizationMember.create(
            organization_id=invitation.organization_id, user_id=user.id
        )

    for role_id in invitation.role_ids:
        await OrganizationMemberRole.create(role_id=role_id, member_id=member.id)

    return cr.success(data={"message": "Successfully approved"})


@router.post("/roles-assign")
async def assign_role(body: AssignRoleSchema, user=Depends(get_current_user)):

    organization_id = user.attributes.get("organization_id")
    member = await OrganizationMember.find_one(
        where={"organization_id": organization_id, "user_id": body.user_id}
    )

    if not member:
        raise HTTPException(400, "Organization Member not found")

    member_role = await OrganizationMemberRole.find_one(
        where={"member_id": member.id, "role_id": body.role_id}
    )

    if not member_role:
        await OrganizationMemberRole.create(role_id=body.role_id, member_id=member.id)

    return cr.success(data={"message": "Successfully assign"})


@router.post("/remove-assign-role")
async def remove_assign_role(body: AssignRoleSchema, user=Depends(get_current_user)):
    organization_id = user.attributes.get("organization_id")

    member = await OrganizationMember.find_one(
        where={"organization_id": organization_id, "user_id": body.user_id}
    )

    if not member:
        raise HTTPException(400, "Organization Member not found")

    member_role = await OrganizationMemberRole.find_one(
        {"member_id": member.id, "role_id": body.role_id}
    )

    if not member_role:
        raise HTTPException(400, "Role not found")

    await OrganizationMemberRole.soft_delete(member_role.id)
    return cr.success(data={"message": "Successfully remove role"})


@router.get("/permissions")
async def get_permissions(user=Depends(get_current_user)):
    permissions = await Permission.filter()
    return cr.success(data=permissions)
