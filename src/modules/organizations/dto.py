from pydantic import BaseModel, Field

class OrganizationDto(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the organization")
    description: str | None = Field(None, max_length=500, description="Description of the organization")
    # slug: str = Field(..., max_length=255, description="Unique slug for the organization")
    logo: str | None = Field(None, max_length=255, description="Logo URL for the organization")
    website: str | None = Field(None, max_length=255, description="Website URL for the organization")


class OrganizationRoleDto(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the role")
    description: str | None = Field(None, max_length=500, description="Description of the role")
   