import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta


print("=" * 70)
print("NSE NIFTY 50 DAILY SNAPSHOT TEST")
print("=" * 70)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_DAYS_BACK = 15

BASE_URL = (
    "https://nsearchives.nseindia.com/"
    "content/indices/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


# ============================================================
# CREATE SESSION
# ============================================================

session = requests.Session()

session.headers.update(HEADERS)


# ============================================================
# START DATE SEARCH
# ============================================================

today = datetime.now()

print()
print("Today:")
print(today.strftime("%d-%m-%Y"))

print()
print(
    f"Searching for the latest available NSE "
    f"Daily Snapshot over the last {MAX_DAYS_BACK} days..."
)


# ============================================================
# SEARCH BACKWARDS
# ============================================================

found_data = None
found_date = None
found_url = None


for days_back in range(MAX_DAYS_BACK + 1):

    check_date = today - timedelta(days=days_back)

    date_string = check_date.strftime("%d%m%Y")

    filename = (
        f"ind_close_all_{date_string}.csv"
    )

    url = BASE_URL + filename

    print()
    print("-" * 70)

    print(
        f"Checking {check_date.strftime('%d-%m-%Y')}"
    )

    print(
        f"File: {filename}"
    )

    print(
        f"URL: {url}"
    )

    try:

        response = session.get(
            url,
            timeout=30
        )

        print(
            f"HTTP status: {response.status_code}"
        )

        print(
            f"Response size: {len(response.content)}"
        )

    except Exception as e:

        print(
            "REQUEST ERROR:"
        )

        print(
            repr(e)
        )

        continue


    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    if response.status_code == 404:

        print(
            "Archive does not exist for this date."
        )

        continue


    # --------------------------------------------------------
    # OTHER HTTP ERROR
    # --------------------------------------------------------

    if response.status_code != 200:

        print(
            "Unexpected HTTP status."
        )

        continue


    # --------------------------------------------------------
    # TRY CSV
    # --------------------------------------------------------

    try:

        data = pd.read_csv(
            StringIO(response.text)
        )

    except Exception as e:

        print(
            "CSV parsing failed:"
        )

        print(
            repr(e)
        )

        continue


    # --------------------------------------------------------
    # VALIDATE CSV
    # --------------------------------------------------------

    if data.empty:

        print(
            "CSV exists but contains zero rows."
        )

        continue


    print()
    print(
        "VALID CSV FOUND!"
    )

    print(
        f"Rows: {len(data)}"
    )

    print(
        f"Columns: {list(data.columns)}"
    )


    found_data = data
    found_date = check_date
    found_url = url

    break


# ============================================================
# NO FILE FOUND
# ============================================================

if found_data is None:

    print()
    print("=" * 70)
    print("ERROR")
    print("=" * 70)

    print()
    print(
        f"No NSE Daily Snapshot was found "
        f"within {MAX_DAYS_BACK} days."
    )

    raise SystemExit(1)


# ============================================================
# DISPLAY FOUND FILE
# ============================================================

data = found_data


print()
print("=" * 70)
print("LATEST AVAILABLE NSE DAILY SNAPSHOT")
print("=" * 70)

print()

print(
    "Archive date:"
)

print(
    found_date.strftime("%d-%m-%Y")
)

print()

print(
    "Archive URL:"
)

print(
    found_url
)


# ============================================================
# DISPLAY COLUMNS
# ============================================================

print()
print("=" * 70)
print("COLUMNS")
print("=" * 70)

print()

for column in data.columns:

    print(
        column
    )


# ============================================================
# DISPLAY FIRST ROWS
# ============================================================

print()
print("=" * 70)
print("FIRST 10 ROWS")
print("=" * 70)

print()

print(
    data.head(10).to_string(index=False)
)


# ============================================================
# SEARCH FOR NIFTY 50
# ============================================================

print()
print("=" * 70)
print("SEARCHING FOR NIFTY 50")
print("=" * 70)

print()


try:

    nifty_rows = data[
        data.astype(str)
        .apply(
            lambda row:
            row.str.contains(
                "NIFTY 50",
                case=False,
                na=False
            ).any(),
            axis=1
        )
    ]

except Exception as e:

    print(
        "Error searching for NIFTY 50:"
    )

    print(
        repr(e)
    )

    raise


# ============================================================
# NIFTY RESULT
# ============================================================

print()

if nifty_rows.empty:

    print(
        "NIFTY 50 was NOT found."
    )

    print()
    print(
        "Complete dataset preview:"
    )

    print(
        data.to_string(index=False)
    )

    raise SystemExit(1)


print(
    "NIFTY 50 FOUND!"
)

print()

print(
    nifty_rows.to_string(index=False)
)


# ============================================================
# SUCCESS
# ============================================================

print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print()

print(
    "GitHub Actions successfully:"
)

print(
    "1. Connected to NSE archive infrastructure"
)

print(
    "2. Found an available Daily Snapshot"
)

print(
    "3. Downloaded the CSV"
)

print(
    "4. Parsed the CSV"
)

print(
    "5. Found NIFTY 50"
)

print()
print(
    "NIFTY archive test completed successfully."
)

print()
print("=" * 70)
