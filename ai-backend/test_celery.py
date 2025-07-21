#!/usr/bin/env python3
"""
Test script to verify Celery is working correctly
"""

from tasks import test_task, scrape_user_tweets_task, scrape_top_tweets_task, trigger_all_user_scraping
import time

def test_basic_task():
    """Test basic task functionality"""
    print("=== Testing Basic Task ===")
    
    # Send test task
    result = test_task.delay()
    print(f"Task sent with ID: {result.id}")
    
    # Wait for result
    print("Waiting for task to complete...")
    try:
        response = result.get(timeout=10)
        print(f"✅ Task completed successfully!")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"❌ Task failed: {e}")
        return False

def test_scraping_tasks():
    """Test scraping task functionality"""
    print("\n=== Testing Scraping Tasks ===")
    
    # Test user tweets scraping
    print("Testing user tweets scraping...")
    user_task = scrape_user_tweets_task.delay("test_user_123")
    print(f"User tweets task ID: {user_task.id}")
    
    # Test top tweets scraping  
    print("Testing top tweets scraping...")
    top_task = scrape_top_tweets_task.delay("test_user_123")
    print(f"Top tweets task ID: {top_task.id}")
    
    # Wait for both tasks
    try:
        user_result = user_task.get(timeout=10)
        top_result = top_task.get(timeout=10)
        
        print(f"✅ User tweets result: {user_result}")
        print(f"✅ Top tweets result: {top_result}")
        return True
    except Exception as e:
        print(f"❌ Scraping tasks failed: {e}")
        return False

def test_master_task():
    """Test master orchestration task"""
    print("\n=== Testing Master Task ===")
    
    # Send master task
    master_task = trigger_all_user_scraping.delay()
    print(f"Master task ID: {master_task.id}")
    
    # Wait for result
    try:
        result = master_task.get(timeout=15)
        print(f"✅ Master task completed!")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"❌ Master task failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Celery Tests...")
    print("Make sure Celery worker is running: python start_celery.py")
    print("=" * 50)
    
    tests = [
        ("Basic Task", test_basic_task),
        ("Scraping Tasks", test_scraping_tasks),
        ("Master Task", test_master_task),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        if test_func():
            passed += 1
        time.sleep(2)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Celery is working correctly.")
    else:
        print("⚠️  Some tests failed. Check Celery worker logs.")

if __name__ == "__main__":
    main() 