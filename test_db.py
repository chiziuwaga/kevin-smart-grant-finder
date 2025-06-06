import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config.settings import get_settings

async def test_db():
    try:
        print("Testing database connection...")
        settings = get_settings()
        
        print(f"Database URL: {settings.db_url[:50]}...")
        
        engine = create_async_engine(settings.db_url, echo=False)
        
        async with engine.connect() as conn:
            result = await conn.execute(text('SELECT 1 as test'))
            row = result.fetchone()
            print(f"Database test successful: {row}")
        
        await engine.dispose()
        print("Database connection test passed!")
        return True
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_db())
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
