import asyncio
from utils.perplexity_client import PerplexityClient

async def test_api():
    client = PerplexityClient()
    result = await client.search('test telecommunications grants')
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(test_api())
