import requests
from datetime import datetime, timedelta

print("=" * 70)
print("RAW NSE HISTORICAL API TEST")
print("=" * 70)

# NIFTY 50 token
token = "26000"

# Last 30 days
end = datetime.now()
start = end - timedelta(days=30)

print(f"Token : {token}")
print(f"Start : {start}")
print(f"End   : {end}")
print()

# ------------------------------------------------------------
# NSE session
# ------------------------------------------------------------

session = requests.Session()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

session.headers.update(headers)

# ------------------------------------------------------------
# Step 1 — NSE homepage
# ------------------------------------------------------------

print("STEP 1: Connecting to NSE homepage...")

try:

    response = session.get(
        "https://www.nseindia.com/",
        timeout=20
    )

    print("HTTP status:", response.status_code)
    print("Response size:", len(response.text))

except Exception as e:

    print("NSE homepage ERROR:")
    print(repr(e))


# ------------------------------------------------------------
# Step 2 — Historical API
# ------------------------------------------------------------

print()
print("=" * 70)
print("STEP 2: NSE HISTORICAL API")
print("=" * 70)

url = (
    "https://www.nseindia.com/api/historical/"
    f"indicesHistory?indexType=NIFTY%2050"
)

print("URL:")
print(url)
print()

try:

    response = session.get(
        url,
        timeout=20
    )

    print("HTTP status:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Response size:", len(response.text))

    print()
    print("First 1000 characters:")
    print(response.text[:1000])

except Exception as e:

    print()
    print("HISTORICAL API ERROR:")
    print(repr(e))


# ------------------------------------------------------------
# FINISH
# ------------------------------------------------------------

print()
print("=" * 70)
print("RAW NSE TEST COMPLETED")
print("=" * 70)
