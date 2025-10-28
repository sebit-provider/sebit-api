from fastapi.testclient import TestClient

try:  # pragma: no cover - compatibility for local vs packaged imports
    from models.app.main import create_app
except ModuleNotFoundError:  # pragma: no cover
    from app.main import create_app


client = TestClient(create_app())


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_asset_dda_endpoint():
    payload = {
        "asset_label": "asset-1",
        "acquisition_cost": 100000.0,
        "salvage_value": 5000.0,
        "useful_life_years": 3,
        "planned_usage_days_per_year": [365, 365, 365],
        "actual_usage_days_per_year": [360, 370, 355],
        "market_price_series": [100000.0, 98000.0, 96000.0, 94000.0],
        "beta": 1.05,
        "adjustment_factor": 1.0,
    }

    response = client.post("/asset/dda", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["asset_label"] == "asset-1"
    assert len(data["schedule"]) > 0
    assert data["total_depreciation"] > 0


def test_asset_lam_endpoint():
    payload = {
        "lease_label": "lease-1",
        "initial_asset_value": 60000.0,
        "lease_term_years": 2,
        "discount_rate": 0.04,
        "planned_usage_days_per_period": [365, 365],
        "actual_usage_days_per_period": [360, 350],
        "unused_days_per_period": [5, 10],
        "actual_daily_usage_hours": [8.0, 7.5],
        "standard_daily_usage_hours": [8.0, 8.0],
        "market_fair_values": [60000.0, 59000.0, 58000.0],
        "ifrs_revaluation_losses": [500.0, 450.0],
        "beta": 1.1,
    }

    response = client.post("/asset/lam", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["lease_label"] == "lease-1"
    assert len(data["schedule"]) == 2
    assert data["total_revaluation_gain_loss"] != 0


def test_asset_rvm_endpoint():
    payload = {
        "resource_label": "resource-1",
        "cumulative_extraction_amount": 12000.0,
        "cumulative_extraction_days": 180.0,
        "current_unit_extraction_value": 12.5,
        "previous_extraction_value": 140000.0,
        "total_years_of_useful_life": 8.0,
        "elapsed_years": 2.0,
        "beta": 1.05,
    }

    response = client.post("/asset/rvm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["resource_label"] == "resource-1"
    assert data["final_revaluation_value"] > 0


def test_expense_ceem_endpoint():
    payload = {
        "expense_label": "ceem-1",
        "cumulative_usage_units": 500.0,
        "cumulative_usage_days": 100.0,
        "current_unit_cost": 10.0,
        "previous_year_standard_usage_value": 15000.0,
        "useful_life_years": 1.5,
        "elapsed_years": 0.5,
        "beta": 1.1,
    }

    response = client.post("/expense/ceem", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["expense_label"] == "ceem-1"
    assert data["final_revaluation_value"] > 0


def test_expense_bdm_endpoint():
    payload = {
        "bond_label": "bond-1",
        "bond_issue_price": 100000.0,
        "bond_contract_days": 1825.0,
        "elapsed_days_since_contract": 365.0,
        "previous_valuation": 95000.0,
        "current_fair_value": 98000.0,
    }

    response = client.post("/expense/bdm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["bond_label"] == "bond-1"
    assert data["final_book_value"] > 0
    assert data["interest_type"] in {"discount", "premium"}


def test_expense_belm_endpoint():
    payload = {
        "debtor_label": "debtor-1",
        "debtor_total_amount": 50000.0,
        "remaining_years": 2.0,
        "elapsed_days": 180.0,
        "actual_repayment_amount": 2000.0,
        "interest_rate": 0.05,
        "total_debt_balance_all_counterparties": 200000.0,
        "last_year_counterparty_repayment": 5000.0,
        "last_year_total_repayment_all": 40000.0,
    }

    response = client.post("/expense/belm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["debtor_label"] == "debtor-1"
    assert data["final_bad_debt_ratio"] >= data["preliminary_bad_debt_ratio"]


def test_risk_cprm_endpoint():
    payload = {
        "exposure_id": "cprm-1",
        "allowance_for_bad_debts": 5000.0,
        "total_bond_related_assets": 100000.0,
        "bad_debt_amount": 4000.0,
        "transaction_value_per_bond_unit": 1000.0,
        "total_convertible_bond_transaction_value": 200000.0,
        "stock_purchase_transaction_value": 120000.0,
        "stock_sale_transaction_value": 100000.0,
        "total_scope_bonds_for_conversion": 5000.0,
        "current_debt_repayments": 20000.0,
        "number_of_debt_repayments": 4,
        "total_convertible_bond_purchases": 150000.0,
        "total_convertible_bond_sales": 140000.0,
        "total_number_purchase_transactions": 3,
        "total_number_sale_transactions": 2,
        "total_bond_transactions_value": 280000.0,
        "total_stock_transaction_value": 260000.0,
        "value_of_convertible_bond_products": 50000.0,
        "rate_trigger_threshold": 0.05,
    }

    response = client.post("/risk/cprm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["exposure_id"] == "cprm-1"
    assert data["final_convertible_bond_amount"] > 0


def test_risk_cocim_endpoint():
    payload = {
        "portfolio_label": "cocim-1",
        "oci_account_balance": 100000.0,
        "total_oci_amount": 500000.0,
        "policy_rate": 0.03,
        "useful_life_years_remaining": 5.0,
        "initial_recognition_amount": 80000.0,
        "year_end_balance": 110000.0,
        "quarterly_data": [
            {
                "quarter_index": 1,
                "pre_compound_balance": 90000.0,
                "post_compound_balance": 92000.0,
                "current_quarter_yield": 0.02,
                "previous_quarter_yield": 0.015,
                "previous_quarter_rate": 0.01,
                "current_quarter_rate": 0.012,
            }
        ],
    }

    response = client.post("/risk/c-ocim", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["portfolio_label"] == "cocim-1"
    assert data["final_adjusted_balance"] >= data["initial_compound_measurement"]


def test_risk_farex_endpoint():
    payload = {
        "contract_id": "farex-1",
        "base_currency_amount": 100000.0,
        "spot_rate": 1100.0,
        "forecast_rate": 1150.0,
        "inflation_rate_home": 0.02,
        "inflation_rate_foreign": 0.03,
        "hedge_ratio": 0.8,
        "last_year_prev_month_export": 50000.0,
        "last_year_prev_month_import": 40000.0,
        "last_year_current_month_export": 52000.0,
        "last_year_current_month_import": 41000.0,
        "current_year_prev_month_export": 53000.0,
        "current_year_prev_month_import": 42000.0,
    }

    response = client.post("/risk/farex", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == "farex-1"
    assert data["final_adjusted_rate"] > 0
