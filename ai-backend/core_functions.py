import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any
from bson import ObjectId

# Import from your existing modules
from database import db

# Import the helper functions from app.py (we'll need to make them importable)
# For now, I'll duplicate the key functions here

async def fetch_profile(client: httpx.AsyncClient, username: str) -> dict | None:
    """
    Call twitter-aio and return a cleaned profile dict, or None on error.
    Duplicated from app.py to make core functions independent.
    """
    from decouple import config
    RAPIDAPI_KEY = config("RAPIDAPI_KEY")
    
    # Clean the username - remove @ if present and strip whitespace
    clean_username = username.replace("@", "").strip()
    
    url = f"https://twitter-aio.p.rapidapi.com/user/by/username/{clean_username}"
    headers = {
        "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "accept": "application/json",
    }

    print(f"[DEBUG] Fetching profile for cleaned username: '{clean_username}'")

    try:
        r = await client.get(url, headers=headers, timeout=30)
        print(f"[DEBUG] Response status: {r.status_code}")
        
        if r.status_code == 400:
            error_text = r.text
            print(f"[ERROR] 400 Bad Request - Response body: {error_text}")
            return None
        
        r.raise_for_status()
        response_data = r.json()
        
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        print(f"[ERROR] API call failed for {clean_username}: {exc}")
        return None

    # Handle different response structures
    user_block = response_data.get("user", {}).get("result")
    if not user_block:
        print(f"[ERROR] No user block found for {username}")
        return None

    # Try multiple paths for screen_name
    legacy = user_block.get("legacy", {})
    core = user_block.get("core", {})
    
    screenname = (
        core.get("screen_name") or
        legacy.get("screen_name") or
        core.get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
    )
    
    if not screenname:
        print(f"[ERROR] No screen_name found for {username}")
        return None

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

    profile = {
        "screenname": screenname,
        "rest_id": user_block.get("rest_id"),
        "followersCount": followers_count,
        "description": description,
    }
    
    print(f"[SUCCESS] Extracted profile for {username}: {profile}")
    return profile


async def fetch_top_tweets(client: httpx.AsyncClient, keyword: str) -> List[dict]:
    """
    Call twitter-aio via RapidAPI for a search term
    Duplicated from app.py to make core functions independent.
    """
    from decouple import config
    from urllib.parse import urlencode
    
    RAPIDAPI_KEY = config("RAPIDAPI_KEY")
    
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
        "count": "20",
        "category": "latest",
        "lang": "en",
        "filters": '{"includeRetweets":false,"removeReplies":true,"removePostsWithLinks":true,"min_likes":100}'
    }

    print(f"[INFO] Searching tweets for keyword: '{keyword}'")

    try:
        r = await client.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        print(f"[SUCCESS] API response status: {r.status_code}")
    except Exception as exc:
        print(f"[ERROR] API call failed for '{keyword}': {exc}")
        return []

    try:
        response_json = r.json()
    except Exception as exc:
        print(f"[ERROR] JSON parsing failed: {exc}")
        return []

    # Process response
    output = []
    category = response_json
    entries = category.get("entries", [])
    print(f"[DEBUG] Processing {len(entries)} top-level entries")
    
    for entry_idx, entry_group in enumerate(entries):
        if not isinstance(entry_group, dict):
            continue
            
        sub_entries = entry_group.get("entries", [])
        
        for sub_idx, entry in enumerate(sub_entries):
            try:
                content = entry.get("content", {})
                item_content = content.get("itemContent", {})
                tweet_results = item_content.get("tweet_results", {})
                result = tweet_results.get("result")
                
                if not result:
                    continue
                
                tweet = result.get("tweet") or result
                legacy = tweet.get("legacy") if tweet else None
                
                if not legacy:
                    continue

                # Extract username
                username = None
                if tweet and "core" in tweet:
                    core_user = tweet["core"].get("user_results", {}).get("result", {})
                    username = core_user.get("legacy", {}).get("screen_name")
                
                if not username:
                    item = content.get("item", {})
                    item_content_alt = item.get("itemContent", {})
                    user_results = item_content_alt.get("user_results", {})
                    if user_results.get("result"):
                        username = user_results["result"].get("legacy", {}).get("screen_name")

                # Extract text
                note_text = None
                if tweet and "note_tweet" in tweet:
                    note_results = tweet["note_tweet"].get("note_tweet_results", {})
                    if note_results.get("result"):
                        note_text = note_results["result"].get("text")
                
                full_text = legacy.get("full_text")
                tweet_text = note_text or full_text

                if not tweet_text:
                    continue

                tweet_obj = {
                    "text": tweet_text,
                    "created_at": legacy.get("created_at"),
                    "conversation_id_str": legacy.get("conversation_id_str"),
                    "user_id_str": legacy.get("user_id_str"),
                    "username": username,
                    "keyword": keyword,
                }
                
                output.append(tweet_obj)
                
            except Exception as exc:
                print(f"[ERROR] Failed to process entry {entry_idx}-{sub_idx}: {exc}")
                continue

    print(f"[SUMMARY] Found {len(output)} tweets for '{keyword}'")
    return output


async def get_behavioral_intelligence(user_id: str, limit: int = 200) -> str:
    """
    Get behavioral intelligence from mem0 memory layer
    Duplicated from app.py to make core functions independent.
    """
    # Import memory from app.py context
    try:
        from app import get_memory_client
        memory = get_memory_client()
        if not memory:
            return ""
        
        # Use get_all() to retrieve all user memories
        results = memory.get_all(user_id=user_id)
        
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


async def select_draft_and_repurpose_tweets(tweets: List[dict], user_persona: str, keyword: str, user_id: str) -> List[dict]:
    """
    Behavioral intelligence: Select exactly 5 tweets + draft replies + draft repurposed content
    Duplicated from app.py to make core functions independent.
    """
    # Import AI client from app.py context
    try:
        from app import get_gemini_client
        client = get_gemini_client()
        if not tweets or not client or not user_id:
            return []
        
        if len(tweets) == 0:
            return []
        
        # GET BEHAVIORAL INTELLIGENCE FROM MEMORY LAYER
        print(f"[BEHAVIORAL] Gathering behavioral intelligence from memory layer for user {user_id}...")
        behavioral_context = await get_behavioral_intelligence(user_id, limit=200)
        
        # Pre-filter promotional content
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
        
        working_tweets = filtered_tweets if len(filtered_tweets) >= 10 else tweets
        
        # Build tweet list for LLM
        tweet_list = ""
        for i, tweet in enumerate(working_tweets, 1):
            tweet_list += f"{i}. @{tweet.get('username', 'unknown')}: \"{tweet['text'][:250]}\"\n"
        
        # Adaptive approach based on behavioral intelligence
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
        
        # Build prompt
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
            response = client.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse the response
            selected_tweets = []
            lines = response_text.split('\n')
            
            current_tweet_num = None
            current_reply = None
            current_repurpose = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Tweet ') and ':' in line:
                    # Save previous tweet if complete
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
            
            # Ensure exactly 5 selections
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
            
            selected_tweets = selected_tweets[:5]
            
            print(f"[SUCCESS] Selected {len(selected_tweets)} tweets using unified behavioral intelligence for '{keyword}'")
            return selected_tweets
            
        except Exception as e:
            print(f"[ERROR] Behavioral intelligence selection failed: {e}")
            # Fallback: select first 5 tweets with generic content
            fallback_selections = []
            for i, tweet in enumerate(working_tweets[:5]):
                fallback_selections.append({
                    'tweet': tweet,
                    'draft_reply': "Thanks for sharing! This is really insightful.",
                    'draft_post': "Interesting perspective on this topic. Worth considering."
                })
            return fallback_selections
            
    except Exception as e:
        print(f"[ERROR] Could not import required modules: {e}")
        return []


async def select_and_draft_user_tweet_replies(tweets: List[dict], user_persona: str, target_username: str, user_id: str) -> List[dict]:
    """
    Behavioral intelligence for user tweets: Select exactly 5 tweets + draft replies
    Duplicated from app.py to make core functions independent.
    """
    try:
        from app import get_gemini_client
        client = get_gemini_client()
        if not tweets or not client or not user_id:
            return []
        
        if len(tweets) == 0:
            return []
        
        # GET BEHAVIORAL INTELLIGENCE FROM MEMORY LAYER
        print(f"[BEHAVIORAL] Gathering behavioral intelligence from memory layer for user {user_id}...")
        behavioral_context = await get_behavioral_intelligence(user_id, limit=200)
        
        # Pre-filter promotional content
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
        
        working_tweets = filtered_tweets if len(filtered_tweets) >= 10 else tweets
        
        # Build tweet list for LLM
        tweet_list = ""
        for i, tweet in enumerate(working_tweets, 1):
            tweet_list += f"{i}. @{tweet.get('username', 'unknown')}: \"{tweet['text'][:250]}\"\n"
        
        # Adaptive approach
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
        
        # Build prompt
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
            response = client.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse the response
            selected_tweets = []
            lines = response_text.split('\n')
            
            current_tweet_num = None
            current_reply = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Tweet ') and ':' in line:
                    # Save previous tweet if complete
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
            
            # Ensure exactly 5 selections
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
            
    except Exception as e:
        print(f"[ERROR] Could not import required modules: {e}")
        return []


async def core_scrape_top_tweets(user_id: str) -> Dict[str, Any]:
    """
    Core function for scraping top tweets - extracted from app.py /scrape_top_tweets endpoint
    This function contains all the logic for keyword-based tweet scraping with behavioral intelligence
    """
    from decouple import config
    
    RAPIDAPI_KEY = config("RAPIDAPI_KEY")
    
    if not RAPIDAPI_KEY:
        raise Exception("RAPIDAPI_KEY environment variable missing")
    
    try:
        from app import get_gemini_client
        client = get_gemini_client()
        if not client:
            raise Exception("Gemini client not initialized")
    except ImportError:
        raise Exception("Could not import Gemini client from app")

    # Convert user_id to ObjectId if it's a string
    if isinstance(user_id, str):
        try:
            user_obj_id = ObjectId(user_id)
        except:
            raise Exception(f"Invalid user_id format: {user_id}")
    else:
        user_obj_id = user_id

    user_filter = {"_id": user_obj_id}
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

            # Process keywords sequentially
            for keyword in search_keywords:
                print(f"[INFO] Fetching tweets for keyword: {keyword}")
                
                await asyncio.sleep(2)  # Rate limiting
                
                # Fetch tweets using core function
                tweets = await fetch_top_tweets(http_client, keyword)
                
                if not tweets:
                    print(f"[WARN] No tweets found for keyword: {keyword}")
                    results.append({"keyword": keyword, "status": "no_tweets", "count": 0})
                    continue

                print(f"[INFO] Found {len(tweets)} candidate tweets for keyword: {keyword}")
                
                # Behavioral Intelligence: selection + reply drafting + repurposing
                selected_tweets = await select_draft_and_repurpose_tweets(tweets, user_persona, keyword, str(uid))
                print(f"[INFO] Selected {len(selected_tweets)} tweets with behavioral intelligence for keyword: {keyword}")
                
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
                        "time_posted": tweet["created_at"],
                        "created_at": datetime.utcnow(),

                        # Pre-drafted reply
                        "draft_reply": draft_reply,
                        "reply_status": "PENDING",
                        "posted_reply_id": None,
                        
                        # Pre-drafted repurposed content
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


async def core_scrape_user_tweets(user_id: str) -> Dict[str, Any]:
    """
    Core function for scraping user tweets - extracted from app.py /scrape_user_tweets endpoint  
    This function contains all the logic for target account tweet scraping with behavioral intelligence
    """
    from decouple import config
    
    RAPIDAPI_KEY = config("RAPIDAPI_KEY")
    
    if not RAPIDAPI_KEY:
        raise Exception("RAPIDAPI_KEY environment variable missing")
    
    try:
        from app import get_gemini_client
        client = get_gemini_client()
        if not client:
            raise Exception("Gemini client not initialized")
    except ImportError:
        raise Exception("Could not import Gemini client from app")

    # Convert user_id to ObjectId if it's a string
    if isinstance(user_id, str):
        try:
            user_obj_id = ObjectId(user_id)
        except:
            raise Exception(f"Invalid user_id format: {user_id}")
    else:
        user_obj_id = user_id

    user_filter = {"_id": user_obj_id}
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

                        # Behavioral Intelligence for User Tweets - selection + reply drafting
                        selected_tweets = await select_and_draft_user_tweet_replies(tweets, current_persona, current_username, str(current_uid))
                        print(f"[INFO] Selected {len(selected_tweets)} tweets with user tweet behavioral intelligence for {current_username}")

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
                                "draft_reply": draft_reply,  # Pre-drafted reply using behavioral intelligence
                                "reply_status": "PENDING",
                                "posted_reply_id": None,
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