# Refined classification logic
def classify_market(bull, bear, sideways):
    if bull > 24 and bear < 12:
        return "bull"
    elif bear > 15 and bear > bull:
        return "bear"
    elif sideways > 65:
        return "sideways"
    else:
        return "sideways"

# Regime data per token per period
regimes = {
    "Q4_2023": {
        "BTC": {"bull": 25.41, "bear": 10.87, "sideways": 63.72},
        "ETH": {"bull": 20.29, "bear": 12.45, "sideways": 67.26},
        "SOL": {"bull": 25.77, "bear": 7.02,  "sideways": 67.21},
    },
    "Aug_Sep_2023": {
        "BTC": {"bull": 9.97,  "bear": 14.82, "sideways": 75.20},
        "ETH": {"bull": 9.36,  "bear": 16.39, "sideways": 74.25},
        "SOL": {"bull": 12.09, "bear": 21.45, "sideways": 66.46},
    },
    "Jan_Feb_2024": {
        "BTC": {"bull": 24.10, "bear": 7.92,  "sideways": 67.99},
        "ETH": {"bull": 23.82, "bear": 7.15,  "sideways": 69.03},
        "SOL": {"bull": 16.53, "bear": 11.04, "sideways": 72.43},
    },
}

# Classify each period based on majority vote
for period, assets in regimes.items():
    results = []
    for asset, values in assets.items():
        regime = classify_market(**values)
        results.append(regime)
    # Determine final regime by majority
    final = max(set(results), key=results.count)
    print(f"{period}: {final.upper()} ({results})")
