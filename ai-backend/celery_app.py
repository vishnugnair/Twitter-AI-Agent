from celery import Celery
from celery.schedules import crontab
from decouple import config

# Create Celery instance
app = Celery('twitter_growth_app')

# Load Redis configuration from environment
REDIS_HOST = config("REDIS_HOST")
REDIS_PORT = config("REDIS_PORT", cast=int)
REDIS_PASSWORD = config("REDIS_PASSWORD")
REDIS_USERNAME = config("REDIS_USERNAME", default="default")

# Build Redis URL
redis_url = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

# Configure Celery
app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'tasks.test_task': {'queue': 'test'},
        'tasks.scrape_user_tweets_task': {'queue': 'scraping'},
        'tasks.scrape_top_tweets_task': {'queue': 'scraping'},
        'tasks.trigger_all_user_scraping': {'queue': 'orchestration'},
    },
    
    # Default queue
    task_default_queue='default',
    
    # Retry configuration
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Rate limiting
    task_annotations={
        'tasks.scrape_user_tweets_task': {'rate_limit': '5/m'},
        'tasks.scrape_top_tweets_task': {'rate_limit': '5/m'},
    },
    
    # Beat schedule for automatic tasks
    beat_schedule={
        'test-every-minute': {
            'task': 'tasks.test_task',
            'schedule': crontab(minute='*'),  # Every minute for testing
        },
        # Main scheduler - runs twice daily for all users
        'daily-user-scraping': {
            'task': 'tasks.trigger_all_user_scraping',
            'schedule': crontab(hour='8,20'),  # 8 AM and 8 PM
        },
    },
)

# Auto-discover tasks
app.autodiscover_tasks(['tasks'])

print(f"[CELERY] Configured with Redis: {REDIS_HOST}:{REDIS_PORT}") 