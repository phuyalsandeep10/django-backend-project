from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_session

from .config import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
