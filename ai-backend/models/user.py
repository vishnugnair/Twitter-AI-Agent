# models/user.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from bson import ObjectId

# ----------  helper for ObjectId ----------
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


# ----------  primary user model ----------
class UserModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: Optional[PyObjectId] = Field(alias="_id", default=None)

    # core profile fields
    name: Optional[str] = None
    email: str
    password: str

    # essential fields
    target_accounts: Optional[List[str]] = []
    search_keywords: Optional[List[str]] = []

    # TWITTER CREDENTIALS
    twitter_username: Optional[str] = None
    twitter_client_id: Optional[str] = None
    twitter_client_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    
    # AI PERSONA (generated from user's own tweets)
    user_persona: Optional[str] = None
    
    # USER'S OWN PROFILE IMAGE (NEW)
    profile_image_url: Optional[str] = None