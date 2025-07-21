from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime

class PostedTweetTracker(BaseModel):
    user: ObjectId                    # Reference to the user who posted
    tweet_id: str                     # The actual Twitter tweet ID
    tweet_type: str                   # "reply" | "repurpose"
    source_type: str                  # "top_tweet" | "user_tweet"
    posted_at: datetime               # When the tweet was posted
    original_text: str                # The actual tweet content for mem0 context
    source_context: str               # Keyword (for top tweets) or @username (for user tweets)
    
    # Optional fields for additional context
    engagement_context: Optional[str] = None    # For future use in analytics
    created_at: datetime = Field(default_factory=datetime.utcnow)  # When record was created

    class Config:
        arbitrary_types_allowed = True 