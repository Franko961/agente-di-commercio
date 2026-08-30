import os

from pymongo import AsyncMongoClient

mongo_url = os.environ["MONGO_URL"]
client: AsyncMongoClient = AsyncMongoClient(mongo_url)
db = client[os.environ["DB_NAME"]]


async def close_db() -> None:
    await client.close()
