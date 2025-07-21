#!/usr/bin/env python3
"""
Startup script for Celery worker and beat scheduler
"""

import subprocess
import sys
import os
import time
import signal
from threading import Thread

def run_worker():
    """Run Celery worker"""
    print("[STARTUP] Starting Celery worker...")
    cmd = [
        sys.executable, "-m", "celery", 
        "-A", "celery_app", 
        "worker", 
        "--loglevel=info",
        "--concurrency=2",
        "--pool=solo",  # Use solo pool for Windows
        "--queues=default,test,scraping,orchestration"
    ]
    
    try:
        return subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Celery worker failed: {e}")
        return None

def run_beat():
    """Run Celery beat scheduler"""
    print("[STARTUP] Starting Celery beat scheduler...")
    cmd = [
        sys.executable, "-m", "celery", 
        "-A", "celery_app", 
        "beat", 
        "--loglevel=info"
    ]
    
    try:
        return subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Celery beat failed: {e}")
        return None

def run_flower():
    """Run Flower monitoring (optional)"""
    print("[STARTUP] Starting Flower monitoring...")
    cmd = [
        sys.executable, "-m", "celery", 
        "-A", "celery_app", 
        "flower", 
        "--port=5555"
    ]
    
    try:
        return subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Flower failed: {e}")
        return None

if __name__ == "__main__":
    print("=== Twitter Growth App - Celery Startup ===")
    print("Starting Celery worker and beat scheduler...")
    
    # Create threads for worker and beat
    worker_thread = Thread(target=run_worker, daemon=True)
    beat_thread = Thread(target=run_beat, daemon=True)
    
    # Start both
    worker_thread.start()
    time.sleep(2)  # Give worker time to start
    beat_thread.start()
    
    print("\n✅ Celery is running!")
    print("- Worker: Processing background tasks")
    print("- Beat: Scheduling automatic tasks")
    print("- Press Ctrl+C to stop")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping Celery...")
        sys.exit(0) 