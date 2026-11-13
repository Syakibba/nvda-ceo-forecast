"""EWMA volatility quantile forecaster.

Reads every *.in case in $MAKEFUN_INPUT_DIR (JSON: {"at", "horizon_minutes",
"markets": [{"id", "prices": [...]}]}). For each market, forecasts 5 quantiles
[0.05, 0.25, 0.5, 0.75, 0.95] of the price at each minute h = 1..horizon and
writes one JSON {"forecasts": [{"id", "q": [[5 floats] x horizon]}]} per case
to $MAKEFUN_OUTPUT_DIR/<case>.out.

Method: EWMA variance (lambda=0.95) over the last 120 minutes of price diffs,
sigma blended 15% toward a 0.0025 floor and clamped to [0.0006, 0.03]; median
pinned at the last price, spreads sigma*sqrt(h), outer tails (|z|>1) shrunk
0.8x. Python 3.13, stdlib only.
"""

import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# Normal quantiles of the 5 forecast levels [0.05, 0.25, 0.5, 0.75, 0.95].
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]

WINDOW = 120        # minutes of diffs used for the EWMA variance
LAMBDA = 0.95       # EWMA decay
FLOOR = 0.0025      # baseline sigma the estimate blends toward
BLEND = 0.15        # weight of the floor in the blend
SIGMA_MIN = 0.0006
SIGMA_MAX = 0.03
TAIL_SHRINK = 0.8   # applied to outer quantiles (|z| > 1)


def clamp01(x):
    """Clamp a price to the [0, 1] range of the market."""
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ewma_sigma(prices, window=WINDOW, lam=LAMBDA, blend=BLEND, floor=FLOOR):
    """EWMA standard deviation of minute diffs over the trailing window.

    Only diffs between consecutive observations count; missing minutes simply
    shorten the effective window rather than being treated as zero moves.
    """
    diffs = [prices[i + 1] - prices[i] for i in range(max(0, len(prices) - window), len(prices) - 1)]
    if not diffs:
        diffs = [0.0]
    var = 0.0
    wsum = 0.0
    for i, d in enumerate(reversed(diffs)):
        w = (1 - lam) * lam ** i
        var += w * d * d
        wsum += w
    sigma = math.sqrt(var / wsum) if wsum > 0 else floor
    # Blend partway to the floor so a quiet stretch does not collapse the bands.
    sigma = (1 - blend) * sigma + blend * floor
    return max(SIGMA_MIN, min(sigma, SIGMA_MAX))


def forecast_market(prices, horizon):
    """Return the horizon x 5 quantile matrix for one market's price path."""
    x = prices[-1]
    sigma = ewma_sigma(prices)
    rows = []
    for h in range(1, horizon + 1):
        spread = sigma * math.sqrt(h)
        rows.append([
            round(clamp01(x + z * spread * (TAIL_SHRINK if abs(z) > 1 else 1)), 6)
            for z in Z
        ])
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for fname in sorted(os.listdir(INPUT_DIR)):
        if not fname.endswith(".in"):
            continue
        with open(os.path.join(INPUT_DIR, fname)) as f:
            case = json.load(f)
        horizon = case["horizon_minutes"]
        out = {
            "forecasts": [
                {"id": m["id"], "q": forecast_market(m["prices"], horizon)}
                for m in case["markets"]
            ]
        }
        out_name = fname[:-3] + ".out"
        with open(os.path.join(OUTPUT_DIR, out_name), "w") as f:
            json.dump(out, f)


if __name__ == "__main__":
    main()
