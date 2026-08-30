from openchart import NSEData
from datetime import datetime, timedelta

print("=" * 60)
print("OPENCHART NIFTY TEST")
print("=" * 60)

end = datetime.now()
start = end - timedelta(days=30)

print(f"Start: {start}")
print(f"End  : {end}")
print()

nse = NSEData()

# TEST 1
print("TEST 1: Searching NIFTY...")

try:
    result = nse.search("NIFTY", "IDX")

    print(result)

    if result is None or result.empty:
        print("ERROR: Search returned no symbols.")
    else:
        print("NIFTY search SUCCESS")

except Exception as e:
    print("Search ERROR:")
    print(repr(e))


# TEST 2
print()
print("TEST 2: Historical NIFTY 50...")

try:

    data = nse.historical(
        "NIFTY 50",
        "IDX",
        start,
        end,
        "1d"
    )

    if data is None or data.empty:
        print("Historical returned ZERO rows.")
    else:
        print()
        print("SUCCESS!")
        print(f"Rows: {len(data)}")
        print(data.tail())

except Exception as e:
    print("Historical ERROR:")
    print(repr(e))


# TEST 3
print()
print("TEST 3: historical_direct()...")

try:

    data_direct = nse.historical_direct(
        token="26000",
        symbol="NIFTY 50",
        symbol_type="Index",
        start=start,
        end=end,
        interval="1d"
    )

    if data_direct is None or data_direct.empty:
        print("historical_direct returned ZERO rows.")
    else:
        print()
        print("DIRECT SUCCESS!")
        print(f"Rows: {len(data_direct)}")
        print(data_direct.tail())

except Exception as e:
    print("Direct ERROR:")
    print(repr(e))


print()
print("=" * 60)
print("TEST COMPLETED")
print("=" * 60)
