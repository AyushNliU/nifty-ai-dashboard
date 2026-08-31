import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta


print("=" * 70)
print("NSE NIFTY 50 ARCHIVE TEST")
print("=" * 70)


# ------------------------------------------------------------
# DATE
# ------------------------------------------------------------

date = datetime.now()

date_string = date.strftime("%d%m%Y")

url = (
    "https://nsearchives.nseindia.com/"
    "content/indices/"
    f"ind_close_all_{date_string}.csv"
)

print()
print("Date:", date.strftime("%d-%m-%Y"))
print("URL:")
print(url)
print()


# ------------------------------------------------------------
# REQUEST
# ------------------------------------------------------------

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/",
}


try:

    print("Downloading NSE archive...")

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print()
    print("HTTP status:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Response size:", len(response.content))

    print()


    if response.status_code != 200:

        print("ERROR: Archive request failed.")

        print()
        print("Response:")
        print(response.text[:1000])

        raise SystemExit(1)


    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    print("Reading CSV...")

    data = pd.read_csv(
        StringIO(response.text)
    )


    print()
    print("SUCCESS!")
    print("Columns:")
    print(list(data.columns))

    print()
    print("Rows:")
    print(len(data))

    print()
    print("First 5 rows:")
    print(data.head())


    # --------------------------------------------------------
    # FIND NIFTY 50
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SEARCHING FOR NIFTY 50")
    print("=" * 70)


    print()

    print(data[
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
    ])


except Exception as e:

    print()
    print("=" * 70)
    print("ERROR")
    print("=" * 70)

    print(repr(e))

    raise
