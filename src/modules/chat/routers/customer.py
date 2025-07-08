from fastapi import APIRouter
from fastapi import FastAPI, Request, Header, Depends
import httpx
from src.common.dependencies import get_current_user
from src.modules.chat.models.conversation import Conversation
from src.modules.chat.models.customer import Customer



router = APIRouter()

@router.post("/{organizationId}")
def create_customer(organizationId:int,request:Request):
    header = request.headers.get("X-Forwarded-For")
    ip = header.split(",")[0].strip() if header else request.client.host


    customer = Customer.create(
        name=f"{ip}-customer",
        ip_address=ip,
        organization_id=organizationId
    )

    conversation = Conversation.create(
        name=f"{ip}-Conversation",
        customer_id=customer.id,
        ip_address = ip,
        organization_id=organizationId
    )

    return {
        "customer":customer,
        "conversation":conversation
    }





@router.get("")
def get_customers(organizationId:int,user = Depends(get_current_user)):

    customers = Customer.filter(where={
        "organization_id": organizationId
    })

    return customers


    
