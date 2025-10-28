# SEBIT Engine API (MVP)

FastAPI implementation of the SEBIT Engine models, focused on the first two series highlighted in the technical specification.

## Implemented scope

- **Asset & Depreciation series**
  - `POST /asset/dda` - Dynamic Depreciation Algorithm (SEBIT-DDA)
  - `POST /asset/lam` - Lease Amortisation Model (SEBIT-LAM)
  - `POST /asset/rvm` - Resource Valuation Model (SEBIT-RVM)
- **Expense & Profit series**
  - `POST /expense/ceem` - Consumable Expense Evaluation Model (SEBIT-CEEM)
  - `POST /expense/bdm` - Bond Depreciation Model (SEBIT-BDM)
  - `POST /expense/belm` - Bad debt Expected Loss Model (SEBIT-BELM)
- **Risk & Comprehensive income series**
  - `POST /risk/cprm` - Collateral-adjusted Probabilistic Risk Model (SEBIT-CPRM)
  - `POST /risk/c-ocim` - Compound Other Comprehensive Income Model (SEBIT-C-OCIM)
  - `POST /risk/farex` - Foreign Adjustment & Real Exchange Model (SEBIT-FAREX)

Each endpoint accepts structured JSON payloads derived from the v1.0 specification and returns typed responses ready for integration.

### Asset-model parameter highlights

- **DDA** supports usage calendars and market price series. The service follows the published sequence (usage variance -> market log shock -> CAPM beta) before applying IFRS-aligned caps.
- **RVM** evaluates cumulative extraction metrics: it derives daily averages, standard vs. actual extraction values, extraction rates, market change index/log terms, and the final resource revaluation figure described in SEBIT-RVM.
- **LAM** ingests per-period usage calendars, usage hours, and fair value series, computing daily lease amortisation, usage ratios, and the revaluation triggers (6-1 ~ 6-3-1) outlined in the spec.

### Expense-model parameter highlights

- **CEEM** captures daily usage, chooses standard values dynamically, logs change vs. prior period, and applies market sensitivity to return the SEBIT-CEEM consumable revaluation.
- **BDM** tracks daily bond usage, computes P_s, market beta, final book value, and classifies discount/premium interest per SEBIT-BDM.
- **BELM** covers debt repayment projections, interest adjustments, and final bad-debt ratio calculations as defined in SEBIT-BELM.

### Risk-model parameter highlights

- **CPRM** models collateral-adjusted convertible bond risk; it calculates assumed bad-debt rates, convertible bond rate, multi-stage adjustments, and trigger logic per SEBIT-CPRM.
- **C-OCIM** compounds OCI balances using account ratios, policy-rate discounting, quarterly adjustments, and growth triggers as defined by SEBIT-C-OCIM.
- **FAREX** blends year-over-year trade ratios, export/import beta, inflation spreads, and threshold-based rate adjustments to produce the SEBIT-FAREX exchange revaluation.

## Render deployment (free tier)

1. Fork or push this repository to GitHub.
2. Ensure the included `render.yaml` is in the repo root (Render scans it automatically).
3. In Render:
   - Create a new Web Service and choose **Use render.yaml** when prompted (or let Render detect it automatically).
   - Point to your GitHub repo, keep the free plan.
4. Render installs dependencies with `pip install -r requirements.txt` and starts the app via  
   `uvicorn models.app.main:app --host 0.0.0.0 --port $PORT`.
5. Once the build finishes, the FastAPI docs are available at `https://<service-name>.onrender.com/docs`.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs become available at `http://localhost:8000/docs`.

## Sample requests

Use the bundled helper to exercise every endpoint with representative payloads:

```bash
python -m models.examples.sample_requests
```

Set `SEBIT_API_BASE_URL` to point at your Render deployment if you want to call the hosted service instead of a local server.

## Next steps

- Extend remaining SEBIT model families using the same service/route structure.
- Calibrate the demand/market inputs to authoritative datasets and wire in IFRS fallback decision trees.
- Add validation datasets and automated regression tests once the reference calculations are finalised.
