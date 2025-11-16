#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import json
import os
import subprocess
import threading
import feedparser
import requests
import re
import html as html_module
from io import BytesIO

app = Flask(__name__)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "MASTODON_URL": "https://mastodon.social",
    "MASTODON_TOKEN": "",
    "RSSHUB_URL": "http://host.docker.internal:1200/twitter/user/L_ThinkTank",
    "TWITTER_ACCOUNT": "L_ThinkTank",
    "CHECK_INTERVAL": "1800",
    "AUTO_DELETE_DELAY": "30",
    "AUTODESTRUCT_VIDEO_URL": "https://media.giphy.com/media/7G9jJdKhlCrED7vEvT/giphy.mp4",
    "MAX_CHAR_PER_POST": "490",
    "STARTUP_MESSAGE_TEMPLATE": "🤖 Bot démarrage: {HEURE}\n📡 Surveillance: @{TWITTER_ACCOUNT}\n⏰ Auto-suppression dans {DELAY}s",
    "CONTINUATION_MESSAGE": "[La suite dans les commentaires 👇]"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"[WEB UI] ❌ Erreur écriture config: {e}")

def update_env_file():
    try:
        config = load_config()
        env_content = f"""MASTODON_URL={config['MASTODON_URL']}
MASTODON_TOKEN={config['MASTODON_TOKEN']}
RSSHUB_URL={config['RSSHUB_URL']}
"""
        with open('.env', 'w') as f:
            f.write(env_content)
    except Exception as e:
        print(f"[WEB UI] ❌ Erreur écriture .env: {e}")

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
    
    img_src_pattern = r'(?:https?://pbs\.twimg\.com/media/[^\s<>"]+\.(?:jpg|jpeg|png|gif))'
    img_src_urls = re.findall(img_src_pattern, description_decoded, re.IGNORECASE)
    for url in img_src_urls:
        url = html_module.unescape(url)
        url = url.split('?')[0]
        if url and url not in media_urls['images']:
            media_urls['images'].append(url)
    
    result = media_urls['videos'] + media_urls['images']
    return result

def upload_media_test(url, token, mastodon_url):
    try:
        print(f"[TEST] Uploading: {url[:60]}")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            headers = {"Authorization": f"Bearer {token}"}
            files = {"file": BytesIO(r.content)}
            resp = requests.post(f"{mastodon_url}/api/v1/media", headers=headers, files=files)
            if resp.status_code == 200:
                media_id = resp.json()["id"]
                print(f"[TEST] ✅ Uploaded: {media_id}")
                return media_id
            else:
                print(f"[TEST] ❌ Upload failed: {resp.status_code}")
        return None
    except Exception as e:
        print(f"[TEST] ❌ Error: {str(e)[:100]}")
        return None

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

@app.route('/api/config', methods=['GET'])
def get_config():
    config = load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config_endpoint():
    try:
        data = request.json
        config = load_config()
        config.update(data)
        save_config(config)
        update_env_file()
        
        print(f"\n[WEB UI] ⚙️ Configuration mise à jour:")
        for key, value in data.items():
            if 'TOKEN' in key or 'PASSWORD' in key:
                print(f"  - {key}: ***hidden***")
            else:
                print(f"  - {key}: {value[:80] if isinstance(value, str) else value}")
        print()
        
        return jsonify({"status": "success", "message": "Configuration mise à jour"})
    except Exception as e:
        print(f"[WEB UI] ❌ Erreur config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/test', methods=['POST'])
def test_post():
    try:
        config = load_config()
        rsshub_url = config.get("RSSHUB_URL", "")
        token = config.get("MASTODON_TOKEN", "")
        mastodon_url = config.get("MASTODON_URL", "https://mastodon.social")
        
        if not rsshub_url or not token:
            return jsonify({"status": "error", "message": "Config manquante"}), 400
        
        print("\n[TEST] 🧪 Début du test...")
        
        print(f"[TEST] Fetching: {rsshub_url}")
        headers_request = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(rsshub_url, headers=headers_request, timeout=10)
        print(f"[TEST] Response: {response.status_code}")
        
        feed = feedparser.parse(response.content)
        print(f"[TEST] Entries: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
        
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            return jsonify({"status": "error", "message": "Aucun entry trouvé"}), 400
        
        entry = feed.entries[0]
        tweet_url = entry.link if hasattr(entry, 'link') else ""
        tweet_description_html = entry.description if hasattr(entry, 'description') else (entry.title if hasattr(entry, 'title') else "")
        
        tweet_description = clean_description(tweet_description_html)
        print(f"[TEST] Text: {tweet_description[:80]}")
        
        media_ids = []
        description_media = extract_media_from_description(tweet_description_html)
        if description_media:
            print(f"[TEST] Found {len(description_media)} medias")
            for img_url in description_media:
                print(f"[TEST] Uploading: {img_url[:60]}")
                media_id = upload_media_test(img_url, token, mastodon_url)
                if media_id:
                    media_ids.append(media_id)
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {"status": tweet_description, "visibility": "public"}
        
        if media_ids:
            data["media_ids"] = [media_ids[0]]
            print(f"[TEST] Posting with media...")
        else:
            print(f"[TEST] Posting without media...")
        
        r = requests.post(f"{mastodon_url}/api/v1/statuses", headers=headers, json=data)
        
        if r.status_code == 200:
            status_id = r.json()["id"]
            print(f"[TEST] ✅ Posted! ID: {status_id}\n")
            return jsonify({
                "status": "success",
                "message": f"✅ Post envoyé! ID: {status_id}",
                "text": tweet_description[:100] + "...",
                "media_count": len(media_ids)
            })
        else:
            print(f"[TEST] ❌ Failed: {r.status_code}\n")
            return jsonify({
                "status": "error",
                "message": f"❌ Erreur Mastodon: {r.status_code}"
            }), 500
    
    except Exception as e:
        print(f"[TEST] ❌ Error: {str(e)}\n")
        return jsonify({
            "status": "error",
            "message": f"❌ Erreur: {str(e)[:200]}"
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route non trouvée"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Erreur serveur interne"}), 500

if __name__ == '__main__':
    print("\n[WEB UI] 🚀 Interface web démarrée sur http://0.0.0.0:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
