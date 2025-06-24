from typing import TypeVar, Generic, Type, List, Optional, Any
from sqlmodel import SQLModel, Session, select
from fastapi import HTTPException


T = TypeVar("T", bound=SQLModel)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def create(self, data: T) -> T:
        instance = self.model(**data)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def findById(self, id: int) -> Optional[T]:
        obj = self.session.get(self.model, id)
        return obj

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        statement = select(self.model).offset(skip).limit(limit)
        results = self.session.exec(statement).all()
        return results
    

    def update(self, id: int, data: dict) -> T:

        obj = self.findById(id)
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, id: int) -> None:

        obj = self.findById(id)
        self.session.delete(obj)
        self.session.commit()

    
    

    
    def find(self, **filters: dict) -> List[T]:
        """
        Type-safe find method filtering by model attributes.
        Filters must correspond to valid model fields.
        """
        statement = select(self.model)
        for attr, value in filters.items():
            if not hasattr(self.model, attr):
                raise HTTPException(status_code=400, detail=f"Invalid filter field: {attr}")
            # Use the model's attribute (which is type annotated) to build the where clause
            statement = statement.where(getattr(self.model, attr) == value)
        results = self.session.exec(statement).all()
        return results
    

    
    # Add a method to find a single record based on filters
    def find_one(self, filters: dict):  # <-- add filters parameter
        query = self.session.query(self.model)
        for key, value in filters.items():
            query = query.filter(getattr(self.model, key) == value)
        return query.first()
    
    


