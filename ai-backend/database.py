# database.py
from motor.motor_asyncio import AsyncIOMotorClient
from decouple import config

MONGODB_URL = config("MONGODB_URL")  # Changed from MONGO_URI
DATABASE_NAME = config("DATABASE_NAME", default="twitter_growth_saas")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]  # Use the database name from .env