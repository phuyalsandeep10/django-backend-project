from typing import TypeVar, Generic, Type, List, Optional, Any, Callable
from sqlmodel import SQLModel, Session, select
from fastapi import HTTPException
from sqlalchemy.sql import Select

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

    def get_all(
        self,
        filters: Optional[List[Any]] = None,
        joins: Optional[List[Any]] = None,
        options: Optional[List[Any]] = None,
        custom_query_builder: Optional[Callable[[Select], Select]] = None,
    ) -> List[T]:
        statement = select(self.model)

        if joins:
            for join_model in joins:
                statement = statement.join(join_model)

        if filters:
            for f in filters:
                statement = statement.where(f)

        if options:
            for opt in options:
                statement = statement.options(opt)

        if custom_query_builder:
            statement = custom_query_builder(statement)

        return self.session.exec(statement).all()
    
    

    def find(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[List[Any]] = None,
        joins: Optional[List[Any]] = None,
        options: Optional[List[Any]] = None,
        custom_query_builder: Optional[Callable[[Select], Select]] = None,
    ) -> List[T]:
        statement = select(self.model)

        if joins:
            for join_model in joins:
                statement = statement.join(join_model)

        if filters:
            for f in filters:
                statement = statement.where(f)

        if options:
            for opt in options:
                statement = statement.options(opt)

        if custom_query_builder:
            statement = custom_query_builder(statement)

        statement = statement.offset(skip).limit(limit)

        return self.session.exec(statement).all()
    

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
    
    


