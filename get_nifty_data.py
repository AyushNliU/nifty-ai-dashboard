\from nsedata import nse

print("=" * 60)
print("NIFTY 50 ALTERNATIVE DATA SOURCE TEST")
print("=" * 60)

try:

    print("Requesting NIFTY 50 historical data...")

    data = nse.get_historical_index(
        "NIFTY 50",
        "01-Aug-2026",
        "31-Aug-2026"
    )

    print()
    print("Response:")
    print(data)

    if data is None or data.empty:

        print()
        print("ERROR: No NIFTY data received.")

    else:

        print()
        print("SUCCESS!")
        print(f"Rows received: {len(data)}")

        print()
        print("Last 5 rows:")
        print(data.tail())

except Exception as e:

    print()
    print("ERROR:")
    print(repr(e))
