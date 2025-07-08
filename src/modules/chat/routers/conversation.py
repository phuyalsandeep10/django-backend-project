from fastapi import APIRouter
from fastapi import FastAPI, Request, Header, Depends, Query
import httpx
from src.common.dependencies import get_current_user
from src.modules.chat.models.conversation import Conversation
from src.modules.chat.models.customer import Customer
from src.modules.chat.models.message import Message


router = APIRouter()

@router.get('')
def get_conversations(user=Depends(get_current_user)):
    organizationId = user.attributes.get('organization_id')
    return Conversation.filter(where={
        "organization_id":organizationId
    })


@router.get('{conversation_id}')
def conversation_detail(conversation_id:int,user=Depends(get_current_user)):
    organizationId = user.attributes.get('organization_id')
    record = Conversation.get(conversation_id)

    if not record or record.organization_id != organizationId:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation Not found"
        )
        
    customer = Customer.get(record.customer_id)
    # record = record.dict()
    return {
        "conversation":record,
        "customer":customer
    }


@router.get('{conversation_id}/customer_messages')
def customer_messages(conversation_id:int, limit:int = 20):
    messages = Message.filter(where={
        "conversation_id": conversation_id
    }, limit=limit)
    return {"messages": messages}

@router.get('{conversation_id}/messages')
def user_messages(conversation_id:int, limit:int = 20, user=Depends(get_current_user)):
    messages = Message.filter(where={
        "conversation_id": conversation_id
        
    }, limit=limit)
    return {"messages": messages}


    
    