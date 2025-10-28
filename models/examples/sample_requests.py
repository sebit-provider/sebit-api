"""
Utility script to exercise the SEBIT Engine API endpoints with representative payloads.

Usage:
    python -m models.examples.sample_requests

Override the default base URL by setting the SEBIT_API_BASE_URL environment variable,
e.g. `set SEBIT_API_BASE_URL=https://sebit-engine.onrender.com`.
"""

from __future__ import annotations

import json
import os
import textwrap
import urllib.request
from typing import Dict, Iterable, Tuple

BASE_URL = os.getenv("SEBIT_API_BASE_URL", "http://localhost:8000").rstrip("/")


def _print_heading(title: str) -> None:
    bar = "=" * len(title)
    print(f"\n{title}\n{bar}")


def _get(path: str) -> Tuple[int, str]:
    with urllib.request.urlopen(f"{BASE_URL}{path}") as response:  # type: ignore[no-untyped-call]
        return response.status, response.read().decode("utf-8")


def _post(path: str, payload: Dict) -> Tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:  # type: ignore[no-untyped-call]
        return response.status, response.read().decode("utf-8")


def _summarise(body: str, limit: int = 400) -> str:
    snippet = body if len(body) <= limit else f"{body[:limit]}…"
    return textwrap.indent(snippet, prefix="  ")


def run_health_check() -> None:
    _print_heading("GET /health")
    status, body = _get("/health")
    print(f"Status: {status}")
    print("Response:\n" + _summarise(body))


def run_samples(samples: Iterable[Tuple[str, Dict]]) -> None:
    for path, payload in samples:
        _print_heading(f"POST {path}")
        status, body = _post(path, payload)
        print(f"Status: {status}")
        print("Payload:")
        print(_summarise(json.dumps(payload, indent=2)))
        print("Response:\n" + _summarise(body))


def main() -> None:
    run_health_check()

    asset_samples = [
        (
            "/asset/dda",
            {
                "asset_label": "facility-line-1",
                "acquisition_cost": 250000.0,
                "salvage_value": 15000.0,
                "useful_life_years": 4,
                "planned_usage_days_per_year": [365, 365, 365, 365],
                "actual_usage_days_per_year": [358, 370, 362, 355],
                "market_price_series": [250000.0, 244000.0, 239500.0, 233000.0, 228500.0],
                "beta": 1.08,
                "adjustment_factor": 1.0,
            },
        ),
        (
            "/asset/lam",
            {
                "lease_label": "hq-lease",
                "initial_asset_value": 180000.0,
                "lease_term_years": 3,
                "discount_rate": 0.045,
                "planned_usage_days_per_period": [365, 365, 365],
                "actual_usage_days_per_period": [360, 354, 348],
                "unused_days_per_period": [8, 6, 12],
                "actual_daily_usage_hours": [9.0, 8.5, 7.8],
                "standard_daily_usage_hours": [8.0, 8.0, 8.0],
                "market_fair_values": [180000.0, 176500.0, 172800.0, 168900.0],
                "ifrs_revaluation_losses": [2500.0, 2200.0, 2600.0],
                "beta": 1.05,
            },
        ),
        (
            "/asset/rvm",
            {
                "resource_label": "mine-alpha",
                "cumulative_extraction_amount": 44000.0,
                "cumulative_extraction_days": 240.0,
                "current_unit_extraction_value": 36.5,
                "previous_extraction_value": 1450000.0,
                "total_years_of_useful_life": 12.0,
                "elapsed_years": 4.5,
                "beta": 1.02,
            },
        ),
    ]

    expense_samples = [
        (
            "/expense/ceem",
            {
                "expense_label": "chemicals",
                "cumulative_usage_units": 1250.0,
                "cumulative_usage_days": 210.0,
                "current_unit_cost": 18.75,
                "previous_year_standard_usage_value": 36000.0,
                "useful_life_years": 2.0,
                "elapsed_years": 0.75,
                "beta": 1.1,
            },
        ),
        (
            "/expense/bdm",
            {
                "bond_label": "corp-bond-2025",
                "bond_issue_price": 500000.0,
                "bond_contract_days": 1825.0,
                "elapsed_days_since_contract": 730.0,
                "previous_valuation": 470000.0,
                "current_fair_value": 485000.0,
            },
        ),
        (
            "/expense/belm",
            {
                "debtor_label": "customer-x",
                "debtor_total_amount": 90000.0,
                "remaining_years": 3.0,
                "elapsed_days": 220.0,
                "actual_repayment_amount": 5500.0,
                "interest_rate": 0.055,
                "total_debt_balance_all_counterparties": 420000.0,
                "last_year_counterparty_repayment": 12000.0,
                "last_year_total_repayment_all": 95000.0,
            },
        ),
    ]

    risk_samples = [
        (
            "/risk/cprm",
            {
                "exposure_id": "cb-risk",
                "allowance_for_bad_debts": 18000.0,
                "total_bond_related_assets": 420000.0,
                "bad_debt_amount": 15000.0,
                "transaction_value_per_bond_unit": 950.0,
                "total_convertible_bond_transaction_value": 380000.0,
                "stock_purchase_transaction_value": 260000.0,
                "stock_sale_transaction_value": 235000.0,
                "total_scope_bonds_for_conversion": 9000.0,
                "current_debt_repayments": 64000.0,
                "number_of_debt_repayments": 6,
                "total_convertible_bond_purchases": 410000.0,
                "total_convertible_bond_sales": 395000.0,
                "total_number_purchase_transactions": 4,
                "total_number_sale_transactions": 3,
                "total_bond_transactions_value": 805000.0,
                "total_stock_transaction_value": 720000.0,
                "value_of_convertible_bond_products": 120000.0,
                "rate_trigger_threshold": 0.08,
            },
        ),
        (
            "/risk/c-ocim",
            {
                "portfolio_label": "oci-bucket-a",
                "oci_account_balance": 250000.0,
                "total_oci_amount": 875000.0,
                "policy_rate": 0.0275,
                "useful_life_years_remaining": 6.0,
                "initial_recognition_amount": 200000.0,
                "year_end_balance": 265000.0,
                "quarterly_data": [
                    {
                        "quarter_index": 1,
                        "pre_compound_balance": 215000.0,
                        "post_compound_balance": 218500.0,
                        "current_quarter_yield": 0.018,
                        "previous_quarter_yield": 0.016,
                        "previous_quarter_rate": 0.012,
                        "current_quarter_rate": 0.013,
                    },
                    {
                        "quarter_index": 2,
                        "pre_compound_balance": 220500.0,
                        "post_compound_balance": 224800.0,
                        "current_quarter_yield": 0.019,
                        "previous_quarter_yield": 0.018,
                        "previous_quarter_rate": 0.013,
                        "current_quarter_rate": 0.014,
                    },
                ],
            },
        ),
        (
            "/risk/farex",
            {
                "contract_id": "fx-hedge-1",
                "base_currency_amount": 750000.0,
                "spot_rate": 1312.5,
                "forecast_rate": 1355.0,
                "inflation_rate_home": 0.018,
                "inflation_rate_foreign": 0.024,
                "hedge_ratio": 0.85,
                "last_year_prev_month_export": 980000.0,
                "last_year_prev_month_import": 840000.0,
                "last_year_current_month_export": 1025000.0,
                "last_year_current_month_import": 865000.0,
                "current_year_prev_month_export": 1080000.0,
                "current_year_prev_month_import": 890000.0,
            },
        ),
    ]

    run_samples(asset_samples + expense_samples + risk_samples)


if __name__ == "__main__":
    main()
