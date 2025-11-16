#!/usr/bin/env python3
import feedparser
import requests
import time
import json
import os
import re
import html as html_module
from datetime import datetime
from io import BytesIO
import shutil

MASTODON_URL = os.getenv("MASTODON_URL", "https://mastodon.social")
MASTODON_TOKEN = os.getenv("MASTODON_TOKEN", "")
RSSHUB_URL = os.getenv("RSSHUB_URL", "http://host.docker.internal:1200/twitter/user/L_ThinkTank")
TWITTER_ACCOUNT = "L_ThinkTank"
CACHE_FILE = "posted_urls.json"
CHECK_INTERVAL = 1800
AUTO_DELETE_DELAY = 30
AUTODESTRUCT_VIDEO_URL = "https://media.giphy.com/media/7G9jJdKhlCrED7vEvT/giphy.mp4"
MAX_CHAR_PER_POST = 490
STARTUP_MESSAGE_TEMPLATE = "🤖 Bot démarrage: {HEURE}\n📡 Surveillance: @{TWITTER_ACCOUNT}\n⏰ Auto-suppression dans {DELAY}s"
CONTINUATION_MESSAGE = "[La suite dans les commentaires 👇]"

def load_config_from_file():
    if os.path.exists("config.json"):
        try:
            with open("config.json", 'r') as f:
                config = json.load(f)
                print(f"[CONFIG] ✅ Config chargée depuis config.json")
                return config
        except Exception as e:
            print(f"[CONFIG] ❌ Erreur lecture config.json: {e}")
    return None

config_from_file = load_config_from_file()
if config_from_file:
    MASTODON_URL = config_from_file.get("MASTODON_URL", MASTODON_URL)
    MASTODON_TOKEN = config_from_file.get("MASTODON_TOKEN", MASTODON_TOKEN)
    RSSHUB_URL = config_from_file.get("RSSHUB_URL", RSSHUB_URL)
    TWITTER_ACCOUNT = config_from_file.get("TWITTER_ACCOUNT", TWITTER_ACCOUNT)
    CHECK_INTERVAL = int(config_from_file.get("CHECK_INTERVAL", CHECK_INTERVAL))
    AUTO_DELETE_DELAY = int(config_from_file.get("AUTO_DELETE_DELAY", AUTO_DELETE_DELAY))
    AUTODESTRUCT_VIDEO_URL = config_from_file.get("AUTODESTRUCT_VIDEO_URL", AUTODESTRUCT_VIDEO_URL)
    MAX_CHAR_PER_POST = int(config_from_file.get("MAX_CHAR_PER_POST", MAX_CHAR_PER_POST))
    STARTUP_MESSAGE_TEMPLATE = config_from_file.get("STARTUP_MESSAGE_TEMPLATE", STARTUP_MESSAGE_TEMPLATE)
    CONTINUATION_MESSAGE = config_from_file.get("CONTINUATION_MESSAGE", CONTINUATION_MESSAGE)

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            if os.path.isfile(CACHE_FILE):
                return json.load(open(CACHE_FILE))
            elif os.path.isdir(CACHE_FILE):
                print(f"[CACHE] ⚠️ {CACHE_FILE} est un dossier, suppression...")
                shutil.rmtree(CACHE_FILE)
                return []
        except Exception as e:
            print(f"[CACHE] ❌ Erreur lecture cache: {e}")
            return []
    return []

def save_cache(urls):
    try:
        if os.path.exists(CACHE_FILE) and os.path.isdir(CACHE_FILE):
            print(f"[CACHE] ⚠️ Suppression du dossier {CACHE_FILE}...")
            shutil.rmtree(CACHE_FILE)
        json.dump(urls, open(CACHE_FILE, "w"))
    except Exception as e:
        print(f"[CACHE] ❌ Erreur écriture cache: {e}")

def extract_media_from_description(description_html):
    media_urls = {
        'videos': [],
        'images': []
    }
    
    if not description_html:
        return []
    
    description_decoded = html_module.unescape(description_html)
    
    video_pattern = r'(?:https?://(?:video|cdn)\.twimg\.com/[^\s<>"]+\.(?:mp4|webm|mov|m3u8))'
    video_urls = re.findall(video_pattern, description_decoded, re.IGNORECASE)
    for url in video_urls:
        url = html_module.unescape(url)
        url = url.split('?')[0]
        if url and url not in media_urls['videos']:
            media_urls['videos'].append(url)
    
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    img_urls = re.findall(img_pattern, description_decoded)
    for url in img_urls:
        url = html_module.unescape(url)
        if url and url not in media_urls['images']:
            media_urls['images'].append(url)
    
    media_pattern = r'<a[^>]+href=["\']([^"\']+\.(?:jpg|jpeg|png|gif))["\']'
    media_urls_found = re.findall(media_pattern, description_decoded, re.IGNORECASE)
    for url in media_urls_found:
        url = html_module.unescape(url)
        if url and url not in media_urls['images']:
            media_urls['images'].append(url)
    
    img_src_pattern = r'(?:https?://pbs\.twimg\.com/media/[^\s<>"]+\.(?:jpg|jpeg|png|gif))'
    img_src_urls = re.findall(img_src_pattern, description_decoded, re.IGNORECASE)
    for url in img_src_urls:
        url = html_module.unescape(url)
        url = url.split('?')[0]
        if url and url not in media_urls['images']:
            media_urls['images'].append(url)
    
    result = media_urls['videos'] + media_urls['images']
    return result

def clean_description(description_html):
    if not description_html:
        return ""
    
    text = re.sub(r'<(?:div|blockquote|span)[^>]*class="rsshub-quote"[^>]*>.*?</(?:div|blockquote|span)>', '', description_html, flags=re.DOTALL)
    text = text.replace('<br/>', '\n').replace('<br>', '\n').replace('<br />', '\n')
    text = re.sub(r'<img[^>]*>', '', text)
    text = re.sub(r'<a[^>]*>', '', text)
    text = re.sub(r'</a>', '', text)
    text = re.sub('<[^<]+?>', '', text)
    text = html_module.unescape(text)
    
    lines = text.split('\n')
    text = '\n'.join([' '.join(line.split()) for line in lines])
    
    text = text.strip()
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    return text

def split_text_into_chunks(text, max_length=MAX_CHAR_PER_POST):
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    i = 0
    while i < len(text):
        if len(current_chunk) < max_length - 30:
            current_chunk += text[i]
            i += 1
        else:
            last_newline = current_chunk.rfind('\n')
            if last_newline > max_length * 0.7:
                chunk_to_save = current_chunk[:last_newline].strip()
                remaining = current_chunk[last_newline:].strip()
                if chunk_to_save:
                    chunks.append(chunk_to_save + "\n\n" + CONTINUATION_MESSAGE)
                current_chunk = remaining
            else:
                last_space = current_chunk.rfind(' ')
                if last_space > max_length * 0.6:
                    chunk_to_save = current_chunk[:last_space].strip()
                    remaining = current_chunk[last_space:].strip()
                    if chunk_to_save:
                        chunks.append(chunk_to_save + "\n\n" + CONTINUATION_MESSAGE)
                    current_chunk = remaining
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip() + "\n\n" + CONTINUATION_MESSAGE)
                    current_chunk = ""
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def upload_media(url):
    try:
        if 'video.twimg.com' in url or 'cdn.twimg.com' in url:
            media_type = "VIDEO"
        else:
            media_type = "IMAGE"
        
        print(f"[MEDIA] Downloading {media_type}: {url[:60]}")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            headers = {"Authorization": f"Bearer {MASTODON_TOKEN}"}
            files = {"file": BytesIO(r.content)}
            resp = requests.post(f"{MASTODON_URL}/api/v1/media", headers=headers, files=files)
            if resp.status_code == 200:
                media_id = resp.json()["id"]
                print(f"[MEDIA] ✅ {media_type} uploaded: {media_id}")
                time.sleep(1)
                return media_id
            elif resp.status_code == 429:
                print(f"[MEDIA] ⚠️ Rate limit (429), waiting 5 seconds...")
                time.sleep(5)
                return None
            elif resp.status_code == 422:
                print(f"[MEDIA] ⚠️ Rejected (422): {url[:50]}")
                return None
            else:
                print(f"[MEDIA] ❌ Upload failed: {resp.status_code}")
        else:
            print(f"[MEDIA] ❌ Download failed: {r.status_code}")
        return None
    except Exception as e:
        print(f"[MEDIA] ❌ Error: {str(e)[:100]}")
        return None

def post_to_mastodon(text, media_ids=None, reply_to_id=None):
    headers = {"Authorization": f"Bearer {MASTODON_TOKEN}", "Content-Type": "application/json"}
    
    valid_media_ids = [m for m in (media_ids or []) if m]
    
    text = text.strip()
    if not text:
        print(f"[POST] ❌ Empty text")
        return None
    
    data = {"status": text, "visibility": "public"}
    if reply_to_id:
        data["in_reply_to_id"] = reply_to_id
    
    if valid_media_ids and len(valid_media_ids) > 0:
        print(f"[POST] Using first media (priority video)...")
        data["media_ids"] = [valid_media_ids[0]]
        try:
            r = requests.post(f"{MASTODON_URL}/api/v1/statuses", headers=headers, json=data)
            if r.status_code == 200:
                status_id = r.json()["id"]
                print(f"[POST] ✅ Posted (ID: {status_id}) + 1 MEDIA")
                return status_id
            elif r.status_code == 422:
                print(f"[POST] ⚠️ 422 with media, trying without...")
        except Exception as e:
            print(f"[POST] ⚠️ Error with media: {e}")
    
    data.pop("media_ids", None)
    try:
        r = requests.post(f"{MASTODON_URL}/api/v1/statuses", headers=headers, json=data)
        if r.status_code == 200:
            status_id = r.json()["id"]
            reply_info = " [Reply]" if reply_to_id else ""
            print(f"[POST] ✅ Posted (ID: {status_id}){reply_info}: {text[:40]}")
            return status_id
        elif r.status_code == 422:
            print(f"[POST] ❌ Failed 422")
            return None
        print(f"[POST] ❌ Failed: {r.status_code}")
        return None
    except Exception as e:
        print(f"[POST] ❌ Error: {e}")
        return None

def post_thread(text, media_ids=None, media_urls=None):
    chunks = split_text_into_chunks(text)
    
    if len(chunks) == 1:
        return post_to_mastodon(chunks[0], media_ids)
    else:
        print(f"[THREAD] Creating thread with {len(chunks)} posts...")
        last_status_id = None
        
        for i, chunk in enumerate(chunks):
            print(f"[THREAD] Posting chunk {i+1}/{len(chunks)}")
            chunk_media_ids = media_ids if i == 0 else None
            status_id = post_to_mastodon(chunk, chunk_media_ids, reply_to_id=last_status_id)
            
            if status_id:
                last_status_id = status_id
                time.sleep(2)
            else:
                print(f"[THREAD] ❌ Failed to post chunk {i+1}")
                break
        
        return last_status_id

def start_bot():
    print("[INIT] Bot started with RSSHub + Videos Priority + No Quotes")
    
    startup_msg = STARTUP_MESSAGE_TEMPLATE.format(
        HEURE=datetime.now().strftime('%H:%M:%S'),
        DATE=datetime.now().strftime('%d/%m/%Y'),
        TWITTER_ACCOUNT=TWITTER_ACCOUNT,
        DELAY=AUTO_DELETE_DELAY
    )
    
    headers = {"Authorization": f"Bearer {MASTODON_TOKEN}", "Content-Type": "application/json"}
    
    print("[STARTUP] Uploading startup video...")
    startup_video_id = upload_media(AUTODESTRUCT_VIDEO_URL)
    
    data = {"status": startup_msg, "visibility": "public"}
    if startup_video_id:
        data["media_ids"] = [startup_video_id]
    
    status_id = None
    try:
        r = requests.post(f"{MASTODON_URL}/api/v1/statuses", headers=headers, json=data)
        if r.status_code == 200:
            status_id = r.json()["id"]
            print("[STARTUP] ✅ Message posted with video! 🎬")
    except Exception as e:
        print(f"[STARTUP] ⚠️ {e}")
    
    if status_id:
        print(f"[STARTUP] Waiting {AUTO_DELETE_DELAY}s before delete...")
        time.sleep(AUTO_DELETE_DELAY)
        try:
            requests.delete(f"{MASTODON_URL}/api/v1/statuses/{status_id}", headers={"Authorization": f"Bearer {MASTODON_TOKEN}"})
            print("[STARTUP] ✅ Message deleted! 💣")
        except Exception as e:
            print(f"[STARTUP] ⚠️ Delete failed: {e}")
    
    posted = load_cache()
    print(f"[CACHE] Loaded: {len(posted)} posts")
    
    if len(posted) == 0:
        print("[FIRST RUN] Posting only the latest tweet...")
        try:
            print(f"[FETCH] Fetching: {RSSHUB_URL}")
            headers_request = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(RSSHUB_URL, headers=headers_request, timeout=10)
            print(f"[FETCH] Response: {response.status_code}")
            
            feed = feedparser.parse(response.content)
            print(f"[FETCH] Entries: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
            
            if hasattr(feed, 'entries') and len(feed.entries) > 0:
                entry = feed.entries[0]
                tweet_url = entry.link if hasattr(entry, 'link') else ""
                tweet_description_html = entry.description if hasattr(entry, 'description') else (entry.title if hasattr(entry, 'title') else "No description")
                
                tweet_description = clean_description(tweet_description_html)
                
                media_ids = []
                
                description_media = extract_media_from_description(tweet_description_html)
                if description_media:
                    print(f"[MEDIA] Found {len(description_media)} medias (videos + images)")
                    for img_url in description_media:
                        media_id = upload_media(img_url)
                        if media_id:
                            media_ids.append(media_id)
                
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    print(f"[MEDIA] Found {len(entry.enclosures)} enclosures")
                    for enclosure in entry.enclosures:
                        media_id = upload_media(enclosure.href)
                        if media_id:
                            media_ids.append(media_id)
                
                print(f"[MEDIA] Total: {len(media_ids)}")
                
                posted_id = post_thread(tweet_description, media_ids, description_media)
                if posted_id:
                    posted.append(tweet_url)
                    save_cache(posted)
                    print("[FIRST RUN] ✅ First tweet posted!")
            else:
                print("[FIRST RUN] ❌ No entries")
        except Exception as e:
            import traceback
            print(f"[FIRST RUN] ❌ Error: {str(e)[:150]}")
            print(f"[FIRST RUN] {traceback.format_exc()}")
    
    try:
        while True:
            print(f"[{datetime.now()}] Checking RSSHub...")
            try:
                headers_request = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(RSSHUB_URL, headers=headers_request, timeout=10)
                feed = feedparser.parse(response.content)
                
                print(f"[FETCH] Entries: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
                
                if hasattr(feed, 'entries') and len(feed.entries) > 0:
                    latest_entry = feed.entries[0]
                    print(f"[FETCH] Latest: {latest_entry.title[:80] if hasattr(latest_entry, 'title') else 'No title'}")
                    
                    new_count = 0
                    for entry in feed.entries[:5]:
                        if not hasattr(entry, 'link'):
                            continue
                        
                        tweet_url = entry.link
                        if tweet_url not in posted:
                            tweet_description_html = entry.description if hasattr(entry, 'description') else (entry.title if hasattr(entry, 'title') else "No description")
                            
                            tweet_description = clean_description(tweet_description_html)
                            
                            media_ids = []
                            
                            description_media = extract_media_from_description(tweet_description_html)
                            if description_media:
                                print(f"[MEDIA] Found {len(description_media)} medias")
                                for img_url in description_media:
                                    media_id = upload_media(img_url)
                                    if media_id:
                                        media_ids.append(media_id)
                            
                            if hasattr(entry, 'enclosures') and entry.enclosures:
                                print(f"[MEDIA] Found {len(entry.enclosures)} enclosures")
                                for enclosure in entry.enclosures:
                                    media_id = upload_media(enclosure.href)
                                    if media_id:
                                        media_ids.append(media_id)
                            
                            print(f"[MEDIA] Total: {len(media_ids)}")
                            
                            posted_id = post_thread(tweet_description, media_ids, description_media)
                            if posted_id:
                                posted.append(tweet_url)
                                new_count += 1
                    
                    if new_count > 0:
                        save_cache(posted)
                        print(f"[OK] Posted {new_count} new tweets")
                    else:
                        print("[INFO] No new tweets")
                else:
                    print("[FETCH] ❌ Feed empty")
            except Exception as e:
                import traceback
                print(f"[ERROR] {str(e)[:150]}")
            
            print(f"[INFO] Next check in {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("[STOP]")

if __name__ == "__main__":
    start_bot()
