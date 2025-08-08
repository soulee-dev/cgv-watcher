import os
import time
import hmac
import json
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

SECRET_KEY = os.getenv("CGV_SECRET_KEY").encode('utf-8')
API_URL = os.getenv("API_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SEEN_FILE = "seen_dates.json"

def generate_signature(url: str, body=None):
    timestamp = str(int(time.time()))

    pathname = urlparse(url).path

    if body is None:
        body_str = ""
    elif isinstance(body, str):
        body_str = body
    else:
        body_str = "multipart/form-data"

    plain = f"{timestamp}|{pathname}|{body_str}"

    signature = base64.b64encode(
        hmac.new(SECRET_KEY, plain.encode('utf-8'), digestmod='sha256').digest()
    ).decode('utf-8')

    return timestamp, signature

def load_seen_dates():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_dates(dates):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(dates), f, ensure_ascii=False, indent=2)

def send_discord_message(new_dates):
    content = f"🎬 **새로운 영화 예매일이 추가되었습니다!**\n" + \
              "\n".join(f"- {datetime.strptime(d, '%Y%m%d').strftime('%Y-%m-%d')}" for d in sorted(new_dates))
    try:
        resp = requests.post(WEBHOOK_URL, json={"content": content}, timeout=10)
        resp.raise_for_status()
        print(f"[INFO] Sent Discord notification for {len(new_dates)} dates.")
    except Exception as e:
        print(f"[ERROR] Failed to send Discord message: {e}")

def fetch_dates():
    timestamp, signature = generate_signature(API_URL)
    headers = {
        'accept': 'application/json',
        'accept-language': 'ko-KR',
        'cache-control': 'no-cache',
        'origin': 'https://cgv.co.kr',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://cgv.co.kr/',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'x-signature': signature,
        'x-timestamp': timestamp,
    }

    params = {
        'coCd': 'A420',
        'siteNo': '0013',
        'movNo': '89706',
        'div': 'TCSCNS_GRAD_CD',
        'attrCd': '03',
    }

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if "data" in data:
            return {item["scnYmd"] for item in data["data"]}
        return set()
    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")
        return set()

def main():
    seen_dates = load_seen_dates()
    current_dates = fetch_dates()
    if current_dates:
        new_dates = current_dates - seen_dates
        if new_dates:
            send_discord_message(new_dates)
            seen_dates.update(new_dates)
            save_seen_dates(seen_dates)
        else:
            print("[INFO] No new dates found.")

if __name__ == "__main__":
    main()