# app.py
from __future__ import annotations

import os
import asyncio
import hashlib
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response, status, Cookie, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import httpx
import uvicorn
from decouple import config
from typing import List, Optional
from urllib.parse import urlencode 
import json
from datetime import timedelta

from database import db
from models.user import UserModel
from models.posted_tweet_tracker import PostedTweetTracker

# -----------------------------------------------------------
# FastAPI initialisation (moved after lifespan definition)
# -----------------------------------------------------------
# FastAPI app will be initialized after lifespan definition

# -----------------------------------------------------------
# Environment variables and API keys
# -----------------------------------------------------------
try:
    RAPIDAPI_KEY = config("RAPIDAPI_KEY")          # twitter-aio RapidAPI key
    GEMINI_API_KEY = config("GEMINI_API_KEY")      # Gemini API key
    PINECONE_API_KEY = config("PINECONE_API_KEY")  # Pinecone API key
    PINECONE_INDEX_NAME = config("PINECONE_INDEX_NAME")  # Pinecone index name
    NEO4J_URI = config("NEO4J_URI")                # Neo4j database URI
    NEO4J_USERNAME = config("NEO4J_USERNAME")      # Neo4j username
    NEO4J_PASSWORD = config("NEO4J_PASSWORD")      # Neo4j password
except Exception as e:
    print(f"[ERROR] Missing environment variables: {e}")
    print("[INFO] Make sure you have RAPIDAPI_KEY, GEMINI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in your .env file")
    RAPIDAPI_KEY = None
    GEMINI_API_KEY = None
    PINECONE_API_KEY = None
    PINECONE_INDEX_NAME = None 
    NEO4J_URI = None
    NEO4J_USERNAME = None
    NEO4J_PASSWORD = None

# Redis Configuration
try:
    REDIS_HOST = config("REDIS_HOST")
    REDIS_PORT = config("REDIS_PORT", cast=int)  
    REDIS_PASSWORD = config("REDIS_PASSWORD")
    REDIS_USERNAME = config("REDIS_USERNAME", default="default")
    print(f"[INFO] Redis config loaded: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"[ERROR] Missing Redis environment variables: {e}")
    print("[INFO] Make sure you have REDIS_HOST, REDIS_PORT, REDIS_PASSWORD in your .env file")
    REDIS_HOST = None
    REDIS_PORT = None  
    REDIS_PASSWORD = None
    REDIS_USERNAME = None

# -----------------------------------------------------------
# Gemini client initialization - LAZY LOADING
# -----------------------------------------------------------
client = None

def get_gemini_client():
    """Lazy load Gemini client only when needed"""
    global client
    if client is None and GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        client = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("[INFO] Gemini client lazy-loaded")
    return client

# -----------------------------------------------------------
# mem0 client initialization - LAZY LOADING
# -----------------------------------------------------------
memory = None

def get_memory_client():
    """Lazy load mem0 client only when needed"""
    global memory
    if memory is None and all([PINECONE_API_KEY, PINECONE_INDEX_NAME, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        from mem0 import Memory
        from langchain_pinecone import PineconeEmbeddings
        
        # Configure Pinecone embeddings (Pinecone handles the embedding conversion)
        pinecone_embed = PineconeEmbeddings(
            model="multilingual-e5-large",
            dimension=1024,
            pinecone_api_key=PINECONE_API_KEY
        )
        
        config = {
            "llm": {
                "provider": "litellm",
                "config": {
                    "model": "gemini/gemini-2.0-flash-exp",
                    "api_key": GEMINI_API_KEY
                }
            },
            "embedder": {
                "provider": "langchain",
                "config": {"model": pinecone_embed}
            },
            "vector_store": {
                "provider": "pinecone",
                "config": {
                    "api_key": PINECONE_API_KEY,
                    "collection_name": PINECONE_INDEX_NAME,
                    "embedding_model_dims": 1024,
                    "serverless_config": {
                        "cloud": "aws",
                        "region": "us-east-1"
                    },
                    "metric": "cosine"
                }
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": NEO4J_URI,
                    "username": NEO4J_USERNAME,
                    "password": NEO4J_PASSWORD,
                }
            }
        }
        memory = Memory.from_config(config)
        print("[SUCCESS] mem0 lazy-loaded with Pinecone hosted embeddings and Neo4j graph store")
    return memory

# -----------------------------------------------------------
# Redis client initialization - LAZY LOADING
# -----------------------------------------------------------
redis_client: Optional[any] = None

async def get_redis_client():
    """Lazy load Redis client only when needed"""
    global redis_client
    
    if redis_client is None and all([REDIS_HOST, REDIS_PORT, REDIS_PASSWORD]):
        import redis.asyncio as aioredis
        
        try:
            redis_client = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                username=REDIS_USERNAME,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True
            )
            
            # Test connection
            await redis_client.ping()
            print(f"[SUCCESS] Redis client lazy-loaded and connected to {REDIS_HOST}:{REDIS_PORT}")
            
        except Exception as e:
            print(f"[ERROR] Redis lazy-load failed: {e}")
            redis_client = None
    
    return redis_client

async def init_redis():
    """Initialize Redis connection - now calls lazy loader"""
    return await get_redis_client()

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            print("[INFO] Redis connection closed")
        except Exception as e:
            print(f"[ERROR] Error closing Redis: {e}")

# -----------------------------------------------------------
# Password hashing utilities
# -----------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return hashlib.sha256(password.encode()).hexdigest() == hashed_password

# -----------------------------------------------------------
# Lifespan Events (replaces deprecated on_event)
# -----------------------------------------------------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[STARTUP] FastAPI app starting up...")
    print("[INFO] Using lazy loading for heavy dependencies")
    yield
    # Shutdown
    print("[SHUTDOWN] Closing services...")
    await close_redis()

# Apply lifespan to FastAPI app
app = FastAPI(
    title="Twitter Growth SaaS API", 
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
         "http://localhost:5174", 
         "http://localhost:5175",# Local development
        "https://twitter-growth-agent-1.onrender.com",
        "https://twitter-ai-agent-1.onrender.com",  
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------
# Redis Cache Helper Functions
# -----------------------------------------------------------
async def cache_set(key: str, value: any, expire_seconds: int = 3600) -> bool:
    """Set cache with expiration"""
    redis = await get_redis_client()
    if not redis:
        return False
        
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        await redis.set(key, value, ex=expire_seconds)
        return True
    except Exception as e:
        print(f"[ERROR] Cache set failed for {key}: {e}")
        return False

async def cache_get(key: str):
    """Get from cache"""
    redis = await get_redis_client()
    if not redis:
        return None
        
    try:
        value = await redis.get(key)
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return None
    except Exception as e:
        print(f"[ERROR] Cache get failed for {key}: {e}")
        return None

async def cache_delete(key: str) -> bool:
    """Delete from cache"""
    redis = await get_redis_client()
    if not redis:
        return False
        
    try:
        result = await redis.delete(key)
        return result > 0
    except Exception as e:
        print(f"[ERROR] Cache delete failed for {key}: {e}")
        return False

# -----------------------------------------------------------
# Basic routes
# -----------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Twitter Growth SaaS API is running!"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/test_memory")
async def test_memory():
    """Test endpoint to verify mem0 connection"""
    mem = get_memory_client()
    if not mem:
        return {"error": "Memory not initialized"}
    
    try:
        # Test adding a memory
        mem.add("Test memory for connection", user_id="test_user")
        
        # Test searching
        results = mem.search("Test memory", user_id="test_user")
        
        return {
            "status": "success", 
            "message": "mem0 connected successfully", 
            "results": len(results),
            "pinecone_index": PINECONE_INDEX_NAME
        }
    except Exception as e:
        return {"error": f"mem0 connection failed: {str(e)}"}


@app.get("/test_gemini")
async def test_gemini():
    """Test endpoint to verify Gemini connection"""
    gemini_client = get_gemini_client()
    if not gemini_client:
        return {"error": "Gemini client not initialized"}
    
    try:
        response = gemini_client.generate_content("Say 'Hello, Gemini is working!'")
        return {
            "status": "success",
            "message": "Gemini connected successfully",
            "model": "gemini-2.0-flash-exp",
            "response": response.text
        }
    except Exception as e:
        return {"error": f"Gemini connection failed: {str(e)}"}


@app.get("/test_redis")
async def test_redis():
    """Test Redis connection and operations"""
    redis = await get_redis_client()
    if not redis:
        return {
            "status": "error",
            "error": "Redis not connected", 
            "config": {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "configured": bool(REDIS_HOST and REDIS_PORT and REDIS_PASSWORD)
            }
        }
    
    try:
        # Test ping
        ping_result = await redis.ping()
        
        # Test basic operations
        test_key = f"test_app:{datetime.utcnow().timestamp()}"
        await redis.set(test_key, "Hello from Twitter Growth App!", ex=300)
        value = await redis.get(test_key)
        
        # Clean up test data
        await redis.delete(test_key)
        
        return {
            "status": "success",
            "message": "Redis fully operational with Twitter Growth App",
            "connection": {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "ping": ping_result
            },
            "test_result": value
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Redis test failed: {str(e)}",
            "connection": {
                "host": REDIS_HOST,
                "port": REDIS_PORT
            }
        }


@app.post("/test_core_functions")
async def test_core_functions(user_id: str | None = Cookie(None)):
    """Test endpoint to verify core functions work independently"""
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing")
    
    try:
        from core_functions import core_scrape_user_tweets, core_scrape_top_tweets
        
        # Test both core functions
        print(f"[TEST] Testing core functions for user: {user_id}")
        
        # Test user tweets scraping
        user_result = await core_scrape_user_tweets(user_id)
        
        # Test top tweets scraping  
        top_result = await core_scrape_top_tweets(user_id)
        
        return {
            "status": "success",
            "message": "Core functions tested successfully",
            "user_tweets_result": user_result,
            "top_tweets_result": top_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Core functions test failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/trigger_background_scraping")
async def trigger_background_scraping(user_id: str | None = Cookie(None)):
    """Manual endpoint to trigger background scraping tasks via Celery"""
    try:
        from tasks import scrape_user_tweets_task, scrape_top_tweets_task, trigger_all_user_scraping
        
        if user_id:
            # Trigger for specific user
            user_task = scrape_user_tweets_task.delay(user_id)
            top_task = scrape_top_tweets_task.delay(user_id)
            
            return {
                "status": "success",
                "message": f"Background scraping triggered for user {user_id}",
                "user_tweets_task_id": user_task.id,
                "top_tweets_task_id": top_task.id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Trigger master task for all users
            master_task = trigger_all_user_scraping.delay()
            
            return {
                "status": "success", 
                "message": "Background scraping triggered for all users",
                "master_task_id": master_task.id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to trigger background scraping: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/debug/auth")
async def debug_auth(user_id: str | None = Cookie(None)):
    """Debug endpoint to check authentication status"""
    return {
        "user_id": user_id,
        "authenticated": user_id is not None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/debug/rapidapi")
async def debug_rapidapi(username: str = "elonmusk"):
    """Debug endpoint to test RapidAPI connection"""
    if not RAPIDAPI_KEY:
        return {"error": "RAPIDAPI_KEY not configured"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Test with a known existing user
            profile = await fetch_profile(client, username)
            
            if profile:
                return {
                    "status": "success",
                    "message": "RapidAPI connection working",
                    "test_user": username,
                    "profile_data": profile
                }
            else:
                return {
                    "status": "failed",
                    "message": "RapidAPI connection failed or user not found",
                    "test_user": username
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"RapidAPI test failed: {str(e)}",
                "test_user": username
            }


@app.get("/get_user_profile_image")
async def get_user_profile_image(user_id: str | None = Cookie(None)):
    """Get the current user's profile image URL"""
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "profile_image_url": user.get("profile_image_url"),
        "username": user.get("twitter_username", "You")
    }


@app.get("/get_user_settings")
async def get_user_settings(user_id: str | None = Cookie(None)):
    """Get the current user's settings (non-sensitive data only)"""
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "twitter_username": user.get("twitter_username", ""),
        "search_keywords": user.get("search_keywords", []),
        "target_accounts": user.get("target_accounts", [])
    }


# -----------------------------------------------------------
#  User management
# -----------------------------------------------------------



class SignInRequest(BaseModel):
    email: str
    password: str

@app.get("/verify-auth")
async def verify_auth(user_id: str | None = Cookie(None)):
    """Verify if the user is authenticated via cookie"""
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing")
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(401, "Unauthorized: user not found")
        
        return {
            "authenticated": True,
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "name": user.get("name"),
                "twitter_username": user.get("twitter_username", "")
            }
        }
    except Exception as e:
        raise HTTPException(401, "Unauthorized: invalid user_id")

@app.post("/sign-in", status_code=status.HTTP_200_OK)
async def sign_in(request: SignInRequest, response: Response):
    """
    Single sign-in endpoint that handles both new user creation and existing user authentication.
    - If user exists: verify password and sign in
    - If user doesn't exist: create new user with password and sign in
    Only requires email and password.
    """
    existing_user = await db.users.find_one({"email": request.email})
    
    if existing_user:
        # User exists - verify password
        if not verify_password(request.password, existing_user.get("password", "")):
            raise HTTPException(401, "Invalid password")

        user_id = str(existing_user["_id"])
        response.set_cookie(
            "user_id", 
            user_id, 
            httponly=True,
            secure=True,
            samesite="none",
            max_age=86400  # 24 hours
        )

        return {
            "message": "Sign in successful", 
            "user_id": user_id,
            "user_type": "existing"
        }
    else:
        # User doesn't exist - create new user
        doc = {
            "email": request.email,
            "password": hash_password(request.password),
            "name": None,  # Name is optional
            "x_api_key": None, 
            "target_accounts": [], 
            "search_keywords": []
        }
        
        result = await db.users.insert_one(doc)
        user_id = str(result.inserted_id)
        response.set_cookie(
            "user_id", 
            user_id, 
            httponly=True,
            secure=True,
            samesite="none",
            max_age=86400  # 24 hours
        )
        
        return {
            "message": "Account created and signed in successfully", 
            "user_id": user_id,
            "user_type": "new"
        }


@app.get("/users")
async def get_users():
    users = []
    async for u in db.users.find():
        users.append(
            {
                "id": str(u["_id"]),
                "name": u.get("name"),
                "email": u.get("email"),
                "search_keywords": u.get("search_keywords", []),
                "target_accounts": u.get("target_accounts", []),
            }
        )
    return {"users": users}


# -----------------------------------------------------------
#  Keyword / target-account update endpoints
# -----------------------------------------------------------
class KeywordsModel(BaseModel):
    keywords: list[str]


@app.post("/update_keywords")
async def update_keywords(data: KeywordsModel, user_id: str | None = Cookie(None)):
    if not user_id:
        raise HTTPException(401, "Unauthorized: No user_id cookie found")

    res = await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"search_keywords": data.keywords}}
    )
    # Always return success, even if no changes were made (same values)
    return {"message": "Keywords updated successfully"}


class AccountsModel(BaseModel):
    target_accounts: list[str]


@app.post("/update_target_accounts")
async def update_target_accounts(
    data: AccountsModel, user_id: str | None = Cookie(None)
):
    if not user_id:
        raise HTTPException(401, "Unauthorized: No user_id cookie found")

    if not RAPIDAPI_KEY:
        raise HTTPException(500, "RAPIDAPI_KEY environment variable missing")

    # Step 1: Update target accounts in user document
    res = await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"target_accounts": data.target_accounts}}
    )
    # Continue processing even if no changes were made (same values)

    # Step 2: Automatically scrape the target accounts to populate tracked_accounts collection
    uid = ObjectId(user_id)
    target_accounts = data.target_accounts
    
    print(f"[INFO] Auto-scraping {len(target_accounts)} target accounts for user {uid}")
    
    # Reduced concurrency to avoid rate limits
    sem = asyncio.Semaphore(2)  # Only 2 concurrent requests
    results = []

    async with httpx.AsyncClient() as client:
        # Process accounts one by one to avoid variable capture issues
        for handle in target_accounts:
            async def process_account(current_uid, current_handle):
                async with sem:
                    # Add delay to respect rate limits
                    await asyncio.sleep(1)
                    
                    print(f"[INFO] Fetching profile for: {current_handle}")
                    prof = await fetch_profile(client, current_handle)
                    
                    if not prof:
                        print(f"[WARN] Failed to fetch profile for: {current_handle}")
                        return {"handle": current_handle, "status": "failed"}

                    doc = {
                        "user": current_uid,
                        "username": prof["screenname"],
                        "rest_id": prof["rest_id"],
                        "followers": prof["followersCount"],
                        "description": prof["description"],
                        "profile_image_url": prof.get("profile_image_url"),
                        "updatedAt": datetime.utcnow(),
                    }
                    
                    await db.tracked_accounts.update_one(
                        {"user": current_uid, "username": doc["username"]},
                        {"$set": doc},
                        upsert=True,
                    )
                    
                    print(f"[SUCCESS] Saved account: {doc['username']}")
                    return {"handle": current_handle, "status": "success", "username": doc['username']}

            # Execute each account fetch sequentially to avoid closure issues
            result = await process_account(uid, handle)
            results.append(result)

    successful_count = len([r for r in results if r.get("status") == "success"])
    
    return {
        "message": f"Target accounts updated and {successful_count} accounts processed successfully",
        "results": results,
        "total_processed": len(results)
    }

class TwitterCredsModel(BaseModel):
    twitter_username: str
    twitter_client_id: str
    twitter_client_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str

async def generate_user_persona(user_tweets: List[str]) -> str:
    """
    Generate a detailed persona summary from user's own tweets using Gemini
    """
    gemini_client = get_gemini_client()
    if not gemini_client:
        return "No persona available - AI client not initialized"
    
    if not user_tweets:
        return "No persona available - no tweets found"
    
    # Combine tweets for analysis
    tweets_text = "\n".join(f"- {tweet}" for tweet in user_tweets[:50])  # Max 50 tweets
    
    prompt = f"""Analyze these tweets from a Twitter user and create a COMPRESSED persona profile for AI content filtering and generation. This persona will be used to:
1. Filter which tweets this user should engage with
2. Draft personalized replies that match their style
3. Create repurposed content in their voice

USER'S TWEETS:
{tweets_text}

Create a compressed persona profile with exactly 2,400 characters using this structure:

## [USER TYPE] - COMPRESSED PERSONA

## EXPERTISE & TOPICS
**Primary**: [Main expertise areas]
**Secondary**: [Secondary interests]  
**Level**: [Technical complexity level]
**Experience**: [Professional experience level]

## ENGAGEMENT RULES
**HIGH ENGAGEMENT**:
• [Topic 1 they engage with]
• [Topic 2 they engage with]
• [Topic 3 they engage with]
• [Topic 4 they engage with]
• [Topic 5 they engage with]

**AVOID**:
• [Topic 1 they avoid]
• [Topic 2 they avoid]
• [Topic 3 they avoid]
• [Topic 4 they avoid]

**AUTHORITY AREAS**:
• [Area 1 they give advice on]
• [Area 2 they give advice on]
• [Area 3 they give advice on]
• [Area 4 they give advice on]

## VOICE & TONE
**Style**: [Communication style]
**Structure**: [Sentence patterns]
**Vocabulary**: [Language complexity]
**Personality**: [Key personality traits]
**Emotional**: [How they express emotions]

## CONTENT STYLE
**Length**: [Typical tweet length]
**Key Phrases**: [Common expressions they use]
**Format**: [Formatting preferences]
**Approach**: [How they explain things]
**CTA Style**: [Call-to-action approach]
**Value**: [What value they provide]

CRITICAL: The final output must be EXACTLY 2,400 characters. Count carefully and adjust content to meet this requirement precisely. Be concise but comprehensive."""

    try:
        response = gemini_client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to generate persona: {e}")
        if "404" in str(e) or "not found" in str(e).lower():
            print(f"[ERROR] Model not found - check if gemini-2.0-flash-exp is available in your region")
            return "No persona available - model not found"
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            print(f"[ERROR] API quota exceeded")
            return "No persona available - API quota exceeded"
        else:
            return f"No persona available - generation failed: {str(e)}"

@app.post("/update_twitter_credentials")
async def update_twitter_credentials(
    creds: TwitterCredsModel,
    user_id: str | None = Cookie(None),
):
    """
    Store the logged-in user's X (Twitter) OAuth 1.0a credentials and generate persona.
    """
    if not user_id:
        raise HTTPException(401, "Unauthorized: No user_id cookie found")

    if not RAPIDAPI_KEY:
        raise HTTPException(500, "RAPIDAPI_KEY environment variable missing")

    # First save the credentials
    res = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "twitter_username": creds.twitter_username,
                "twitter_client_id": creds.twitter_client_id,
                "twitter_client_secret": creds.twitter_client_secret,
                "twitter_access_token": creds.twitter_access_token,
                "twitter_access_token_secret": creds.twitter_access_token_secret,
            }
        },
    )

    # Continue processing even if no changes were made (same values)

    # Now scrape user's own tweets to generate persona
    username = creds.twitter_username.replace("@", "")  # Remove @ if present
    
    async with httpx.AsyncClient() as http_client:
        try:
            # Step 1: Get user profile to get rest_id
            print(f"[INFO] Fetching profile for user: {username}")
            profile = await fetch_profile(http_client, username)
            
            if not profile or not profile.get("rest_id"):
                print(f"[WARN] Could not get profile for {username}")
                return {
                    "message": "Twitter credentials updated successfully", 
                    "persona_status": "failed - profile not found",
                    "error_details": f"Unable to fetch Twitter profile for username '{username}'. Please verify the username exists and try again. This may be due to: 1) Username doesn't exist, 2) API rate limit, 3) API key issues."
                }
            
            rest_id = profile["rest_id"]
            user_profile_image_url = profile.get("profile_image_url")
            print(f"[INFO] Got rest_id {rest_id} and profile image for {username}")
            
            # Save the user's profile image URL to their record
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"profile_image_url": user_profile_image_url}}
            )
            print(f"[SUCCESS] Saved user's profile image URL: {user_profile_image_url}")
            
            # Step 2: Fetch user's own tweets
            print(f"[INFO] Fetching tweets for user: {username}")
            url = f"https://twitter-aio.p.rapidapi.com/user/{rest_id}/tweets"
            headers = {
                "x-rapidapi-host": "twitter-aio.p.rapidapi.com", 
                "x-rapidapi-key": RAPIDAPI_KEY,
                "accept": "application/json",
            }
            params = {
                "count": 50,  # Get up to 50 tweets
                "filters": '{"includeRetweets":true,"removeReplies":false,"removePostsWithLinks":false}'
            }

            r = await http_client.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            
            data = r.json()
            instructions = (
                data.get("user", {})
                    .get("result", {})
                    .get("timeline", {})
                    .get("timeline", {})
                    .get("instructions", [])
            )

            entries = []
            for inst in instructions:
                entries.extend(inst.get("entries", []))

            tweets = []
            for entry in entries:
                tweet = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result")
                legacy = tweet.get("legacy") if tweet else None
                if not legacy:
                    continue

                note_text = (
                    tweet.get("note_tweet", {})
                        .get("note_tweet_results", {})
                        .get("result", {})
                        .get("text")
                )
                text = note_text or legacy.get("full_text")
                
                if not text:  # Only skip if no text at all
                    continue
                    
                tweets.append(text)

            print(f"[INFO] Found {len(tweets)} tweets for persona generation")
            
            if tweets:
                # Step 3: Generate persona using Gemini
                print(f"[INFO] Generating persona for {username} using {len(tweets)} tweets")
                persona = await generate_user_persona(tweets)
                
                # Step 4: Save persona to user document
                await db.users.update_one(
        {"_id": ObjectId(user_id)},
                    {"$set": {"user_persona": persona}}
                )
                
                print(f"[SUCCESS] Generated and saved persona for {username}")
                
                # Step 5: Store persona and individual tweets in mem0 (max 50 tweets)
                mem = get_memory_client()
                if mem:
                    try:
                        # Store the generated persona
                        mem.add(f"User's initial persona based on their Twitter posting history: {persona}", user_id=user_id)
                        print(f"[SUCCESS] Stored persona in mem0 memory layer for {username}")
                        
                        # Store individual tweets (max 50) for detailed behavioral intelligence
                        tweets_to_store = tweets[:50]  # Max 50 tweets
                        for i, tweet in enumerate(tweets_to_store):
                            mem.add(f"User's historical tweet {i+1}: {tweet}", user_id=user_id)
                        
                        print(f"[SUCCESS] Stored {len(tweets_to_store)} individual tweets in mem0 for {username}")
                        
                    except Exception as e:
                        print(f"[ERROR] Failed to store in mem0: {e}")
                
                return {
                    "message": "Twitter credentials updated and persona generated successfully", 
                    "persona_status": "success",
                    "tweets_processed": len(tweets),
                    "tweets_stored_in_mem0": min(len(tweets), 50)
                }
            else:
                print(f"[WARN] No tweets found for {username}")
                return {"message": "Twitter credentials updated successfully", "persona_status": "no_tweets_found"}
                
        except Exception as e:
            print(f"[ERROR] Failed to generate persona for {username}: {e}")
            return {
                "message": "Twitter credentials updated successfully", 
                "persona_status": "failed",
                "error_details": f"Persona generation failed: {str(e)}"
            }

    return {
        "message": "Twitter credentials updated successfully",
        "persona_status": "skipped - no persona generation attempted"
    }



# -----------------------------------------------------------
#  SCRAPE TRACKED ACCOUNTS  (n8n "Get User Data" equivalent)
# -----------------------------------------------------------
async def fetch_profile(client: httpx.AsyncClient, username: str) -> dict | None:
    """
    Call twitter-aio and return a cleaned profile dict, or None on error.
    """
    # Clean the username - remove @ if present and strip whitespace
    clean_username = username.replace("@", "").strip()
    
    url = f"https://twitter-aio.p.rapidapi.com/user/by/username/{clean_username}"
    headers = {
        "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "accept": "application/json",
    }

    print(f"[DEBUG] Fetching profile for cleaned username: '{clean_username}'")
    print(f"[DEBUG] Full URL: {url}")
    print(f"[DEBUG] Using API key: {RAPIDAPI_KEY[:10]}..." if RAPIDAPI_KEY else "[DEBUG] No API key found")

    try:
        r = await client.get(url, headers=headers, timeout=30)
        print(f"[DEBUG] Response status: {r.status_code}")
        print(f"[DEBUG] Response headers: {dict(r.headers)}")
        
        if r.status_code == 400:
            error_text = r.text
            print(f"[ERROR] 400 Bad Request - Response body: {error_text}")
            
            # Check if it's a "User not found" error
            if "not found" in error_text.lower() or "does not exist" in error_text.lower():
                print(f"[ERROR] Twitter user '{clean_username}' does not exist")
                return None
            elif "rate limit" in error_text.lower():
                print(f"[ERROR] Rate limit exceeded for API")
                return None
            else:
                print(f"[ERROR] Unknown 400 error: {error_text}")
                return None
        
        r.raise_for_status()
        
        response_data = r.json()
        print(f"[DEBUG] Raw API response for {clean_username}: {response_data}")
        
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        print(f"[ERROR] API call failed for {clean_username}: {exc}")
        if hasattr(exc, 'response') and exc.response:
            try:
                error_body = exc.response.text
                print(f"[ERROR] Response body: {error_body}")
            except:
                print(f"[ERROR] Could not read response body")
        return None

    # Handle different response structures
    user_block = response_data.get("user", {}).get("result")
    if not user_block:
        print(f"[ERROR] No user block found for {username}")
        return None

    # Try multiple paths for screen_name (API structure varies)
    legacy = user_block.get("legacy", {})
    core = user_block.get("core", {})
    
    # Try different extraction methods based on your n8n flow
    screenname = (
        core.get("screen_name") or          # From core (newer API)
        legacy.get("screen_name") or        # From legacy (older API)
        core.get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
    )
    
    if not screenname:
        print(f"[ERROR] No screen_name found for {username}")
        print(f"[DEBUG] Core data: {core}")
        print(f"[DEBUG] Legacy data: {legacy}")
        return None

    # Extract other fields with fallbacks
    followers_count = (
        legacy.get("followers_count") or 
        core.get("followers_count") or 
        0
    )
    
    description = (
        legacy.get("description") or 
        core.get("description") or 
        ""
    )

    # Extract profile image URL with fallbacks
    avatar = user_block.get("avatar", {})
    profile_image_url = (
        avatar.get("image_url") or                    # NEW: This is where the actual profile image is!
        legacy.get("profile_image_url_https") or
        core.get("profile_image_url_https") or
        legacy.get("profile_image_url") or
        core.get("profile_image_url") or
        None
    )

    profile = {
        "screenname": screenname,
        "rest_id": user_block.get("rest_id"),
        "followersCount": followers_count,
        "description": description,
        "profile_image_url": cleanup_profile_image_url(profile_image_url),
    }
    
    print(f"[SUCCESS] Extracted profile for {username}: {profile}")
    return profile


def cleanup_profile_image_url(url: str) -> str:
    """
    Fix common typos and issues in Twitter profile image URLs
    """
    if not url:
        return url
    
    original_url = url
    
    # Fix the "noormal" typo to "normal"
    url = url.replace("_noormal.jpg", "_normal.jpg")
    url = url.replace("_noormal.png", "_normal.png")
    
    # Fix any other common typos we might encounter
    url = url.replace("_normall.jpg", "_normal.jpg")  # double 'l'
    url = url.replace("_norml.jpg", "_normal.jpg")    # missing 'a'
    
    # Debug logging if we made changes
    if url != original_url:
        print(f"[URL CLEANUP] Fixed: {original_url} → {url}")
    
    return url


@app.post("/scrape_tracked_accounts")
async def scrape_tracked_accounts(user_id: str | None = Cookie(None)):
    if not RAPIDAPI_KEY:
        raise HTTPException(500, "RAPIDAPI_KEY environment variable missing")

    user_filter = {"_id": ObjectId(user_id)} if user_id else {}
    cursor = db.users.find(user_filter)

    # Reduced concurrency to avoid rate limits
    sem = asyncio.Semaphore(2)  # Only 2 concurrent requests
    results = []

    async with httpx.AsyncClient() as client:
        async for user in cursor:
            uid = user["_id"]
            target_accounts = user.get("target_accounts", [])
            
            print(f"[INFO] Processing user {uid} with accounts: {target_accounts}")

            # Process accounts one by one to avoid variable capture issues
            for handle in target_accounts:
                async def process_account(current_uid, current_handle):
                    async with sem:
                        # Add delay to respect rate limits
                        await asyncio.sleep(1)
                        
                        print(f"[INFO] Fetching profile for: {current_handle}")
                        prof = await fetch_profile(client, current_handle)
                        
                        if not prof:
                            print(f"[WARN] Failed to fetch profile for: {current_handle}")
                            return {"handle": current_handle, "status": "failed"}

                        doc = {
                            "user": current_uid,
                            "username": prof["screenname"],
                            "rest_id": prof["rest_id"],
                            "followers": prof["followersCount"],
                            "description": prof["description"],
                            "profile_image_url": prof.get("profile_image_url"),
                            "updatedAt": datetime.utcnow(),
                        }
                        
                        await db.tracked_accounts.update_one(
                            {"user": current_uid, "username": doc["username"]},
                            {"$set": doc},
                            upsert=True,
                        )
                        
                        print(f"[SUCCESS] Saved account: {doc['username']}")
                        return {"handle": current_handle, "status": "success", "username": doc['username']}

                # Execute each account fetch sequentially to avoid closure issues
                result = await process_account(uid, handle)
                results.append(result)

    return {
        "message": "Tracked accounts processing completed",
        "results": results,
        "total_processed": len(results)
    } 

async def fetch_top_tweets_for_keyword(client: httpx.AsyncClient, keyword: str) -> List[dict]:
    """
    Helper function to call twitter-aio via RapidAPI for a search term.
    Processes the response to extract relevant tweets.
    Returns a list of cleaned tweet dicts.
    """
    if not RAPIDAPI_KEY:
        raise RuntimeError("RAPIDAPI_KEY is missing")

    url = f"https://twitter-aio.p.rapidapi.com/search/{keyword.replace(' ', '%20')}"
    headers = {
        "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "accept": "application/json",
    }
    params = {
        "count": "20",
        "category": "latest",
        "lang": "en",
        "filters": '{"includeRetweets":false,"removeReplies":true,"removePostsWithLinks":true,"min_likes":50}'
    }

    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        print(f"[WARN] fetch_top_tweets error for '{keyword}': {exc}")
        return []

    response_json = r.json()

    # Flatten & clean tweet results (matches your n8n Code node)
    output = []
    for category in response_json if isinstance(response_json, list) else [response_json]:
        entries = category.get("entries", [])
        for entry_group in entries:
            sub_entries = entry_group.get("entries", [])
            for entry in sub_entries:
                tweet_data = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result")
                tweet = tweet_data.get("tweet") if tweet_data else tweet_data
                legacy = tweet.get("legacy") if tweet else None
                if not legacy:
                    continue

                username = (
                    tweet.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                    or entry.get("content", {}).get("item", {}).get("itemContent", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                )

                note_text = tweet.get("note_tweet", {}).get("note_tweet_results", {}).get("result", {}).get("text")
                full_text = legacy.get("full_text")

                cleaned = {
                    "text": note_text or full_text,
                    "created_at": legacy.get("created_at"),
                    "conversation_id_str": legacy.get("conversation_id_str"),
                    "user_id_str": legacy.get("user_id_str"),
                    "username": username,
                }
                output.append(cleaned)

    return output


# -----------------------------------------------------------
#SIMPLIFIED BEHAVIORAL INTELLIGENCE SYSTEM
# -----------------------------------------------------------

async def select_draft_and_repurpose_tweets(tweets: List[dict], user_persona: str, keyword: str, user_id: str) -> List[dict]:
    """
    BEHAVIORAL INTELLIGENCE TRIPLE COMBO: Select exactly 5 tweets + draft replies + draft repurposed content 
    using unified behavioral intelligence from memory layer
    """
    gemini_client = get_gemini_client()
    if not tweets or not gemini_client or not user_id:
        return []
    
    # Ensure we have tweets to work with
    if len(tweets) == 0:
        return []
    
    # GET BEHAVIORAL INTELLIGENCE FROM MEMORY LAYER
    print(f"[BEHAVIORAL] Gathering behavioral intelligence from memory layer for user {user_id}...")
    behavioral_context = await get_behavioral_intelligence(user_id, limit=200)
    
    print(f"[BEHAVIORAL] Retrieved behavioral intelligence from memory layer")
    
    # Pre-filter promotional content before sending to LLM
    filtered_tweets = []
    skip_indicators = [
        "$", "🚀", "🔍", "🌐", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
        "looking to connect", "let's connect", "DM me", 
        "fellow devs", "What are you building", "share feedback"
    ]
    
    for tweet in tweets:
        tweet_text = tweet.get('text', '')
        should_skip = any(indicator.lower() in tweet_text.lower() for indicator in skip_indicators)
        emoji_count = sum(1 for char in tweet_text if ord(char) > 127 and ord(char) != 8217)
        
        if not should_skip and emoji_count <= 3:
            filtered_tweets.append(tweet)
    
    # Use filtered tweets or original if not enough remain
    working_tweets = filtered_tweets if len(filtered_tweets) >= 10 else tweets
    
    # Build tweet list for LLM
    tweet_list = ""
    for i, tweet in enumerate(working_tweets, 1):
        tweet_list += f"{i}. @{tweet.get('username', 'unknown')}: \"{tweet['text'][:250]}\"\n"
    
    # SIMPLE ADAPTIVE APPROACH
    if behavioral_context.strip():
        print(f"[STRATEGY] Using behavioral intelligence from memory layer")
        intelligence_section = f"""You are a Twitter growth AI with access to this user's behavioral intelligence:

{behavioral_context}

Use this data to make optimal decisions for content selection, drafting, and engagement."""
    else:
        print(f"[STRATEGY] No behavioral intelligence available - using persona-based approach")
        intelligence_section = f"""You are a Twitter growth AI. Use this persona to guide your decisions:

{user_persona}

Focus on authentic, valuable content that matches this persona."""
    
    # BUILD SIMPLE PROMPT
    prompt = f"""{intelligence_section}

TWEETS FOR KEYWORD "{keyword}":
{tweet_list}

REQUIREMENTS:
- Select exactly 5 tweets from your areas of expertise
- Provide genuine value, avoid promotional content  
- Replies: Under 20 words, NO emojis, authentic style
- Repurposed content: Under 25 words, NO hashtags, NO emojis

OUTPUT FORMAT (EXACTLY 5 ENTRIES):
Tweet 3:
Reply: [Your reply draft]
Repurpose: [Your repurposed version]

Tweet 7:
Reply: [Your reply draft]
Repurpose: [Your repurposed version]

Tweet 12:
Reply: [Your reply draft]
Repurpose: [Your repurposed version]

Tweet 15:
Reply: [Your reply draft]
Repurpose: [Your repurposed version]

Tweet 18:
Reply: [Your reply draft]
Repurpose: [Your repurposed version]"""

    try:
        response = gemini_client.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse the response to extract tweet selections, replies, and repurposed content
        selected_tweets = []
        lines = response_text.split('\n')
        
        current_tweet_num = None
        current_reply = None
        current_repurpose = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for tweet number
            if line.startswith('Tweet ') and ':' in line:
                # Save previous tweet if we have complete data
                if current_tweet_num and current_reply and current_repurpose:
                    if 1 <= current_tweet_num <= len(working_tweets):
                        tweet = working_tweets[current_tweet_num - 1]
                        selected_tweets.append({
                            'tweet': tweet,
                            'draft_reply': current_reply,
                            'draft_post': current_repurpose
                        })
                
                # Start new tweet
                try:
                    current_tweet_num = int(line.split()[1].replace(':', ''))
                    current_reply = None
                    current_repurpose = None
                except:
                    continue
                    
            elif line.startswith('Reply:'):
                current_reply = line.replace('Reply:', '').strip()
                
            elif line.startswith('Repurpose:'):
                current_repurpose = line.replace('Repurpose:', '').strip()
        
        # Don't forget the last tweet
        if current_tweet_num and current_reply and current_repurpose:
            if 1 <= current_tweet_num <= len(working_tweets):
                tweet = working_tweets[current_tweet_num - 1]
                selected_tweets.append({
                    'tweet': tweet,
                    'draft_reply': current_reply,
                    'draft_post': current_repurpose
                })
        
        # Ensure we have exactly 5 selections
        if len(selected_tweets) < 5:
            print(f"[WARN] Only got {len(selected_tweets)} complete selections, using fallback")
            selected_indices = {working_tweets.index(s['tweet']) for s in selected_tweets}
            
            for i, tweet in enumerate(working_tweets):
                if len(selected_tweets) >= 5:
                    break
                if i not in selected_indices:
                    selected_tweets.append({
                        'tweet': tweet,
                        'draft_reply': "Thanks for sharing! This is really insightful.",
                        'draft_post': "Interesting perspective on this topic. Worth considering for implementation."
                    })
        
        # Take only first 5 if we somehow got more
        selected_tweets = selected_tweets[:5]
        
        print(f"[SUCCESS] Selected {len(selected_tweets)} tweets using unified behavioral intelligence for '{keyword}'")
        return selected_tweets
        
    except Exception as e:
        print(f"[ERROR] Behavioral intelligence triple combo failed: {e}")
        # Fallback: select first 5 tweets with generic content
        fallback_selections = []
        for i, tweet in enumerate(working_tweets[:5]):
            fallback_selections.append({
                'tweet': tweet,
                'draft_reply': "Thanks for sharing! This is really insightful.",
                'draft_post': "Interesting perspective on this topic. Worth considering."
            })
        return fallback_selections


async def select_and_draft_user_tweet_replies(tweets: List[dict], user_persona: str, target_username: str, user_id: str) -> List[dict]:
    """
    BEHAVIORAL INTELLIGENCE FOR USER TWEETS: Select exactly 5 tweets + draft replies
    using unified behavioral intelligence from memory layer
    """
    gemini_client = get_gemini_client()
    if not tweets or not gemini_client or not user_id:
        return []
    
    # Ensure we have tweets to work with
    if len(tweets) == 0:
        return []
    
    # GET BEHAVIORAL INTELLIGENCE FROM MEMORY LAYER
    print(f"[BEHAVIORAL] Gathering behavioral intelligence from memory layer for user {user_id}...")
    behavioral_context = await get_behavioral_intelligence(user_id, limit=200)
    
    print(f"[BEHAVIORAL] Retrieved behavioral intelligence from memory layer")
    
    # Pre-filter promotional content before sending to LLM
    filtered_tweets = []
    skip_indicators = [
        "$", "🚀", "🔍", "🌐", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
        "looking to connect", "let's connect", "DM me", 
        "fellow devs", "What are you building", "share feedback"
    ]
    
    for tweet in tweets:
        tweet_text = tweet.get('text', '')
        should_skip = any(indicator.lower() in tweet_text.lower() for indicator in skip_indicators)
        emoji_count = sum(1 for char in tweet_text if ord(char) > 127 and ord(char) != 8217)
        
        if not should_skip and emoji_count <= 3:
            filtered_tweets.append(tweet)
    
    # Use filtered tweets or original if not enough remain
    working_tweets = filtered_tweets if len(filtered_tweets) >= 10 else tweets
    
    # Build tweet list for LLM
    tweet_list = ""
    for i, tweet in enumerate(working_tweets, 1):
        tweet_list += f"{i}. @{tweet.get('username', 'unknown')}: \"{tweet['text'][:250]}\"\n"
    
    # SIMPLE ADAPTIVE APPROACH
    if behavioral_context.strip():
        print(f"[STRATEGY] Using behavioral intelligence from memory layer")
        intelligence_section = f"""You are a Twitter growth AI with access to this user's behavioral intelligence:

{behavioral_context}

Use this data to make optimal decisions for content selection, drafting, and engagement."""
    else:
        print(f"[STRATEGY] No behavioral intelligence available - using persona-based approach")
        intelligence_section = f"""You are a Twitter growth AI. Use this persona to guide your decisions:

{user_persona}

Focus on authentic, valuable content that matches this persona."""
    
    # BUILD SIMPLE PROMPT
    prompt = f"""{intelligence_section}

TWEETS FROM @{target_username}:
{tweet_list}

REQUIREMENTS:
- Select exactly 5 tweets from your areas of expertise
- Provide genuine value, avoid promotional content
- Replies: Under 20 words, NO emojis, authentic style

OUTPUT FORMAT (EXACTLY 5 ENTRIES):
Tweet 3:
Reply: [Your reply draft]

Tweet 7:
Reply: [Your reply draft]

Tweet 12:
Reply: [Your reply draft]

Tweet 15:
Reply: [Your reply draft]

Tweet 18:
Reply: [Your reply draft]"""

    try:
        response = gemini_client.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse the response to extract tweet selections and replies
        selected_tweets = []
        lines = response_text.split('\n')
        
        current_tweet_num = None
        current_reply = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for tweet number
            if line.startswith('Tweet ') and ':' in line:
                # Save previous tweet if we have complete data
                if current_tweet_num and current_reply:
                    if 1 <= current_tweet_num <= len(working_tweets):
                        tweet = working_tweets[current_tweet_num - 1]
                        selected_tweets.append({
                            'tweet': tweet,
                            'draft_reply': current_reply
                        })
                
                # Start new tweet
                try:
                    current_tweet_num = int(line.split()[1].replace(':', ''))
                    current_reply = None
                except:
                    continue
                    
            elif line.startswith('Reply:'):
                current_reply = line.replace('Reply:', '').strip()
        
        # Don't forget the last tweet
        if current_tweet_num and current_reply:
            if 1 <= current_tweet_num <= len(working_tweets):
                tweet = working_tweets[current_tweet_num - 1]
                selected_tweets.append({
                    'tweet': tweet,
                    'draft_reply': current_reply
                })
        
        # Ensure we have exactly 5 selections
        if len(selected_tweets) < 5:
            print(f"[WARN] Only got {len(selected_tweets)} complete selections, using fallback")
            selected_indices = {working_tweets.index(s['tweet']) for s in selected_tweets}
            
            for i, tweet in enumerate(working_tweets):
                if len(selected_tweets) >= 5:
                    break
                if i not in selected_indices:
                    selected_tweets.append({
                        'tweet': tweet,
                        'draft_reply': "Thanks for sharing! This is really insightful."
                    })
        
        # Take only first 5 if we somehow got more
        selected_tweets = selected_tweets[:5]
        
        print(f"[SUCCESS] Selected {len(selected_tweets)} tweets using unified behavioral intelligence for @{target_username}")
        return selected_tweets
        
    except Exception as e:
        print(f"[ERROR] Behavioral intelligence dual combo failed: {e}")
        # Fallback: select first 5 tweets with generic content
        fallback_selections = []
        for i, tweet in enumerate(working_tweets[:5]):
            fallback_selections.append({
                'tweet': tweet,
                'draft_reply': "Thanks for sharing! This is really insightful."
            })
        return fallback_selections


async def fetch_top_tweets(client: httpx.AsyncClient, keyword: str) -> List[dict]:
    """
    Call twitter-aio via RapidAPI for a search term - CORRECTED VERSION
    Based on actual n8n flow structure
    """
    if not RAPIDAPI_KEY:
        raise RuntimeError("RAPIDAPI_KEY is missing")

    # URL encode the keyword
    encoded_keyword = keyword.replace(' ', '%20')
    url = f"https://twitter-aio.p.rapidapi.com/search/{encoded_keyword}"
    
    headers = {
        "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "accept": "application/json",
    }
    
    params = {
        "count": "20",                    # fetch 20 tweets per keyword
        "category": "latest",
        "lang": "en",
        # Exclude tweets that already contain links at the API layer
        "filters": '{"includeRetweets":false,"removeReplies":true,"removePostsWithLinks":true,"min_likes":100}'
    }

    print(f"[INFO] Searching tweets for keyword: '{keyword}'")
    print(f"[DEBUG] Full URL: {url}?{urlencode(params)}")

    try:
        r = await client.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        print(f"[SUCCESS] API response status: {r.status_code}")
    except Exception as exc:
        print(f"[ERROR] API call failed for '{keyword}': {exc}")
        return []

    try:
        response_json = r.json()
        print(f"[DEBUG] Raw response type: {type(response_json)}")
        
        # Log the actual structure we got
        if isinstance(response_json, dict):
            print(f"[DEBUG] Response keys: {list(response_json.keys())}")
            # Check if it has the expected structure
            if 'entries' in response_json:
                print(f"[DEBUG] Found 'entries' key with {len(response_json['entries'])} items")
        
    except Exception as exc:
        print(f"[ERROR] JSON parsing failed: {exc}")
        return []

    # CORRECTED: Based on your n8n flow, response is a single object, not array
    output = []
    
    # The response is a single category object (not an array)
    category = response_json
    entries = category.get("entries", [])
    print(f"[DEBUG] Processing {len(entries)} top-level entries")
    
    for entry_idx, entry_group in enumerate(entries):
        if not isinstance(entry_group, dict):
            continue
            
        sub_entries = entry_group.get("entries", [])
        print(f"[DEBUG] Entry group {entry_idx} has {len(sub_entries)} sub-entries")
        
        for sub_idx, entry in enumerate(sub_entries):
            try:
                # Navigate exactly like your n8n Code4 node
                content = entry.get("content", {})
                item_content = content.get("itemContent", {})
                tweet_results = item_content.get("tweet_results", {})
                result = tweet_results.get("result")
                
                if not result:
                    print(f"[DEBUG] No result in entry {entry_idx}-{sub_idx}")
                    continue
                
                # Handle TweetWithVisibilityResults wrapper (from n8n)
                tweet = result.get("tweet") or result
                legacy = tweet.get("legacy") if tweet else None
                
                if not legacy:
                    print(f"[DEBUG] No legacy data in entry {entry_idx}-{sub_idx}")
                    continue

                # Extract username - EXACT n8n logic
                username = None
                profile_image_url = None
                
                # Path 1: tweet?.core?.user_results?.result?.legacy?.screen_name
                if tweet and "core" in tweet:
                    core_user = tweet["core"].get("user_results", {}).get("result", {})
                    username = core_user.get("legacy", {}).get("screen_name")
                    
                    # Extract profile image - COMPREHENSIVE FALLBACK LOGIC
                    legacy_user = core_user.get("legacy", {})
                    profile_image_url = (
                        legacy_user.get("profile_image_url_https") or
                        legacy_user.get("profile_image_url") or
                        legacy_user.get("profile_image_url_normal") or
                        legacy_user.get("profile_image_url_bigger") or
                        legacy_user.get("profile_image_url_mini") or
                        None
                    )
                    
                    # Additional fallback: check if avatar exists at user level
                    if not profile_image_url:
                        avatar = core_user.get("avatar", {})
                        profile_image_url = avatar.get("image_url")
                    
                    # DEBUG: Log the user structure to find profile image
                    if username and not profile_image_url:
                        print(f"[DEBUG] Path 1 - MISSING PROFILE for {username}")
                        print(f"[DEBUG] Path 1 - Legacy keys: {list(legacy_user.keys())}")
                        print(f"[DEBUG] Path 1 - User keys: {list(core_user.keys())}")
                        # Show all profile-related fields
                        profile_fields = {k: v for k, v in legacy_user.items() if 'profile' in k.lower() or 'image' in k.lower() or 'avatar' in k.lower()}
                        print(f"[DEBUG] Path 1 - Profile-related fields: {profile_fields}")
                
                # Path 2: entry?.content?.item?.itemContent?.user_results?.result?.legacy?.screen_name  
                if not username:
                    item = content.get("item", {})
                    item_content_alt = item.get("itemContent", {})
                    user_results = item_content_alt.get("user_results", {})
                    if user_results.get("result"):
                        username = user_results["result"].get("legacy", {}).get("screen_name")
                        
                        # Extract profile image - COMPREHENSIVE FALLBACK LOGIC
                        legacy_user = user_results["result"].get("legacy", {})
                        profile_image_url = (
                            legacy_user.get("profile_image_url_https") or
                            legacy_user.get("profile_image_url") or
                            legacy_user.get("profile_image_url_normal") or
                            legacy_user.get("profile_image_url_bigger") or
                            legacy_user.get("profile_image_url_mini") or
                            None
                        )
                        
                        # Additional fallback: check if avatar exists at user level
                        if not profile_image_url:
                            avatar = user_results["result"].get("avatar", {})
                            profile_image_url = avatar.get("image_url")
                        
                        # DEBUG: Log the user structure to find profile image
                        if username and not profile_image_url:
                            print(f"[DEBUG] Path 2 - MISSING PROFILE for {username}")
                            print(f"[DEBUG] Path 2 - Legacy keys: {list(legacy_user.keys())}")
                            print(f"[DEBUG] Path 2 - User keys: {list(user_results['result'].keys())}")
                            # Show all profile-related fields
                            profile_fields = {k: v for k, v in legacy_user.items() if 'profile' in k.lower() or 'image' in k.lower() or 'avatar' in k.lower()}
                            print(f"[DEBUG] Path 2 - Profile-related fields: {profile_fields}")

                # Extract text - EXACT n8n logic
                note_text = None
                if tweet and "note_tweet" in tweet:
                    note_results = tweet["note_tweet"].get("note_tweet_results", {})
                    if note_results.get("result"):
                        note_text = note_results["result"].get("text")
                
                full_text = legacy.get("full_text")
                tweet_text = note_text or full_text

                if not tweet_text:
                    print(f"[DEBUG] No text in entry {entry_idx}-{sub_idx}")
                    continue

                # Create tweet object
                tweet_obj = {
                    "text": tweet_text,
                    "created_at": legacy.get("created_at"),
                    "conversation_id_str": legacy.get("conversation_id_str"),
                    "user_id_str": legacy.get("user_id_str"),
                    "username": username,
                    "profile_image_url": cleanup_profile_image_url(profile_image_url),  # NEW: Clean profile image URL
                    "keyword": keyword,
                }
                
                output.append(tweet_obj)
                print(f"[SUCCESS] Extracted: @{username or 'unknown'}: {tweet_text[:100]}... | Profile: {cleanup_profile_image_url(profile_image_url) or 'None'}")
                
                # Track accounts with missing profile images for debugging
                if not profile_image_url:
                    print(f"[PROFILE MISSING] @{username}: No profile image found in API response")
                    # Show what profile-related fields we do have
                    if tweet and "core" in tweet:
                        core_user = tweet["core"].get("user_results", {}).get("result", {})
                        legacy_user = core_user.get("legacy", {})
                        profile_fields = {k: v for k, v in legacy_user.items() if 'profile' in k.lower() or 'image' in k.lower() or 'avatar' in k.lower() or 'photo' in k.lower()}
                        print(f"[PROFILE MISSING] @{username} available profile fields: {profile_fields}")
                else:
                    print(f"[PROFILE SUCCESS] @{username}: Got profile image")
                
            except Exception as exc:
                print(f"[ERROR] Failed to process entry {entry_idx}-{sub_idx}: {exc}")
                continue

    print(f"[SUMMARY] Found {len(output)} tweets for '{keyword}'")
    return output 


@app.post("/scrape_top_tweets")
async def scrape_top_tweets(user_id: str | None = Cookie(None)):
    """
    Enhanced keyword-based tweet scraping with triple combo: selection + reply drafting + repurposing
    """
    if not RAPIDAPI_KEY:
        raise HTTPException(500, "RAPIDAPI_KEY environment variable missing")
    
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(500, "Gemini client not initialized")

    user_filter = {"_id": ObjectId(user_id)} if user_id else {}
    cursor = db.users.find(user_filter)
    results = []

    async with httpx.AsyncClient() as http_client:
        async for user in cursor:
            uid = user["_id"]
            search_keywords = user.get("search_keywords", [])
            
            # Get user persona for LLM filtering
            user_persona = user.get("user_persona", "")
            
            print(f"[INFO] Processing user {uid} with keywords: {search_keywords}")
            print(f"[INFO] User has persona: {'Yes' if user_persona else 'No'}")

            # Process keywords sequentially (same as before)
            for keyword in search_keywords:
                print(f"[INFO] Fetching tweets for keyword: {keyword}")
                
                await asyncio.sleep(2)  # Same rate limiting as before
                
                # Fetch tweets using your existing function
                tweets = await fetch_top_tweets(http_client, keyword)
                
                if not tweets:
                    print(f"[WARN] No tweets found for keyword: {keyword}")
                    results.append({"keyword": keyword, "status": "no_tweets", "count": 0})
                    continue

                print(f"[INFO] Found {len(tweets)} candidate tweets for keyword: {keyword}")
                
                # NEW: Behavioral Intelligence Triple combo - selection + reply drafting + repurposing
                selected_tweets = await select_draft_and_repurpose_tweets(tweets, user_persona, keyword, user_id)
                print(f"[INFO] Selected {len(selected_tweets)} tweets with behavioral intelligence for keyword: {keyword}")
                
                # If no behavioral intelligence available, fallback is handled inside the function
                
                # Save selected tweets with draft replies and repurposed content
                saved_count = 0
                for selection in selected_tweets:
                    tweet = selection['tweet']
                    draft_reply = selection['draft_reply']
                    draft_post = selection['draft_post']
                    
                    # Validation
                    if not tweet.get("conversation_id_str") or not tweet.get("text"):
                        continue
                        
                    tweet_doc = {
                        # Core tweet data
                        "user": uid,
                        "keyword": keyword,
                        "conversation_id_str": tweet["conversation_id_str"],
                        "text": tweet["text"],
                        "user_id_str": tweet["user_id_str"],
                        "username": tweet["username"],
                        "profile_image_url": tweet.get("profile_image_url"),  # NEW: Profile image URL of the tweet author
                        "time_posted": tweet["created_at"],
                        "created_at": datetime.utcnow(),

                        # Pre-drafted reply (NEW!)
                        "draft_reply": draft_reply,
                        "reply_status": "PENDING",
                        "posted_reply_id": None,
                        
                        # Pre-drafted repurposed content (NEW!)
                        "draft_post": draft_post,
                        "post_status": "PENDING",
                        "posted_post_id": None,
                        "repurposedAt": None,
                        "updatedAt": None,
                        "status": "NOT DONE",
                        "repurposed": "NOT DONE"
                    }
                    
                    # Save to database
                    await db.scraped_tweets.update_one(
                        {"conversation_id_str": tweet_doc["conversation_id_str"]},
                        {"$set": tweet_doc},
                        upsert=True,
                    )
                    saved_count += 1
                    print(f"[SUCCESS] Saved tweet with reply + repurpose: {tweet['text'][:80]}... | Reply: {draft_reply[:40]}... | Repurpose: {draft_post[:40]}...")
                
                print(f"[SUCCESS] Saved {saved_count} selected tweets with replies and repurposed content for keyword: {keyword}")
                results.append({"keyword": keyword, "status": "success", "count": saved_count, "total_candidates": len(tweets)})

    return {
        "message": "Enhanced tweet scraping with triple combo (selection + reply drafting + repurposing) completed",
        "results": results,
        "total_processed": len(results)
    }  

@app.post("/scrape_user_tweets")
async def scrape_user_tweets(user_id: str | None = Cookie(None)):
    """
    Scrape tweets for each tracked account with combined selection and reply drafting.
    """
    if not RAPIDAPI_KEY:
        raise HTTPException(500, "RAPIDAPI_KEY environment variable missing")
    
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(500, "Gemini client not initialized")

    user_filter = {"_id": ObjectId(user_id)} if user_id else {}
    cursor = db.users.find(user_filter)

    results = []
    sem = asyncio.Semaphore(2)  # limit concurrency to 2

    async with httpx.AsyncClient() as http_client:
        async for user in cursor:
            uid = user["_id"]

            # Get user persona for LLM filtering
            user_persona = user.get("user_persona", "")
            print(f"[INFO] User has persona: {'Yes' if user_persona else 'No'}")

            tracked_accounts_cursor = db.tracked_accounts.find({"user": uid})
            tracked_accounts = []
            async for acc in tracked_accounts_cursor:
                tracked_accounts.append(acc)

            print(f"[INFO] User {uid} has {len(tracked_accounts)} tracked accounts.")

            for acc in tracked_accounts:
                rest_id = acc.get("rest_id")
                username = acc.get("username")

                if not rest_id:
                    print(f"[WARN] Skipping {username}: No rest_id")
                    continue

                async def fetch_and_save(current_uid, current_rest_id, current_username, current_persona):
                    async with sem:
                        await asyncio.sleep(1)  # avoid rate limit

                        print(f"[INFO] Fetching tweets for: {current_username}")
                        url = f"https://twitter-aio.p.rapidapi.com/user/{current_rest_id}/tweets"
                        headers = {
                            "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
                            "x-rapidapi-key": RAPIDAPI_KEY,
                            "accept": "application/json",
                        }
                        params = {
                            "count": 20,
                            "filters": '{"includeRetweets":false,"removeReplies":true,"removePostsWithLinks":true}'
                        }

                        try:
                            r = await http_client.get(url, headers=headers, params=params, timeout=20)
                            r.raise_for_status()
                        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                            print(f"[ERROR] {current_username}: {exc}")
                            return {"username": current_username, "status": "failed"}

                        data = r.json()
                        instructions = (
                            data.get("user", {})
                                .get("result", {})
                                .get("timeline", {})
                                .get("timeline", {})
                                .get("instructions", [])
                        )

                        entries = []
                        for inst in instructions:
                            entries.extend(inst.get("entries", []))

                        tweets = []
                        for entry in entries:
                            tweet = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result")
                            legacy = tweet.get("legacy") if tweet else None
                            if not legacy:
                                continue

                            note_text = (
                                tweet.get("note_tweet", {})
                                    .get("note_tweet_results", {})
                                    .get("result", {})
                                    .get("text")
                            )
                            text = note_text or legacy.get("full_text")
                            
                            if not text:  # Only skip if absolutely no text
                                continue

                            tweets.append({
                                "text": text,
                                "created_at": legacy.get("created_at"),
                                "conversation_id_str": legacy.get("conversation_id_str"),
                                "user_id_str": legacy.get("user_id_str"),
                                "username": current_username
                            })

                        if not tweets:
                            print(f"[WARN] No candidate tweets found for {current_username}")
                            return {"username": current_username, "status": "no_tweets"}

                        print(f"[INFO] Found {len(tweets)} candidate tweets for {current_username}")

                        # NEW: Behavioral Intelligence for User Tweets - selection + reply drafting
                        selected_tweets = await select_and_draft_user_tweet_replies(tweets, current_persona, current_username, str(current_uid))
                        print(f"[INFO] Selected {len(selected_tweets)} tweets with user tweet behavioral intelligence for {current_username}")
                        
                        # If no behavioral intelligence available, fallback is handled inside the function

                        # Save selected tweets with draft replies
                        saved = 0
                        for selection in selected_tweets:
                            tweet = selection['tweet']
                            draft_reply = selection['draft_reply']

                            doc = {
                                "user": current_uid,
                                "username": tweet["username"],
                                "tweet_id": tweet["conversation_id_str"],
                                "text": tweet["text"],
                                "created_at": tweet["created_at"],
                                "draft_reply": draft_reply,  # Pre-drafted reply using usertweet behavioral intelligence
                                "reply_status": "PENDING",
                                "posted_reply_id": None,
                                "profile_image_url": acc.get("profile_image_url"),  # NEW: Profile image URL from tracked account
                                "createdAt": datetime.utcnow()
                            }
                            await db.tracked_user_tweets.update_one(
                                {"user": current_uid, "tweet_id": doc["tweet_id"]},
                                {"$set": doc},
                                upsert=True
                            )
                            saved += 1
                            print(f"[SUCCESS] Saved tweet with reply for {current_username}: {tweet['text'][:80]}... | Reply: {draft_reply[:40]}...")

                        print(f"[SUCCESS] Saved {saved} selected tweets with replies for {current_username}")
                        return {"username": current_username, "saved": saved, "total_candidates": len(tweets)}

                res = await fetch_and_save(uid, rest_id, username, user_persona)
                results.append(res)

    return {
        "message": "Tracked user tweets scraping with behavioral intelligence (selection + reply drafting) completed",
        "results": results,
        "total_processed": len(results)
    }



@app.post("/draft_replies")
async def draft_replies(user_id: str | None = Cookie(None)):
    """
    DEPRECATED: This endpoint is now largely unnecessary since /scrape_user_tweets 
    handles both selection and reply drafting in a single optimized call.
    Keep for backwards compatibility.
    """
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing.")
    
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(500, "Gemini client not initialized - check GEMINI_API_KEY")

    # Get user's persona for style context
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    user_persona = user.get("user_persona", "")

    cursor = db.tracked_user_tweets.find({
        "user": ObjectId(user_id),
        "reply_status": "PENDING",
        "draft_reply": None
    })

    drafted = []

    async for tweet in cursor:
        tweet_text = tweet.get("text", "")
        if not tweet_text:
            continue

        # Create persona-based context
        if user_persona:
            prompt = f"""You are drafting a reply based on this comprehensive user persona:

USER PERSONA:
{user_persona}

TWEET TO REPLY TO:
{tweet_text}

Create a reply that authentically matches this user by considering:

1. **EXPERTISE**: Use their knowledge areas and technical level
2. **WRITING STYLE**: Match their tone, sentence structure, and vocabulary
3. **COMMUNICATION PATTERNS**: Follow their typical reply style and approach
4. **PERSONALITY**: Reflect their confidence level, helpfulness, and enthusiasm
5. **VALUE PROPOSITION**: Provide the unique value they typically offer

Requirements:
- Stay within their expertise boundaries
- Use their typical communication style
- Match their level of technical detail
- Reflect their personality traits
- ABSOLUTELY NO emojis or emoji characters
- Keep it under 20 words
- Sound authentic to their voice"""
        else:
            # Fallback if no persona
            prompt = (
                f"Create a reply to this tweet:\n\n{tweet_text}\n\n"
                "Keep it under 20 words, be engaging and authentic. ABSOLUTELY NO emojis or emoji characters."
            )

        response = gemini_client.generate_content(prompt)
        ai_reply = response.text.strip()

        # --- Save draft reply in DB ---
        await db.tracked_user_tweets.update_one(
            {"_id": tweet["_id"]},
            {
                "$set": {
                    "draft_reply": ai_reply,
                    "reply_status": "PENDING",
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        drafted.append({
            "tweet_id": tweet["tweet_id"],
            "draft_reply": ai_reply
        })

    return {
        "message": f"Drafted {len(drafted)} personalized replies",
        "drafts": drafted
    }

@app.get("/fetch_pending_replies")
async def fetch_pending_replies(user_id: str | None = Cookie(None)):
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing.")
    
    cursor = db.tracked_user_tweets.find({
        "user": ObjectId(user_id),
        "reply_status": "PENDING",
        "draft_reply": { "$ne": None }
    })

    pending = []
    async for tweet in cursor:
        pending.append({
            "tweet_id": tweet["tweet_id"],
            "text": tweet["text"],
            "draft_reply": tweet["draft_reply"],
            "username": tweet["username"],
            "profile_image_url": tweet.get("profile_image_url"),  # NEW: Profile image URL of the tweet author
            "created_at": tweet["created_at"]
        })

    return {
        "message": f"Found {len(pending)} pending replies",
        "pending_replies": pending
    } 

# -----------------------------------------------------------
#  CONFIRM / CANCEL / EDIT a drafted reply
# -----------------------------------------------------------

# ── helper: really post a reply to X/Twitter ────────────────────────────
async def post_reply_twitter_oauth1(   
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
    reply_to_tweet_id: str,
    text: str,
) -> str:
    """Post reply using Tweepy - much more reliable than manual OAuth"""
    
    def make_tweet():
        """
        Post a reply using Twitter API **v2** (works on Basic access).
        Returns the new tweet ID as a string.
        """
        try:
            # Import tweepy only when needed for memory optimization
            import tweepy
            
            # 1️⃣  Build the Tweepy v2 Client with OAuth-1.0a creds
            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )

            # 2️⃣  Create the reply tweet
            response = client.create_tweet(
                text=text,                       # body of the reply
                in_reply_to_tweet_id=reply_to_tweet_id,   # parent tweet
            )

            # 3️⃣  Extract and return the tweet ID
            posted_id = response.data["id"]
            print(f"[SUCCESS] Tweet posted with ID: {posted_id}")
            return str(posted_id)

        except Exception as e:
            print(f"[ERROR] Tweepy v2 error: {e}")
            raise RuntimeError(f"Twitter posting failed: {e}")
    
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, make_tweet)


# ── body model for the endpoint ─────────────────────────────────────────
class HandleReplyModel(BaseModel):
    tweet_id: str
    action:   str                 # confirm | cancel | edit
    edited_text: Optional[str] = None


# ── the single /handle_reply_action endpoint ────────────────────────────
@app.post("/handle_reply_action")
async def handle_reply_action(
    data: HandleReplyModel = Body(...),
    user_id: str | None = Cookie(None),
):
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")

    # 1 fetch the pending draft
    tweet_doc = await db.tracked_user_tweets.find_one(
        {"user": ObjectId(user_id), 
         "tweet_id": data.tweet_id,
         "reply_status": "PENDING"}
    )
    if not tweet_doc:
        raise HTTPException(404, "No pending draft for this tweet_id")

    action = data.action.lower()
    if action == "confirm":
        post_text = tweet_doc.get("draft_reply")
        if not post_text:
            raise HTTPException(400, "Draft reply missing – cannot confirm")

    elif action == "edit":
        if not data.edited_text or not data.edited_text.strip():
            raise HTTPException(400, "edited_text required for action = edit")
        post_text = data.edited_text.strip()

    elif action == "cancel":
        await db.tracked_user_tweets.update_one(
            {"_id": tweet_doc["_id"]},
            {"$set": {"reply_status": "CANCELLED",
                      "updatedAt": datetime.utcnow()}}
        )
        
        # Feed cancellation behavior to mem0
        mem = get_memory_client()
        if mem:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            user_name = user.get("name", "Unknown") if user else "Unknown"
            context = f"User rejected AI reply to @{tweet_doc['username']}. Original tweet: '{tweet_doc['text'][:100]}...' AI suggestion: '{tweet_doc['draft_reply']}'"
            
            print(f"[MEM0 INSERT] USER TWEET REPLY CANCEL - About to insert into mem0:")
            print(f"[MEM0 INSERT] User ID: {user_id}")
            print(f"[MEM0 INSERT] Context String: {context}")
            
            try:
                mem.add(context, user_id=user_id)
                print(f"[MEM0 SUCCESS] USER TWEET REPLY CANCEL - Successfully inserted behavioral data into mem0")
            except Exception as e:
                print(f"[MEM0 ERROR] USER TWEET REPLY CANCEL - Failed to insert into mem0: {e}")
        else:
            print(f"[MEM0 SKIP] USER TWEET REPLY CANCEL - mem0 not available, skipping behavioral tracking")
        
        return {"message": "Draft reply cancelled"}

    else:
        raise HTTPException(400, "action must be confirm, cancel or edit")

    # 2 GET ALL FOUR OAUTH-1 KEYS FROM USER DOC ────────────────────────────
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    # pull all four OAuth-1 keys from the user doc
    api_key             = user.get("twitter_client_id")
    api_secret          = user.get("twitter_client_secret")
    access_token        = user.get("twitter_access_token")
    access_token_secret = user.get("twitter_access_token_secret")

    missing = [k for k, v in {
        "twitter_client_id": api_key,
        "twitter_client_secret": api_secret,
        "access_token": access_token,
        "access_token_secret": access_token_secret}.items() if not v]
    if missing:
        raise HTTPException(400, f"Missing Twitter credentials: {', '.join(missing)}")

    # 3 POST THE REPLY USING OAUTH-1.0A ────────────────────────────────────
    posted_id = await post_reply_twitter_oauth1(
        api_key, api_secret,
        access_token, access_token_secret,
        reply_to_tweet_id=data.tweet_id,
        text=post_text,
    )

    # Feed successful behavior to mem0
    mem = get_memory_client()
    if mem:
        user_name = user.get("name", "Unknown") if user else "Unknown"
        if action == "confirm":
            context = f"User posted AI reply to @{tweet_doc['username']} without changes. Original tweet: '{tweet_doc['text'][:100]}...' AI suggestion: '{post_text}'"
        elif action == "edit":
            context = f"User edited AI reply to @{tweet_doc['username']} before posting. Original tweet: '{tweet_doc['text'][:100]}...' AI suggestion: '{tweet_doc['draft_reply']}' User changed to: '{post_text}'"
        
        print(f"[MEM0 INSERT] USER TWEET REPLY {action.upper()} - About to insert into mem0:")
        print(f"[MEM0 INSERT] User ID: {user_id}")
        print(f"[MEM0 INSERT] Context String: {context}")
        
        try:
            mem.add(context, user_id=user_id)
            print(f"[MEM0 SUCCESS] USER TWEET REPLY {action.upper()} - Successfully inserted behavioral data into mem0")
        except Exception as e:
            print(f"[MEM0 ERROR] USER TWEET REPLY {action.upper()} - Failed to insert into mem0: {e}")
    else:
        print(f"[MEM0 SKIP] USER TWEET REPLY {action.upper()} - mem0 not available, skipping behavioral tracking")

    # 4 mark as POSTED
    await db.tracked_user_tweets.update_one(
        {"_id": tweet_doc["_id"]},
        {"$set": {
            "reply_status":    "POSTED",
            "posted_reply_id": posted_id,
            "draft_reply":     post_text,
            "updatedAt":       datetime.utcnow(),
        }}
    )

    # 5 ADD TO UNIFIED TWEET TRACKER
    tracker_doc = {
        "user": ObjectId(user_id),
        "tweet_id": posted_id,
        "tweet_type": "reply",
        "source_type": "user_tweet",
        "posted_at": datetime.utcnow(),
        "original_text": post_text,
        "source_context": f"@{tweet_doc['username']}",
        "engagement_context": None,
        "created_at": datetime.utcnow()
    }
    await db.posted_tweet_tracker.insert_one(tracker_doc)
    print(f"[SUCCESS] Added user tweet reply to tracker: {posted_id}")

    return {
        "message": "Reply posted successfully"
                  if action == "confirm"
                  else "Reply edited & posted successfully",
        "posted_reply_id": posted_id,
    }


@app.post("/test_twitter_credentials")
async def test_twitter_credentials(user_id: str | None = Cookie(None)):
    """
    Test Twitter OAuth credentials without posting anything.
    Uses the verify_credentials endpoint to validate authentication.
    """
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")

    # Get user credentials
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    # Get all four OAuth-1 keys from the user doc
    api_key             = user.get("twitter_client_id")
    api_secret          = user.get("twitter_client_secret")
    access_token        = user.get("twitter_access_token")
    access_token_secret = user.get("twitter_access_token_secret")

    missing = [k for k, v in {
        "twitter_client_id": api_key,
        "twitter_client_secret": api_secret,
        "access_token": access_token,
        "access_token_secret": access_token_secret}.items() if not v]
    if missing:
        raise HTTPException(400, f"Missing Twitter credentials: {', '.join(missing)}")

    # Test credentials using verify_credentials endpoint
    import asyncio
    
    def test_credentials():
        try:
            # Import OAuth1Session only when needed for memory optimization
            from requests_oauthlib import OAuth1Session
            
            # Create OAuth1Session with Twitter credentials
            oauth = OAuth1Session(
                client_key=api_key,
                client_secret=api_secret,
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret
            )
            
            url = "https://api.twitter.com/1.1/account/verify_credentials.json"
            
            print(f"[DEBUG] Testing credentials...")
            print(f"[DEBUG] Using API key: {api_key[:10]}...")
            print(f"[DEBUG] Access token format: {access_token[:15]}...")
            print(f"[DEBUG] Making request to: {url}")
            
            response = oauth.get(url, timeout=15)
            
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                print(f"[ERROR] 401 Unauthorized - Full response body: {response.text}")
                return {"success": False, "error": f"OAuth failed: {response.text}"}
            
            response.raise_for_status()
            user_data = response.json()
            
            return {
                "success": True, 
                "username": user_data.get("screen_name"),
                "user_id": user_data.get("id_str"),
                "name": user_data.get("name")
            }
            
        except Exception as e:
            print(f"[ERROR] Credential test failed: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"[ERROR] Response body: {e.response.text}")
            return {"success": False, "error": str(e)}
    
    # Execute in thread pool to maintain async compatibility
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, test_credentials)
    
    return result

# ---------------------------------------------------------------------------
# ⚡️ TOP-TWEET REPLY WORKFLOW  (copy–paste this entire block into app.py)
# ---------------------------------------------------------------------------

# 0️⃣  make sure every new "top tweet" already has the workflow fields
#     → extend the tweet_doc in /scrape_top_tweets exactly like shown earlier.

# 1️⃣  Draft replies with GPT
@app.post("/draft_replies_toptweets") 
async def draft_replies_toptweets(user_id: str | None = Cookie(None)):
    """
    DEPRECATED: This endpoint is now largely unnecessary since /scrape_top_tweets 
    handles both selection and reply drafting in a single optimized call.
    Keep for backwards compatibility.
    """
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")
    
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(500, "Gemini not initialised")

    # Get user's persona for style context
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    user_persona = user.get("user_persona", "")

    cursor = db.scraped_tweets.find({
        "user": ObjectId(user_id),
        "reply_status": "PENDING",
        "draft_reply": None
    })

    drafted = []
    async for tw in cursor:
        # Create persona-based context
        if user_persona:
            prompt = f"""You are drafting a reply based on this comprehensive user persona:

USER PERSONA:
{user_persona}

TWEET TO REPLY TO:
{tw['text']}

Create a reply that authentically matches this user by considering:

1. **EXPERTISE**: Use their knowledge areas and technical level
2. **WRITING STYLE**: Match their tone, sentence structure, and vocabulary
3. **COMMUNICATION PATTERNS**: Follow their typical reply style and approach
4. **PERSONALITY**: Reflect their confidence level, helpfulness, and enthusiasm
5. **VALUE PROPOSITION**: Provide the unique value they typically offer

Requirements:
- Stay within their expertise boundaries
- Use their typical communication style
- Match their level of technical detail
- Reflect their personality traits
- ABSOLUTELY NO emojis or emoji characters
- Keep it under 20 words
- Sound authentic to their voice"""
        else:
            # Fallback if no persona
            prompt = (
                f"Create a reply to this tweet:\n\n{tw['text']}\n\n"
                "Keep it under 20 words, be engaging and authentic. ABSOLUTELY NO emojis or emoji characters."
            )

        ai = gemini_client.generate_content(prompt)
        reply_text = ai.text.strip()

        await db.scraped_tweets.update_one(
            {"_id": tw["_id"]},
            {"$set": {"draft_reply": reply_text,
                      "reply_status": "PENDING",
                      "updatedAt": datetime.utcnow()}}
        )
        drafted.append({"tweet_id": tw["conversation_id_str"], "draft_reply": reply_text})

    return {"message": f"Drafted {len(drafted)} personalized top-tweet replies", "drafts": drafted}


# 2️⃣  Fetch pending drafts so you can confirm / edit / cancel
@app.get("/fetch_pending_replies_toptweets")
async def fetch_pending_replies_toptweets(user_id: str | None = Cookie(None)):
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")

    cursor = db.scraped_tweets.find({
        "user": ObjectId(user_id),
        "reply_status": "PENDING",
        "draft_reply": {"$ne": None}
    })

    pending = []
    async for tw in cursor:
        pending.append({
            "tweet_id": tw["conversation_id_str"],
            "text": tw["text"],
            "draft_reply": tw["draft_reply"],
            "username": tw["username"],
            "profile_image_url": tw.get("profile_image_url"),  # NEW: Profile image URL of the tweet author
            "created_at": tw["created_at"],
            "keyword": tw["keyword"]
        })

    return {"message": f"Found {len(pending)} pending top-tweet replies",
            "pending_replies": pending}


# 3️⃣  Confirm / edit / cancel a draft and post it to X
class HandleReplyTopTweetsModel(BaseModel):
    tweet_id: str
    action: str                     # confirm | cancel | edit
    edited_text: Optional[str] = None

@app.post("/handle_reply_action_toptweets") 
async def handle_reply_action_toptweets(
    data: HandleReplyTopTweetsModel = Body(...),
    user_id: str | None = Cookie(None),
):
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")

    tw = await db.scraped_tweets.find_one({
        "user": ObjectId(user_id),
        "conversation_id_str": data.tweet_id,
        "reply_status": "PENDING"
    })
    if not tw:
        raise HTTPException(404, "No pending draft for this tweet_id")

    act = data.action.lower()
    if act == "confirm":
        post_text = tw["draft_reply"] or ""
    elif act == "edit":
        if not data.edited_text or not data.edited_text.strip():
            raise HTTPException(400, "edited_text required for edit")
        post_text = data.edited_text.strip()
    elif act == "cancel":
        await db.scraped_tweets.update_one(
            {"_id": tw["_id"]},
            {"$set": {"reply_status": "CANCELLED", "updatedAt": datetime.utcnow()}}
        )
        
        # Feed cancellation behavior to mem0
        mem = get_memory_client()
        if mem:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            user_name = user.get("name", "Unknown") if user else "Unknown"
            context = f"User rejected AI reply about '{tw['keyword']}'. Original tweet: '{tw['text'][:100]}...' AI suggestion: '{tw['draft_reply']}'"
            
            print(f"[MEM0 INSERT] TOP TWEET REPLY CANCEL - About to insert into mem0:")
            print(f"[MEM0 INSERT] User ID: {user_id}")
            print(f"[MEM0 INSERT] Context String: {context}")
            
            try:
                mem.add(context, user_id=user_id)
                print(f"[MEM0 SUCCESS] TOP TWEET REPLY CANCEL - Successfully inserted behavioral data into mem0")
            except Exception as e:
                print(f"[MEM0 ERROR] TOP TWEET REPLY CANCEL - Failed to insert into mem0: {e}")
        else:
            print(f"[MEM0 SKIP] TOP TWEET REPLY CANCEL - mem0 not available, skipping behavioral tracking")
        
        return {"message": "Draft reply cancelled"}
    else:
        raise HTTPException(400, "action must be confirm, cancel or edit")

    # pull OAuth keys
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    keys = (
        user.get("twitter_client_id"),
        user.get("twitter_client_secret"),
        user.get("twitter_access_token"),
        user.get("twitter_access_token_secret"),
    )
    if not all(keys):
        raise HTTPException(400, "Missing Twitter credentials")

    # post reply
    posted_id = await post_reply_twitter_oauth1(
        *keys, reply_to_tweet_id=data.tweet_id, text=post_text
    )

    # Feed successful behavior to mem0
    mem = get_memory_client()
    if mem:
        user_name = user.get("name", "Unknown") if user else "Unknown"
        if act == "confirm":
            context = f"User posted AI reply about '{tw['keyword']}' without changes. Original tweet: '{tw['text'][:100]}...' AI suggestion: '{post_text}'"
        elif act == "edit":
            context = f"User edited AI reply about '{tw['keyword']}' before posting. Original tweet: '{tw['text'][:100]}...' AI suggestion: '{tw['draft_reply']}' User changed to: '{post_text}'"
        
        print(f"[MEM0 INSERT] TOP TWEET REPLY {act.upper()} - About to insert into mem0:")
        print(f"[MEM0 INSERT] User ID: {user_id}")
        print(f"[MEM0 INSERT] Context String: {context}")
        
        try:
            mem.add(context, user_id=user_id)
            print(f"[MEM0 SUCCESS] TOP TWEET REPLY {act.upper()} - Successfully inserted behavioral data into mem0")
        except Exception as e:
            print(f"[MEM0 ERROR] TOP TWEET REPLY {act.upper()} - Failed to insert into mem0: {e}")
    else:
        print(f"[MEM0 SKIP] TOP TWEET REPLY {act.upper()} - mem0 not available, skipping behavioral tracking")

    # mark as posted
    await db.scraped_tweets.update_one(
        {"_id": tw["_id"]},
        {"$set": {"reply_status": "POSTED",
                  "posted_reply_id": posted_id,
                  "draft_reply": post_text,
                  "updatedAt": datetime.utcnow()}}
    )

    # ADD TO UNIFIED TWEET TRACKER
    tracker_doc = {
        "user": ObjectId(user_id),
        "tweet_id": posted_id,
        "tweet_type": "reply",
        "source_type": "top_tweet",
        "posted_at": datetime.utcnow(),
        "original_text": post_text,
        "source_context": tw['keyword'],
        "engagement_context": None,
        "created_at": datetime.utcnow()
    }
    await db.posted_tweet_tracker.insert_one(tracker_doc)
    print(f"[SUCCESS] Added top tweet reply to tracker: {posted_id}")

    return {"message": "Reply posted successfully" if act == "confirm"
                       else "Reply edited & posted successfully",
            "posted_reply_id": posted_id}


# ---------------------------------------------------------------------------
#  TOP-TWEET REPURPOSING WORKFLOW  ➜  paste this whole block into app.py
#  (place it anywhere; helper and "post" endpoint are intentionally last)
# ---------------------------------------------------------------------------

# 1️⃣  ───  Gemini 2.0 drafts a rewritten tweet  ───────────────────────────────────
@app.post("/draft_repurposed_tweets")
async def draft_repurposed_tweets(user_id: str | None = Cookie(None)):
    """
    DEPRECATED: This endpoint is now largely unnecessary since /scrape_top_tweets 
    handles selection, reply drafting, AND repurposing in a single optimized call.
    Keep for backwards compatibility.
    """
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")
    
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(500, "Gemini not initialised")

    # Get user's persona for style context
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    user_persona = user.get("user_persona", "")

    cursor = db.scraped_tweets.find({
        "user": ObjectId(user_id),
        "post_status": "PENDING",
        "draft_post": None
    })

    drafted = []
    skipped = []
    
    async for tw in cursor:
        tweet_text = tw['text']
        
        # Filter out promotional/networking content
        skip_indicators = [
            # Crypto/promotional
            "$", "🚀", "🔍", "🌐", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
            "looking to connect", "let's connect", "DM me", 
            # Networking posts
            "fellow devs", "What are you building", "share feedback"
        ]
        
        # Check if tweet should be skipped
        should_skip = any(indicator.lower() in tweet_text.lower() for indicator in skip_indicators)
        
        # Also skip if tweet has more than 3 emojis (indicates promotional content)
        emoji_count = sum(1 for char in tweet_text if ord(char) > 127 and ord(char) != 8217)  # Count non-ASCII chars except apostrophe
        if emoji_count > 3:
            should_skip = True
            
        if should_skip:
            skipped.append({
                "tweet_id": tw["conversation_id_str"],
                "reason": "promotional/networking content",
                "text": tweet_text[:100] + "..."
            })
            print(f"[SKIP] Promotional content: {tweet_text[:100]}...")
            continue

        # Create personalized repurposing prompt using persona
        if user_persona:
            prompt = f"""You are repurposing content based on this comprehensive user persona:

USER PERSONA:
{user_persona}

ORIGINAL TWEET:
{tweet_text}

Rewrite this tweet to authentically match this user by considering:

1. **EXPERTISE**: Adjust technical level to match their knowledge areas
2. **WRITING STYLE**: Use their tone, vocabulary, and sentence structure
3. **CONTENT PREFERENCES**: Frame it according to their preferred topics and depth
4. **PERSONALITY**: Reflect their confidence, perspective, and communication style
5. **VALUE PROPOSITION**: Ensure it provides the unique value they typically offer
6. **CONTENT GENERATION GUIDELINES**: Follow their typical tweet length and style

Requirements:
- Stay within their expertise boundaries
- Use their authentic voice and perspective
- Match their typical content depth and approach
- Reflect their personality and communication patterns
- Keep it under 25 words
- No hashtags
- ABSOLUTELY NO emojis
- Make it sound like something they would naturally write"""
        else:
            # Fallback if no persona
            prompt = f"""Rewrite the following tweet in your own voice:

{tweet_text}

Keep it under 25 words, no hashtags, ABSOLUTELY NO emojis, be authentic and engaging."""

        ai = gemini_client.generate_content(prompt)
        rewrite = ai.text.strip()

        await db.scraped_tweets.update_one(
            {"_id": tw["_id"]},
            {"$set": {
                "draft_post": rewrite,
                "post_status": "PENDING",
                "updatedAt": datetime.utcnow()
            }}
        )
        drafted.append({
            "tweet_id": tw["conversation_id_str"],
            "draft_post": rewrite,
            "original_text": tweet_text[:100] + "..."
        })
        print(f"[SUCCESS] Drafted personalized repurpose: {rewrite}")

    return {
        "message": f"Drafted {len(drafted)} personalized repurposed tweets",
        "drafts": drafted,
        "skipped": len(skipped),
        "skipped_details": skipped
    }


# 2️⃣  ───  Fetch all pending rewritten drafts  ────────────────────────────
@app.get("/fetch_pending_repurposed_tweets")
async def fetch_pending_repurposed_tweets(user_id: str | None = Cookie(None)):
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")

    cursor = db.scraped_tweets.find({
        "user": ObjectId(user_id),
        "post_status": "PENDING",
        "draft_post": {"$ne": None}
    })

    pending = []
    async for tw in cursor:
        pending.append({
            "tweet_id": tw["conversation_id_str"],
            "original_text": tw["text"],
            "draft_post": tw["draft_post"],
            "username": tw["username"],
            "profile_image_url": tw.get("profile_image_url"),  # NEW: Profile image URL of the tweet author
            "keyword": tw["keyword"],
            "created_at": tw["created_at"]
        })

    return {
        "message": f"Found {len(pending)} repurposed drafts",
        "pending_repurposed": pending
    }


# 3️⃣  ───  Confirm / edit / cancel ➜ post the rewrite  ────────────────────
class HandleRepurposeModel(BaseModel):
    tweet_id: str
    action: str                       # confirm | cancel | edit
    edited_text: Optional[str] = None

@app.post("/handle_repurpose_action_toptweets")
async def handle_repurpose_action_toptweets(
    data: HandleRepurposeModel = Body(...),
    user_id: str | None = Cookie(None),
):
    if not user_id:
        raise HTTPException(401, "user_id cookie missing")

    tw = await db.scraped_tweets.find_one({
        "user": ObjectId(user_id),
        "conversation_id_str": data.tweet_id,
        "post_status": "PENDING"
    })
    if not tw:
        raise HTTPException(404, "No pending repurposed draft for this tweet_id")

    act = data.action.lower()
    if act == "confirm":
        post_text = tw["draft_post"] or ""
        if not post_text:
            raise HTTPException(400, "draft_post missing – cannot confirm")
    elif act == "edit":
        if not data.edited_text or not data.edited_text.strip():
            raise HTTPException(400, "edited_text required for edit")
        post_text = data.edited_text.strip()
    elif act == "cancel":
        await db.scraped_tweets.update_one(
            {"_id": tw["_id"]},
            {"$set": {"post_status": "CANCELLED",
                      "repurposedAt": datetime.utcnow(),
                      "updatedAt": datetime.utcnow()}}
        )
        
        # Feed cancellation behavior to mem0
        mem = get_memory_client()
        if mem:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            user_name = user.get("name", "Unknown") if user else "Unknown"
            context = f"User rejected AI repurposed content about '{tw['keyword']}'. Original tweet: '{tw['text'][:100]}...' AI repurposed: '{tw['draft_post']}'"
            
            print(f"[MEM0 INSERT] TOP TWEET REPURPOSE CANCEL - About to insert into mem0:")
            print(f"[MEM0 INSERT] User ID: {user_id}")
            print(f"[MEM0 INSERT] Context String: {context}")
            
            try:
                mem.add(context, user_id=user_id)
                print(f"[MEM0 SUCCESS] TOP TWEET REPURPOSE CANCEL - Successfully inserted behavioral data into mem0")
            except Exception as e:
                print(f"[MEM0 ERROR] TOP TWEET REPURPOSE CANCEL - Failed to insert into mem0: {e}")
        else:
            print(f"[MEM0 SKIP] TOP TWEET REPURPOSE CANCEL - mem0 not available, skipping behavioral tracking")
        
        return {"message": "Repurposed draft cancelled"}
    else:
        raise HTTPException(400, "action must be confirm, cancel or edit")

    # pull OAuth keys
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    keys = (
        user.get("twitter_client_id"),
        user.get("twitter_client_secret"),
        user.get("twitter_access_token"),
        user.get("twitter_access_token_secret"),
    )
    if not all(keys):
        raise HTTPException(400, "Missing Twitter credentials")

    # post the new tweet
    posted_id = await post_original_tweet_oauth1(*keys, text=post_text)

    # Feed successful behavior to mem0
    mem = get_memory_client()
    if mem:
        user_name = user.get("name", "Unknown") if user else "Unknown"
        if act == "confirm":
            context = f"User posted AI repurposed content about '{tw['keyword']}' without changes. Original tweet: '{tw['text'][:100]}...' AI repurposed: '{post_text}'"
        elif act == "edit":
            context = f"User edited AI repurposed content about '{tw['keyword']}' before posting. Original tweet: '{tw['text'][:100]}...' AI repurposed: '{tw['draft_post']}' User changed to: '{post_text}'"
        
        print(f"[MEM0 INSERT] TOP TWEET REPURPOSE {act.upper()} - About to insert into mem0:")
        print(f"[MEM0 INSERT] User ID: {user_id}")
        print(f"[MEM0 INSERT] Context String: {context}")
        
        try:
            mem.add(context, user_id=user_id)
            print(f"[MEM0 SUCCESS] TOP TWEET REPURPOSE {act.upper()} - Successfully inserted behavioral data into mem0")
        except Exception as e:
            print(f"[MEM0 ERROR] TOP TWEET REPURPOSE {act.upper()} - Failed to insert into mem0: {e}")
    else:
        print(f"[MEM0 SKIP] TOP TWEET REPURPOSE {act.upper()} - mem0 not available, skipping behavioral tracking")

    # mark as posted
    await db.scraped_tweets.update_one(
        {"_id": tw["_id"]},
        {"$set": {
            "post_status": "POSTED",
            "posted_post_id": posted_id,
            "draft_post": post_text,
            "repurposedAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "repurposed": "DONE"
        }}
    )

    # ADD TO UNIFIED TWEET TRACKER
    tracker_doc = {
        "user": ObjectId(user_id),
        "tweet_id": posted_id,
        "tweet_type": "repurpose",
        "source_type": "top_tweet",
        "posted_at": datetime.utcnow(),
        "original_text": post_text,
        "source_context": tw['keyword'],
        "engagement_context": None,
        "created_at": datetime.utcnow()
    }
    await db.posted_tweet_tracker.insert_one(tracker_doc)
    print(f"[SUCCESS] Added top tweet repurpose to tracker: {posted_id}")

    return {"message": "Repurposed tweet posted successfully",
            "posted_post_id": posted_id}


# 4️⃣  ───  Helper (kept last) — post a stand-alone tweet  ────────────────
async def post_original_tweet_oauth1(
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
    text: str,
) -> str:
    """Create a brand-new tweet and return its ID."""
    def make_tweet():
        try:
            # Import tweepy only when needed for memory optimization
            import tweepy
            
            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            response = client.create_tweet(text=text)
            posted_id = response.data["id"]
            print(f"[SUCCESS] Posted new tweet {posted_id}")
            return str(posted_id)
        except Exception as e:
            print(f"[ERROR] Tweepy v2 error: {e}")
            raise RuntimeError(f"Posting failed: {e}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, make_tweet)


# -----------------------------------------------------------
# SIMPLE BEHAVIORAL INTELLIGENCE FUNCTION
# -----------------------------------------------------------

async def get_behavioral_intelligence(user_id: str, limit: int = 200) -> str:
    """
    Get all behavioral intelligence using get_all() to retrieve all user memories.
    This avoids the empty string search that causes LLM processing failures.
    """
    mem = get_memory_client()
    if not mem:
        return ""
    
    try:
        # Use get_all() instead of search("") to avoid LLM processing failures
        results = mem.get_all(user_id=user_id)
        
        # Extract behavioral data
        if isinstance(results, dict) and 'results' in results:
            behavioral_data = results['results']
        elif isinstance(results, list):
            behavioral_data = results
        else:
            return ""
        
        # Limit results if needed
        if len(behavioral_data) > limit:
            behavioral_data = behavioral_data[:limit]
        
        # Format into readable string
        formatted_behavior = ""
        for item in behavioral_data:
            formatted_behavior += f"- {item.get('text', '')}\n"
        
        return formatted_behavior
    except Exception as e:
        print(f"[ERROR] Behavioral intelligence query failed: {e}")
        return ""


# -----------------------------------------------------------
# TWEET STATISTICS FETCHING
# -----------------------------------------------------------

@app.post("/fetch_tweet_statistics")
async def fetch_tweet_statistics(user_id: str | None = Cookie(None)):
    """
    Fetch statistics for the user's last 50 posted tweets using RapidAPI.
    """
    if not user_id:
        raise HTTPException(401, "Unauthorized: user_id cookie missing")
    
    if not RAPIDAPI_KEY:
        raise HTTPException(500, "RAPIDAPI_KEY environment variable missing")
    
    print(f"[INFO] Starting statistics fetch for user {user_id}")
    
    # Step 1: Get user's Twitter profile to extract rest_id
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    twitter_username = user.get("twitter_username")
    if not twitter_username:
        raise HTTPException(400, "Twitter username not found - please connect Twitter account")
    
    # Remove @ if present
    username = twitter_username.replace("@", "")
    
    async with httpx.AsyncClient() as client:
        try:
            # Get user profile to extract rest_id
            print(f"[INFO] Fetching user profile for {username}")
            profile_url = f"https://twitter-aio.p.rapidapi.com/user/by/username/{username}"
            headers = {
                "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
                "x-rapidapi-key": RAPIDAPI_KEY,
                "accept": "application/json"
            }
            
            profile_response = await client.get(profile_url, headers=headers, timeout=30)
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            
            # Extract rest_id from profile
            user_rest_id = profile_data.get("user", {}).get("result", {}).get("rest_id")
            if not user_rest_id:
                raise HTTPException(500, "Could not extract user rest_id from profile")
            
            print(f"[INFO] Found user rest_id: {user_rest_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch user profile: {e}")
            raise HTTPException(500, f"Failed to fetch user profile: {str(e)}")
    
    # Step 2: Get recent tweet IDs from posted_tweet_tracker
    print(f"[INFO] Fetching recent tweet IDs from database")
    recent_tweets = []
    async for tweet_record in db.posted_tweet_tracker.find(
        {"user": ObjectId(user_id)}
    ).sort("posted_at", -1).limit(50):
        recent_tweets.append(tweet_record)
    
    if not recent_tweets:
        return {
            "message": "No posted tweets found to fetch statistics for",
            "total_tweets_processed": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "stats_summary": {}
        }
    
    print(f"[INFO] Found {len(recent_tweets)} recent tweets to process")
    
    # Step 3: Fetch stats for each tweet with rate limiting
    stats_results = []
    successful_fetches = 0
    failed_fetches = 0
    
    # Rate limiting semaphore
    semaphore = asyncio.Semaphore(2)
    
    async def fetch_tweet_stats(tweet_record):
        nonlocal successful_fetches, failed_fetches
        
        async with semaphore:
            tweet_id = tweet_record["tweet_id"]
            
            try:
                # Add delay for rate limiting
                await asyncio.sleep(1)
                
                print(f"[INFO] Fetching stats for tweet {tweet_id}")
                
                # Call RapidAPI for tweet stats
                tweet_url = f"https://twitter-aio.p.rapidapi.com/tweet/{tweet_id}"
                params = {"count": "200"}
                
                response = await client.get(tweet_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                tweet_data = response.json()
                
                # Step 4: Process response to extract stats (exactly like n8n)
                instructions = (
                    tweet_data.get("data", {})
                    .get("threaded_conversation_with_injections_v2", {})
                    .get("instructions", [])
                )
                
                tweet_stats = None
                
                for instruction in instructions:
                    if instruction.get("type") != "TimelineAddEntries":
                        continue
                    
                    for entry in instruction.get("entries", []):
                        tweet_result = (
                            entry.get("content", {})
                            .get("itemContent", {})
                            .get("tweet_results", {})
                            .get("result")
                        )
                        
                        if not tweet_result:
                            continue
                        
                        # Check if this tweet is authored by the user (exactly like n8n)
                        author_id = (
                            tweet_result.get("core", {})
                            .get("user_results", {})
                            .get("result", {})
                            .get("rest_id")
                        )
                        
                        # Fallback to legacy id_str if rest_id not found
                        if not author_id:
                            author_id = (
                                tweet_result.get("core", {})
                                .get("user_results", {})
                                .get("result", {})
                                .get("legacy", {})
                                .get("id_str")
                            )
                        
                        if author_id != user_rest_id:
                            continue
                        
                        # Extract stats from legacy object (exactly like n8n)
                        legacy = tweet_result.get("legacy", {})
                        
                        # Extract views (exactly like n8n)
                        raw_views = tweet_result.get("views", {}).get("count")
                        views_count = 0
                        if raw_views is not None:
                            try:
                                views_count = int(raw_views) if isinstance(raw_views, str) else int(raw_views)
                            except (ValueError, TypeError):
                                views_count = 0

                        tweet_stats = {
                            "tweet_id": tweet_id,
                            "original_text": tweet_record.get("original_text", ""),
                            "tweet_type": tweet_record.get("tweet_type", ""),
                            "source_type": tweet_record.get("source_type", ""),
                            "source_context": tweet_record.get("source_context", ""),
                            "likes": legacy.get("favorite_count", 0),
                            "retweets": legacy.get("retweet_count", 0),
                            "replies": legacy.get("reply_count", 0),
                            "quotes": legacy.get("quote_count", 0),
                            "bookmarks": legacy.get("bookmark_count", 0),
                            "views": views_count,
                            "impressions": views_count,  # Same as views in Twitter API
                            "posted_at": tweet_record.get("posted_at"),
                            "fetched_at": datetime.now(timezone.utc)
                        }
                        break
                    
                    if tweet_stats:
                        break
                
                if tweet_stats:
                    stats_results.append(tweet_stats)
                    successful_fetches += 1
                    print(f"[SUCCESS] Fetched stats for tweet {tweet_id}: {tweet_stats['likes']} likes, {tweet_stats['retweets']} retweets")
                
                else:
                    failed_fetches += 1
                    print(f"[WARN] No stats found for tweet {tweet_id} (may not be authored by user)")
                
            except Exception as e:
                failed_fetches += 1
                print(f"[ERROR] Failed to fetch stats for tweet {tweet_id}: {e}")
    
    # Process all tweets concurrently with rate limiting
    async with httpx.AsyncClient() as client:
        tasks = [fetch_tweet_stats(tweet_record) for tweet_record in recent_tweets]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Step 5: Calculate summary statistics
    total_likes = sum(stat["likes"] for stat in stats_results)
    total_retweets = sum(stat["retweets"] for stat in stats_results)
    total_replies = sum(stat["replies"] for stat in stats_results)
    total_quotes = sum(stat["quotes"] for stat in stats_results)
    total_bookmarks = sum(stat["bookmarks"] for stat in stats_results)
    total_views = sum(stat["views"] for stat in stats_results)  # Now always int
    total_impressions = sum(stat["impressions"] for stat in stats_results)  # Same as views
    
    avg_engagement = (total_likes + total_retweets + total_replies + total_quotes + total_bookmarks) / len(stats_results) if stats_results else 0
    
    # Step 6: Feed raw performance data to mem0
    insights_added = 0
    mem = get_memory_client()
    if mem and stats_results:
        print(f"[MEM0] Adding {len(stats_results)} raw performance insights to memory")
        
        for stat in stats_results:
            # Simplified format: only tweet text, likes, and views
            insight = f"Tweet: '{stat['original_text']}' - {stat['likes']} likes, {stat['views']} views"
            
            try:
                mem.add(insight, user_id=user_id)
                insights_added += 1
                print(f"[MEM0 SUCCESS] Added: {insight[:80]}...")
            except Exception as e:
                print(f"[MEM0 ERROR] Failed to add insight: {e}")
        
        print(f"[MEM0] Successfully added {insights_added} simplified performance insights")
    else:
        print(f"[MEM0 SKIP] mem0 not available or no stats to process")
    
    print(f"[SUCCESS] Statistics fetch completed: {successful_fetches} successful, {failed_fetches} failed")
    
    return {
        "message": "Tweet statistics fetched and fed to mem0 successfully",
        "total_tweets_processed": len(recent_tweets),
        "successful_fetches": successful_fetches,
        "failed_fetches": failed_fetches,
        "insights_added_to_mem0": insights_added,
        "stats_summary": {
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "total_replies": total_replies,
            "total_quotes": total_quotes,
            "total_bookmarks": total_bookmarks,
            "total_views": total_views,
            "total_impressions": total_impressions,
            "avg_engagement": round(avg_engagement, 2)
        },
        "tweet_stats": stats_results  # Detailed stats for each tweet
    }





if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
