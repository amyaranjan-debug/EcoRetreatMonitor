import requests
from datetime import datetime, timedelta
import os

# =====================================================
# ECO RETREAT MULTI-HOTEL AVAILABILITY MONITOR
# =====================================================

# ---------------------- CONFIG -----------------------

API_URL = "https://admin.bookodisha.com/api/auth/hotel_details"

# Monitor all hotels
HOTEL_IDS = ["41", "37", "43"]

# HOTEL ID → LOCATION MAPPING
HOTEL_MAP = {
    "37": "Konark",
    "41": "Satkosia",
    "43": "Sonapur",
}

CHECKIN_START = datetime(2025, 12, 19)
CHECKIN_END   = datetime(2025, 12, 24)

WATCH_DATES = {
    "2025-12-20",
    "2025-12-21",
    "2025-12-22",
    "2025-12-23"
}

TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.bookodisha.com",
    "Referer": "https://www.bookodisha.com/",
}

ALERT_LOG = "alert_log.txt"

# =====================================================
# TELEGRAM
# =====================================================

def send_telegram(msg):

    print("[TG] sending message...")

    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[ERROR] TELEGRAM ENV VAR missing")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            },
            timeout=10,
        )
        print("[TG] ✅ sent")
    except Exception as e:
        print("[TG] ❌ failed:", e)

# =====================================================
# ALERT MEMORY
# =====================================================

def already_alerted(key):
    try:
        with open(ALERT_LOG, "r") as f:
            return key in f.read()
    except:
        return False


def mark_alerted(key):
    with open(ALERT_LOG, "a") as f:
        f.write(key + "\n")

# =====================================================
# DATE GENERATOR
# =====================================================

def date_range(start, end):
    while start <= end:
        yield start.strftime("%Y-%m-%d")
        start += timedelta(days=1)

# =====================================================
# API SCRAPER
# =====================================================

def get_availability(hotel_id, date_str):

    next_day = (
        datetime.strptime(date_str, "%Y-%m-%d") +
        timedelta(days=1)
    ).strftime("%Y-%m-%d")

    payload = {
        "request_type": "check_room_availability",
        "requested_room": "all",
        "hotelId": hotel_id,
        "roomRequest": '[{"adult":2,"child":0}]',
        "checkinDate": date_str,
        "checkoutDate": next_day,
    }

    try:
        r = requests.post(
            API_URL, payload,
            headers=HEADERS,
            timeout=15
        )
        data = r.json()
    except Exception as e:
        print("[API ERROR]", hotel_id, date_str, e)
        return []

    rooms = data.get("data", [])
    parsed = []

    for room in rooms:
        parsed.append({
            "hotel": hotel_id,
            "date": date_str,
            "weekday": datetime.strptime(date_str, "%Y-%m-%d").strftime("%A"),
            "room": room.get("title"),
            "room_id": room.get("id"),
            "qty": room.get("quantity"),
            "price": room.get("price"),
            "available": room.get("booking_status"),
        })

    return parsed

# =====================================================
# MAIN
# =====================================================

def main():

    # ✅ TEST STARTUP MESSAGE
    send_telegram(
        "✅ <b>Eco Retreat Monitor is ACTIVE</b>\n"
        "Monitoring Konark, Satkosia and Sonapur."
    )

    print("\n==== ECO RETREAT WATCH RUNNING ====\n")

    for hotel in HOTEL_IDS:

        location = HOTEL_MAP.get(hotel, "Unknown")

        print(f"--- HOTEL {hotel} → {location} ---")

        for d in date_range(CHECKIN_START, CHECKIN_END):

            rooms = get_availability(hotel, d)

            for r in rooms:

                if r["available"] == 1 and r["date"] in WATCH_DATES:

                    key = f"{hotel}-{r['date']}-{r['room_id']}"

                    if already_alerted(key):
                        continue

                    msg = (
                        f"🏨 <b>ROOM AVAILABLE</b>\n"
                        f"📍 <b>Location:</b> {location}\n"
                        f"🏷 Hotel ID: {hotel}\n"
                        f"📅 {r['date']} ({r['weekday']})\n"
                        f"🛏 {r['room']}\n"
                        f"💰 ₹{r['price']}\n"
                        f"📦 Qty: {r['qty']}"
                    )

                    send_telegram(msg)
                    mark_alerted(key)

    print("\n==== RUN COMPLETE ====\n")


if __name__ == "__main__":
    main()
