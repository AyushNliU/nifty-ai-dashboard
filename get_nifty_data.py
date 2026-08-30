from openchart import NSEData
from datetime import datetime, timedelta
import sys


# ============================================================
# CONFIGURATION
# ============================================================

NIFTY_TOKEN = "26000"

DAYS_BACK = 30


# ============================================================
# START
# ============================================================

print("=" * 60)
print("OPENCHART NIFTY 50 DIAGNOSTIC TEST")
print("=" * 60)

end = datetime.now()
start = end - timedelta(days=DAYS_BACK)

print()
print(f"Start date : {start}")
print(f"End date   : {end}")
print(f"Token      : {NIFTY_TOKEN}")
print(f"Interval   : 1d")
print()


# ============================================================
# CREATE NSE CONNECTION
# ============================================================

print("Creating NSEData connection...")

try:

    nse = NSEData()

    print("NSEData connection created successfully.")

except Exception as e:

    print()
    print("ERROR creating NSEData:")
    print(repr(e))

    sys.exit(1)


# ============================================================
# TEST 1 — SEARCH NIFTY
# ============================================================

print()
print("=" * 60)
print("TEST 1: SEARCH NIFTY")
print("=" * 60)

try:

    print("Searching for NIFTY...")

    result = nse.search(
        "NIFTY",
        "IDX"
    )

    print()
    print("Search response:")

    print(result)

    if result is None:

        print()
        print("RESULT: Search returned None.")

    elif result.empty:

        print()
        print("RESULT: Search returned ZERO rows.")

    else:

        print()
        print("RESULT: NIFTY search SUCCESS")
        print(f"Rows returned: {len(result)}")

except Exception as e:

    print()
    print("SEARCH ERROR:")
    print(repr(e))


# ============================================================
# TEST 2 — NORMAL HISTORICAL METHOD
# ============================================================

print()
print("=" * 60)
print("TEST 2: nse.historical()")
print("=" * 60)

try:

    print("Requesting NIFTY 50 historical data...")

    data = nse.historical(
        "NIFTY 50",
        "IDX",
        start,
        end,
        "1d"
    )

    print()
    print("Historical response:")

    if data is None:

        print("None")

        print()
        print("RESULT: historical() returned None.")

    elif data.empty:

        print(data)

        print()
        print("RESULT: historical() returned ZERO rows.")

    else:

        print(data)

        print()
        print("RESULT: historical() SUCCESS")
        print(f"Rows returned: {len(data)}")

        print()
        print("Last 5 rows:")

        print(data.tail())


except Exception as e:

    print()
    print("HISTORICAL ERROR:")
    print(repr(e))


# ============================================================
# TEST 3 — DIRECT TOKEN METHOD
# ============================================================

print()
print("=" * 60)
print("TEST 3: nse.historical_direct()")
print("=" * 60)

try:

    print("Requesting NIFTY 50 using token 26000...")

    data_direct = nse.historical_direct(
        token=NIFTY_TOKEN,
        symbol="NIFTY 50",
        symbol_type="Index",
        start=start,
        end=end,
        interval="1d"
    )

    print()
    print("Direct historical response:")

    if data_direct is None:

        print("None")

        print()
        print(
            "RESULT: historical_direct() "
            "returned None."
        )

    elif data_direct.empty:

        print(data_direct)

        print()
        print(
            "RESULT: historical_direct() "
            "returned ZERO rows."
        )

    else:

        print(data_direct)

        print()
        print(
            "RESULT: historical_direct() SUCCESS"
        )

        print(
            f"Rows returned: {len(data_direct)}"
        )

        print()
        print("Last 5 rows:")

        print(data_direct.tail())


except Exception as e:

    print()
    print("DIRECT HISTORICAL ERROR:")
    print(repr(e))


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 60)
print("DIAGNOSTIC TEST COMPLETED")
print("=" * 60)
