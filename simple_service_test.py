import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("Testing service initialization...")
    
    try:
        from app.services import init_services, services
        print("Services imported successfully")
        print(f"Before init: {services}")
        
        await init_services()
        print(f"After init: {services}")
        
        # Test database
        if services.db_sessionmaker:
            print("Database sessionmaker is initialized")
            from sqlalchemy import text
            async with services.db_sessionmaker() as session:
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                print(f"Database test successful: {row}")
        
        print("Service test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
