from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime

class TrackedUserTweetsModel(BaseModel):
    user: ObjectId                # Ref to the main User
    username: str                 # Tracked account's handle
    tweet_id: str                 # Twitter conversation ID
    text: str                     # Original tweet text
    created_at: str               # Original tweet timestamp from Twitter API

    # New fields for reply workflow
    draft_reply: Optional[str] = None    # The AI-drafted reply text
    reply_status: str = "PENDING"        # PENDING, POSTED, CANCELLED
    posted_reply_id: Optional[str] = None  # Twitter ID of the reply, if posted
    
    # NEW: Profile image URL of the tracked user
    profile_image_url: Optional[str] = None  # Profile picture URL of the tracked user

    createdAt: datetime = Field(default_factory=datetime.utcnow)  # When stored in DB

    class Config:
        arbitrary_types_allowed = True
