import requests
import csv
from datetime import datetime, timedelta
import os

# ---------------- CONFIG ----------------

API_URL = "https://admin.bookodisha.com/api/auth/hotel_details"
HOTEL_ID = "41"

CHECKIN_START = datetime(2025, 12, 1)
CHECKIN_END   = datetime(2026, 2, 28)

WATCH_DATES = {"2025-12-21", "2025-12-22", "2025-12-23"}

TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.bookodisha.com",
    "Referer": "https://www.bookodisha.com/",
}

ALERT_LOG = "alert_log.txt"


# ---------------- HELPERS ----------------

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[!] Telegram config missing")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
        print("✅ Alert sent")
    except Exception as e:
        print("❌ Alert error:", e)


def already_alerted(key):
    try:
        with open(ALERT_LOG, "r") as f:
            return key in f.read()
    except:
        return False


def mark_alerted(key):
    with open(ALERT_LOG, "a") as f:
        f.write(key+"\n")


def date_range(start, end):
    while start <= end:
        yield start.strftime("%Y-%m-%d")
        start += timedelta(days=1)


# ---------------- SCRAPER ----------------

def get_availability(date_str):
    next_day = (datetime.strptime(date_str,"%Y-%m-%d")+timedelta(days=1)).strftime("%Y-%m-%d")

    payload = {
        "request_type": "check_room_availability",
        "requested_room": "all",
        "hotelId": HOTEL_ID,
        "roomRequest": '[{"adult":2,"child":0}]',
        "checkinDate": date_str,
        "checkoutDate": next_day
    }

    try:
        r = requests.post(API_URL, data=payload, headers=HEADERS, timeout=15)
        data = r.json()
    except:
        print("API error @", date_str)
        return []

    rooms = data.get("data", [])

    parsed = []

    for room in rooms:
        parsed.append({
            'date': date_str,
            'weekday': datetime.strptime(date_str,"%Y-%m-%d").strftime("%A"),
            'room': room.get("title"),
            'id': room.get("id"),
            'qty': room.get("quantity"),
            'price': room.get("price"),
            'available': room.get("booking_status")
        })

    return parsed


# ---------------- MAIN ----------------

def main():
    print("---- ECO RETREAT WATCH START ----")

    for d in date_range(CHECKIN_START, CHECKIN_END):
        rooms = get_availability(d)

        for r in rooms:

            if r["available"] == 1 and r["date"] in WATCH_DATES:

                alert_key = f"{r['date']}-{r['id']}"

                if already_alerted(alert_key):
                    continue

                msg = (
                    f"🏨 <b>ROOM AVAILABLE</b>\n"
                    f"📅 {r['date']} ({r['weekday']})\n"
                    f"🛏 {r['room']}\n"
                    f"💰 ₹{r['price']}\n"
                    f"📦 Qty: {r['qty']}"
                )

                send_telegram(msg)
                mark_alerted(alert_key)

    print("---- CHECK COMPLETE ----")


if __name__ == "__main__":
    main()
  
