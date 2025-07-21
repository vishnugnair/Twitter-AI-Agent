# models/tracked_user.py

from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime

# Helper to parse ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


# ✅ MongoDB TrackedUser schema
class TrackedUserModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    username: str
    user_id: str  # Twitter's internal user ID
    about_them: Optional[str]
    followers: Optional[int]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Reference to the registered user who owns this tracked user
    registered_user_id: PyObjectId

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# ✅ Input model if needed (optional, can use same model)
class TrackedUserCreateModel(BaseModel):
    username: str
    user_id: str
    about_them: Optional[str]
    followers: Optional[int]
