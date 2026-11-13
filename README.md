# EWMA vol quantile forecaster — polymarket-nvidia-ceo-forecast-01

## What it does

`main.py` reads every `*.in` file in `$MAKEFUN_INPUT_DIR` (default `/input`). Each
file is one case: `{"at", "horizon_minutes", "markets": [{"id", "prices": [...]}]}`.
For every market it emits `horizon_minutes` rows (h = 1..horizon) of 5 quantile
predictions at levels [0.05, 0.25, 0.5, 0.75, 0.95], written as
`{"forecasts": [{"id", "q": [[5 floats] x horizon]}]}` to
`$MAKEFUN_OUTPUT_DIR/<case>.out`.

## Method

1. Current price `x = prices[-1]`.
2. Take minute-to-minute diffs over the last 120 minutes.
3. EWMA variance with decay lambda = 0.95: weights `w_i = (1-lambda) * lambda**i`
   over the reversed diffs (most recent diff gets the largest weight).
4. `sigma = sqrt(EWMA variance)`, blended 15% toward a 0.0025 floor to keep the
   tails sane when realized vol collapses, then clamped to [0.0006, 0.03].
5. Row at horizon h: median `= x`, spread `= sigma * sqrt(h)` (diffusion scaling).
   Quantile q at level z is `x + z * spread`, with a 0.8 shrink factor applied to
   the outer tails (|z| > 1) since empirical price moves are thinner-tailed than
   Gaussian in this market. Z values are the exact normal quantiles of the five
   levels. Every value is rounded to 6 decimals and clamped to [0, 1].

## Backtest

Hold-out validation on the 6 practice cases (last 120 minutes of each market
held out; the model is fit on the first 120 minutes only):

| horizon | ours | house baseline | improvement |
|---------|------|----------------|-------------|
| 120 min | 0.177 | 0.249 | -29% |
| 240 min | 0.181 | 0.189 | -4% |

House baseline = flat median at the last price with `0.0025 * sqrt(h)` spreads.
Pinball loss averaged over the 5 quantile levels.

## Files

- `main.py` — the forecaster (Python 3.13, stdlib only).
- `LICENSE` — MIT.

## Running

```
MAKEFUN_INPUT_DIR=<dir with *.in> MAKEFUN_OUTPUT_DIR=<out dir> python3 main.py
```
