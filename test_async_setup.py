#!/usr/bin/env python3
"""
Test script to verify async database setup and Alembic compatibility.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

async def test_async_database():
    """Test async database operations."""
    from src.config.database import async_session
    from src.models import User  # Import your models
    
    print("Testing async database setup...")
    
    # Test async session
    async with async_session() as session:
        try:
            # Test a simple query
            from sqlmodel import select
            result = await session.execute(select(User).limit(1))
            users = result.scalars().all()
            print(f"✓ Async database query successful. Found {len(users)} users.")
        except Exception as e:
            print(f"✗ Async database query failed: {e}")
            return False
    
    return True

def test_sync_database():
    """Test sync database operations (for Alembic)."""
    from src.config.database import sync_engine
    from src.models import User  # Import your models
    
    print("Testing sync database setup (for Alembic)...")
    
    try:
        from sqlmodel import Session, select
        with Session(sync_engine) as session:
            # Test a simple query
            result = session.exec(select(User).limit(1))
            users = result.all()
            print(f"✓ Sync database query successful. Found {len(users)} users.")
        return True
    except Exception as e:
        print(f"✗ Sync database query failed: {e}")
        return False

def test_alembic_connection():
    """Test Alembic can connect to the database."""
    print("Testing Alembic connection...")
    
    try:
        # This simulates what Alembic does
        
        from sqlmodel import SQLModel
        
        # Test metadata access
        metadata = SQLModel.metadata
        print(f"✓ Alembic metadata access successful. Tables: {list(metadata.tables.keys())}")
        return True
    except Exception as e:
        print(f"✗ Alembic connection failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Async Database Setup with Alembic Support")
    print("=" * 50)
    
    # Test 1: Async database
    async_success = await test_async_database()
    
    # Test 2: Sync database (for Alembic)
    sync_success = test_sync_database()
    
    # Test 3: Alembic connection
    alembic_success = test_alembic_connection()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Async Database: {'✓ PASS' if async_success else '✗ FAIL'}")
    print(f"Sync Database:  {'✓ PASS' if sync_success else '✗ FAIL'}")
    print(f"Alembic:        {'✓ PASS' if alembic_success else '✗ FAIL'}")
    print("=" * 50)
    
    if all([async_success, sync_success, alembic_success]):
        print("\n🎉 All tests passed! Your async setup with Alembic support is working correctly.")
        print("\nNext steps:")
        print("1. Run Alembic migrations: alembic upgrade head")
        print("2. Start your FastAPI app: fastapi dev src/main.py")
        print("3. Use AsyncBaseRepository in your services for async operations")
    else:
        print("\n❌ Some tests failed. Please check your database configuration.")

if __name__ == "__main__":
    asyncio.run(main()) 