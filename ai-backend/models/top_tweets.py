# models/top_tweets.py  🚀 FINAL

from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime


# ---------- helper for clean ObjectId handling ----------
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


# ---------- Top-tweets document ----------
class TopTweetsModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")

    # core tweet metadata
    user: PyObjectId                   # → users._id (owner of the automation)
    keyword: str                       # search term that surfaced the tweet
    conversation_id_str: str           # tweet ID
    text: str                          # full tweet text
    user_id_str: str                   # original poster’s user ID
    username: str                      # original poster’s handle
    time_posted: str                   # Twitter’s created_at string
    created_at: datetime               # when *we* saved the doc

    # NEW: Profile image URL of the original tweet author
    profile_image_url: Optional[str] = None  # Profile picture URL of the tweet author

    # ---------- reply-workflow fields ----------
    draft_reply: Optional[str] = None                 # OpenAI draft reply
    reply_status: str = "PENDING"                     # PENDING | POSTED | CANCELLED
    posted_reply_id: Optional[str] = None             # ID of our reply tweet
    updatedAt: Optional[datetime] = None              # last change (reply or post)

    # ---------- repurpose-workflow (original post) ----------
    draft_post: Optional[str] = None                  # OpenAI rewritten tweet
    post_status: str = "PENDING"                      # PENDING | POSTED | CANCELLED
    posted_post_id: Optional[str] = None              # ID of our posted tweet
    repurposedAt: Optional[datetime] = None           # timestamp of repurpose action

    # ---------- misc flags ----------
    status: str = "NOT DONE"                          # existing flag
    repurposed: str = "NOT DONE"                      # flip to DONE when posted

    class Config:
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True
