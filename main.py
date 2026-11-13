
import json, os, math

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]

def clamp(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def forecast_prices(p, horizon, win=120, lam=0.95, tail=0.8, blend=0.15):
    x = p[-1]
    n = len(p)
    diffs = [p[i+1]-p[i] for i in range(max(0, n-win), n-1)] or [0.0]
    s2 = 0.0
    w = 0.0
    for i, d in enumerate(reversed(diffs)):
        a = (1-lam)*lam**i
        s2 += a*d*d
        w += a
    sigma = math.sqrt(s2/w) if w > 0 else 0.0025
    sigma = (1-blend)*sigma + blend*0.0025
    sigma = max(0.0006, min(sigma, 0.03))
    q = []
    for h in range(1, horizon+1):
        spread = sigma*math.sqrt(h)
        q.append([round(clamp(x + z*spread*(tail if abs(z) > 1 else 1)), 6) for z in Z])
    return q

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for fn in sorted(os.listdir(INPUT_DIR)):
        if not fn.endswith(".in"):
            continue
        case = json.load(open(os.path.join(INPUT_DIR, fn)))
        horizon = case["horizon_minutes"]
        out = {"forecasts": [
            {"id": m["id"], "q": forecast_prices(m["prices"], horizon)}
            for m in case["markets"]
        ]}
        with open(os.path.join(OUTPUT_DIR, fn[:-3] + ".out"), "w") as f:
            json.dump(out, f)

main()
