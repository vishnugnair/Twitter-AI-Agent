from celery_app import app
from datetime import datetime
import asyncio
from bson import ObjectId

# Import database and core functions
from database import db

@app.task(bind=True)
def test_task(self):
    """Simple test task to verify Celery is working"""
    current_time = datetime.utcnow()
    print(f"[TEST TASK] Hello from Celery! Time: {current_time}")
    
    return {
        "message": "Test task completed successfully!",
        "task_id": self.request.id,
        "timestamp": current_time.isoformat(),
        "worker": self.request.hostname
    }

@app.task(bind=True, max_retries=3)
def scrape_user_tweets_task(self, user_id: str):
    """Background task for scraping user tweets using core function"""
    try:
        print(f"[SCRAPE USER TWEETS] Starting task for user: {user_id}")
        
        # Import and use core function
        from core_functions import core_scrape_user_tweets
        
        # Run the core scraping function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(core_scrape_user_tweets(user_id))
            return {
                "message": f"User tweets scraping completed for user {user_id}",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
                "core_result": result
            }
        finally:
            loop.close()
        
    except Exception as e:
        print(f"[ERROR] User tweets scraping failed for {user_id}: {e}")
        # Retry with exponential backoff
        self.retry(countdown=2 ** self.request.retries, exc=e)

@app.task(bind=True, max_retries=3)
def scrape_top_tweets_task(self, user_id: str):
    """Background task for scraping top tweets using core function"""
    try:
        print(f"[SCRAPE TOP TWEETS] Starting task for user: {user_id}")
        
        # Import and use core function
        from core_functions import core_scrape_top_tweets
        
        # Run the core scraping function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(core_scrape_top_tweets(user_id))
            return {
                "message": f"Top tweets scraping completed for user {user_id}",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
                "core_result": result
            }
        finally:
            loop.close()
        
    except Exception as e:
        print(f"[ERROR] Top tweets scraping failed for {user_id}: {e}")
        # Retry with exponential backoff
        self.retry(countdown=2 ** self.request.retries, exc=e)

@app.task(bind=True)
def trigger_all_user_scraping(self):
    """Master task that triggers scraping for all users"""
    print(f"[MASTER TASK] Starting to trigger scraping for all users")
    
    try:
        # Get all users from the database
        users_processed = 0
        users_failed = 0
        
        # Query database for all users
        cursor = db.users.find({})
        
        for user in cursor:
            try:
                user_id = str(user["_id"])
                
                # Schedule both scraping tasks for each user
                scrape_user_tweets_task.delay(user_id)
                scrape_top_tweets_task.delay(user_id)
                
                users_processed += 1
                print(f"[MASTER TASK] Scheduled scraping for user: {user_id}")
                
            except Exception as e:
                users_failed += 1
                print(f"[ERROR] Failed to schedule scraping for user {user.get('_id')}: {e}")
        
        return {
            "message": f"Triggered scraping for {users_processed} users",
            "users_processed": users_processed,
            "users_failed": users_failed,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }
        
    except Exception as e:
        print(f"[ERROR] Master task failed: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }

# Helper function to test database connection in tasks
def test_database_connection():
    """Test if we can connect to database from Celery tasks"""
    try:
        # Simple test query
        result = db.users.find_one()
        return True
    except Exception as e:
        print(f"[ERROR] Database connection failed in task: {e}")
        return False 