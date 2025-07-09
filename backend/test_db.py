import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_mongodb():
    try:
        client = AsyncIOMotorClient('mongodb://localhost:27017/pcap_reporter')
        db = client.pcap_reporter
        result = await db.command('ping')
        print('MongoDB connection successful:', result)
        await client.close()
        return True
    except Exception as e:
        print(f'MongoDB connection failed: {e}')
        return False

if __name__ == "__main__":
    asyncio.run(test_mongodb()) 