import requests
from datetime import datetime, timedelta

print("=" * 70)
print("RAW NSE NIFTY 50 HISTORICAL API TEST")
print("=" * 70)

end = datetime.now()
start = end - timedelta(days=30)

from_date = start.strftime("%d-%m-%Y")
to_date = end.strftime("%d-%m-%Y")

print(f"Index     : NIFTY 50")
print(f"From date : {from_date}")
print(f"To date   : {to_date}")
print()

# ============================================================
# NSE SESSION
# ============================================================

session = requests.Session()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json, text/plain, */*"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

session.headers.update(headers)


# ============================================================
# TEST 1 — NSE HOMEPAGE
# ============================================================

print("=" * 70)
print("TEST 1: NSE HOMEPAGE")
print("=" * 70)

try:

    response = session.get(
        "https://www.nseindia.com/",
        timeout=20
    )

    print("HTTP status :", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Response size:", len(response.content))

    print()
    print("Cookies received:")

    for cookie in session.cookies:
        print(
            f"  {cookie.name} = "
            f"{cookie.value[:20]}..."
        )

except Exception as e:

    print("ERROR:")
    print(repr(e))


# ============================================================
# TEST 2 — NSE INDEX HISTORY
# ============================================================

print()
print("=" * 70)
print("TEST 2: NSE INDEX HISTORY")
print("=" * 70)

url = "https://www.nseindia.com/api/historical/indicesHistory"

params = {
    "indexType": "NIFTY 50",
    "fromDate": from_date,
    "toDate": to_date,
}

print("URL:")
print(url)

print()
print("Parameters:")
print(params)

print()

try:

    response = session.get(
        url,
        params=params,
        timeout=20
    )

    print("Final URL:")
    print(response.url)

    print()
    print("HTTP status :", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Response size:", len(response.content))

    print()
    print("Response preview:")
    print("-" * 70)
    print(response.text[:3000])
    print("-" * 70)

    if response.status_code == 200:

        try:

            json_data = response.json()

            print()
            print("JSON successfully parsed.")

            print()
            print("JSON type:")
            print(type(json_data))

            if isinstance(json_data, dict):

                print()
                print("JSON keys:")
                print(list(json_data.keys()))

                if "data" in json_data:

                    print()
                    print(
                        "Number of records:",
                        len(json_data["data"])
                    )

                    if json_data["data"]:

                        print()
                        print("First record:")
                        print(json_data["data"][0])

                        print()
                        print("Last record:")
                        print(json_data["data"][-1])

        except Exception as e:

            print()
            print("JSON parsing failed:")
            print(repr(e))


except Exception as e:

    print()
    print("HISTORICAL API ERROR:")
    print(repr(e))


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 70)
print("RAW NSE TEST COMPLETED")
print("=" * 70)
