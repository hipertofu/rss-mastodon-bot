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

MASTODON_URL = os.getenv("MASTODON_URL", "https://mastodon.social")
MASTODON_TOKEN = os.getenv("MASTODON_TOKEN", "")
RSSHUB_URL = os.getenv("RSSHUB_URL", "http://host.docker.internal:1200/twitter/user/<TWITTER_USERNAME>")
TWITTER_ACCOUNT = "<TWITTER_USERNAME>"
CACHE_FILE = "posted_urls.json"
CHECK_INTERVAL = 1800
AUTO_DELETE_DELAY = 30

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE))
        except:
            pass
    return []

def save_cache(urls):
    json.dump(urls, open(CACHE_FILE, "w"))

def extract_media_from_description(description_html):
    """Extrait les URLs d'images/vidéos de la description HTML"""
    media_urls = []
    
    if not description_html:
        return media_urls
    
    # Décode les entités HTML d'abord
    description_decoded = html_module.unescape(description_html)
    
    # Regex pour trouver les images dans les balises <img>
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    img_urls = re.findall(img_pattern, description_decoded)
    for url in img_urls:
        url = html_module.unescape(url)
        if url:
            media_urls.append(url)
    
    # Regex pour trouver les vidéos/images dans les liens avec classe media
    media_pattern = r'<a[^>]+href=["\']([^"\']+\.(?:jpg|jpeg|png|gif|mp4|webm|mov|m3u8))["\']'
    media_urls_found = re.findall(media_pattern, description_decoded, re.IGNORECASE)
    for url in media_urls_found:
        url = html_module.unescape(url)
        if url:
            media_urls.append(url)
    
    # Regex pour trouver les images directes (pbs.twimg.com, video.twimg.com)
    src_pattern = r'(?:https?://(?:pbs|video|cdn)\.twimg\.com/[^\s<>"]+\.(?:jpg|jpeg|png|gif|mp4|webm|mov|m3u8))'
    src_urls = re.findall(src_pattern, description_decoded, re.IGNORECASE)
    for url in src_urls:
        url = html_module.unescape(url)
        # Nettoie l'URL : enlève les paramètres inutiles et les fragments
        url = url.split('?')[0]  # Enlève tout après le ?
        if url:
            media_urls.append(url)
    
    return list(set(media_urls))  # Supprime les doublons

def clean_description(description_html):
    """Nettoie le HTML et retourne le texte"""
    if not description_html:
        return ""
    
    # Remplace les <br> par des newlines
    text = description_html.replace('<br/>', '\n').replace('<br>', '\n').replace('<br />', '\n')
    
    # Supprime les balises <img> entières
    text = re.sub(r'<img[^>]*>', '', text)
    
    # Supprime les balises <a> mais garde le texte
    text = re.sub(r'<a[^>]*>', '', text)
    text = re.sub(r'</a>', '', text)
    
    # Supprime les autres balises HTML
    text = re.sub('<[^<]+?>', '', text)
    
    # Décode les entités HTML
    text = html_module.unescape(text)
    
    # Supprime les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def upload_media(url):
    try:
        print(f"[INFO] Downloading media: {url[:60]}")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            headers = {"Authorization": f"Bearer {MASTODON_TOKEN}"}
            files = {"file": BytesIO(r.content)}
            resp = requests.post(f"{MASTODON_URL}/api/v1/media", headers=headers, files=files)
            if resp.status_code == 200:
                media_id = resp.json()["id"]
                print(f"[OK] Media uploaded: {media_id}")
                return media_id
            else:
                print(f"[ERROR] Upload failed: {resp.status_code}")
        else:
            print(f"[ERROR] Download failed: {r.status_code}")
        return None
    except Exception as e:
        print(f"[ERROR] Media upload failed: {str(e)[:100]}")
        return None

def post_to_mastodon(text, media_ids=None):
    """Poste sur Mastodon SANS le lien, juste le texte + les médias"""
    headers = {"Authorization": f"Bearer {MASTODON_TOKEN}", "Content-Type": "application/json"}
    data = {"status": text, "visibility": "public"}
    if media_ids and len(media_ids) > 0:
        data["media_ids"] = media_ids
    try:
        r = requests.post(f"{MASTODON_URL}/api/v1/statuses", headers=headers, json=data)
        if r.status_code == 200:
            status_id = r.json()["id"]
            print(f"[OK] Posted (ID: {status_id}): {text[:40]}")
            return status_id
        print(f"[ERROR] Post failed: {r.status_code}")
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

print("[INIT] Bot started with RSSHub + Media extraction")

startup_msg = f"""🤖 Bot demarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📡 Surveillance: @{TWITTER_ACCOUNT}

⏰ Message destiné à l'autodestruction
   (Comme le service d'Ethan Hunt... mais sans la dramatique)
   Ce message s'évaporera en {AUTO_DELETE_DELAY}s ☁️💨"""

headers = {"Authorization": f"Bearer {MASTODON_TOKEN}", "Content-Type": "application/json"}
data = {"status": startup_msg, "visibility": "public"}
status_id = None
try:
    r = requests.post(f"{MASTODON_URL}/api/v1/statuses", headers=headers, json=data)
    if r.status_code == 200:
        status_id = r.json()["id"]
        print("[OK] Startup message posted")
except Exception as e:
    print(f"[WARNING] {e}")

if status_id:
    print(f"[INFO] Waiting {AUTO_DELETE_DELAY}s before delete...")
    time.sleep(AUTO_DELETE_DELAY)
    try:
        requests.delete(f"{MASTODON_URL}/api/v1/statuses/{status_id}", headers={"Authorization": f"Bearer {MASTODON_TOKEN}"})
        print("[OK] Startup message deleted! 💣")
    except Exception as e:
        print(f"[WARNING] Delete failed: {e}")

posted = load_cache()
print(f"[INIT] Cached: {len(posted)}")

if len(posted) == 0:
    print("[INIT] First run...")
    try:
        print(f"[INFO] Fetching: {RSSHUB_URL}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(RSSHUB_URL, headers=headers, timeout=10)
        print(f"[DEBUG] Response status: {response.status_code}")
        
        feed = feedparser.parse(response.content)
        print(f"[DEBUG] Number of entries: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
        
        if hasattr(feed, 'entries') and len(feed.entries) > 0:
            entry = feed.entries[0]
            tweet_url = entry.link if hasattr(entry, 'link') else ""
            tweet_description_html = entry.description if hasattr(entry, 'description') else (entry.title if hasattr(entry, 'title') else "No description")
            
            # Nettoie la description
            tweet_description = clean_description(tweet_description_html)
            
            media_ids = []
            
            # Cherche les images dans la description HTML
            print(f"[INFO] Looking for images in description...")
            description_media = extract_media_from_description(tweet_description_html)
            if description_media:
                print(f"[INFO] Found {len(description_media)} images in description")
                for img_url in description_media:
                    print(f"[DEBUG] Image URL: {img_url}")
                    media_id = upload_media(img_url)
                    if media_id:
                        media_ids.append(media_id)
            
            # Cherche les enclosures classiques
            if hasattr(entry, 'enclosures') and entry.enclosures:
                print(f"[INFO] Found {len(entry.enclosures)} enclosures")
                for enclosure in entry.enclosures:
                    media_id = upload_media(enclosure.href)
                    if media_id:
                        media_ids.append(media_id)
            
            print(f"[INFO] Total media to post: {len(media_ids)}")
            
            # Poste SANS le lien du tweet
            posted_id = post_to_mastodon(tweet_description, media_ids)
            if posted_id:
                posted.append(tweet_url)
                save_cache(posted)
                print("[OK] First tweet posted!")
        else:
            print("[ERROR] No entries in feed")
    except Exception as e:
        import traceback
        print(f"[ERROR] First tweet: {str(e)[:150]}")
        print(f"[ERROR] {traceback.format_exc()}")

try:
    while True:
        print(f"[{datetime.now()}] Checking RSSHub...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(RSSHUB_URL, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            
            print(f"[DEBUG] Number of entries: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
            
            if hasattr(feed, 'entries') and len(feed.entries) > 0:
                latest_entry = feed.entries[0]
                print(f"[DEBUG] Latest tweet: {latest_entry.title[:80] if hasattr(latest_entry, 'title') else 'No title'}")
                
                new_count = 0
                for entry in feed.entries[:5]:
                    if not hasattr(entry, 'link'):
                        continue
                    
                    tweet_url = entry.link
                    if tweet_url not in posted:
                        tweet_description_html = entry.description if hasattr(entry, 'description') else (entry.title if hasattr(entry, 'title') else "No description")
                        
                        # Nettoie la description
                        tweet_description = clean_description(tweet_description_html)
                        
                        media_ids = []
                        
                        # Cherche les images dans la description HTML
                        print(f"[INFO] Looking for images in description...")
                        description_media = extract_media_from_description(tweet_description_html)
                        if description_media:
                            print(f"[INFO] Found {len(description_media)} images in description")
                            for img_url in description_media:
                                print(f"[DEBUG] Image URL: {img_url}")
                                media_id = upload_media(img_url)
                                if media_id:
                                    media_ids.append(media_id)
                        
                        # Cherche les enclosures classiques
                        if hasattr(entry, 'enclosures') and entry.enclosures:
                            print(f"[INFO] Found {len(entry.enclosures)} enclosures")
                            for enclosure in entry.enclosures:
                                media_id = upload_media(enclosure.href)
                                if media_id:
                                    media_ids.append(media_id)
                        
                        print(f"[INFO] Total media to post: {len(media_ids)}")
                        
                        # Poste SANS le lien du tweet
                        posted_id = post_to_mastodon(tweet_description, media_ids)
                        if posted_id:
                            posted.append(tweet_url)
                            new_count += 1
                
                if new_count > 0:
                    save_cache(posted)
                    print(f"[OK] Posted {new_count} new tweets")
                else:
                    print("[INFO] No new tweets")
            else:
                print("[ERROR] Feed empty")
        except Exception as e:
            import traceback
            print(f"[ERROR] {str(e)[:150]}")
        
        print(f"[INFO] Next check in {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)
except KeyboardInterrupt:
    print("[STOP]")
