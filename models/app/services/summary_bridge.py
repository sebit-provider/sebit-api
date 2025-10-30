from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import httpx
from pydantic import BaseModel, Field, ValidationError


class SummaryEntry(BaseModel):
    """Representation of a single summary entry."""

    series: str = Field(..., description="Model category label (e.g., Asset & Depreciation).")
    model: str = Field(..., description="Model identifier (e.g., SEBIT-DDA).")
    headline_amount: float = Field(..., description="Headline metric promoted to dashboards.")
    currency: str = Field(..., description="Currency code for the headline amount.")
    details: Dict[str, Any] = Field(..., description="Raw model output payload.")


class SummaryReportRequest(BaseModel):
    """Payload submitted to the summary API."""

    generated_at: str = Field(
        ...,
        description="ISO-8601 timestamp the bridge produced the summary.",
    )
    entries: List[SummaryEntry] = Field(..., description="Flattened entries drawn from model results.")


MODEL_MAPPING: Dict[str, Mapping[str, Any]] = {
    "asset/dda": {
        "series": "Asset & Depreciation",
        "model": "SEBIT-DDA",
        "headline_key": "total_revaluation_gain_loss",
        "fallback_key": "total_depreciation",
        "currency": "KRW",
    },
    "asset/lam": {
        "series": "Asset & Depreciation",
        "model": "SEBIT-LAM",
        "headline_key": "total_revaluation_gain_loss",
        "fallback_key": "total_interest_expense",
        "currency": "KRW",
    },
    "asset/rvm": {
        "series": "Asset & Depreciation",
        "model": "SEBIT-RVM",
        "headline_key": "final_revaluation_value",
        "fallback_key": "total_extraction_value",
        "currency": "KRW",
    },
    "expense/ceem": {
        "series": "Expense & Profitability",
        "model": "SEBIT-CEEM",
        "headline_key": "final_revaluation_value",
        "fallback_key": "adjusted_consumable_usage_value",
        "currency": "KRW",
    },
    "expense/bdm": {
        "series": "Expense & Profitability",
        "model": "SEBIT-BDM",
        "headline_key": "final_book_value",
        "fallback_key": "interest_cost",
        "currency": "KRW",
    },
    "expense/belm": {
        "series": "Expense & Profitability",
        "model": "SEBIT-BELM",
        "headline_key": "final_bad_debt_ratio",
        "fallback_key": "actual_interest_cost",
        "currency": "KRW",
    },
    "risk/cprm": {
        "series": "Capital & Risk Derivatives",
        "model": "SEBIT-CPRM",
        "headline_key": "final_convertible_bond_amount",
        "fallback_key": "final_adjusted_convertible_bond_rate",
        "currency": "KRW",
    },
    "risk/c-ocim": {
        "series": "Capital & Risk Derivatives",
        "model": "SEBIT-C-OCIM",
        "headline_key": "final_adjusted_balance",
        "fallback_key": "compound_adjustment_amount",
        "currency": "KRW",
    },
    "risk/farex": {
        "series": "Capital & Risk Derivatives",
        "model": "SEBIT-FAREX",
        "headline_key": "revaluation_amount",
        "fallback_key": "final_adjusted_rate",
        "currency": "KRW",
    },
    "analysis/tct-beam": {
        "series": "Advanced Analytics",
        "model": "SEBIT-TCT-BEAM",
        "headline_key": "cumulative_operating_profit",
        "fallback_key": "cumulative_fixed_cost",
        "currency": "KRW",
    },
    "analysis/cpmrv": {
        "series": "Advanced Analytics",
        "model": "SEBIT-CPMRV",
        "headline_key": "adjusted_crypto_value",
        "fallback_key": "relative_asset_risk",
        "currency": "USD",
    },
    "analysis/dcbpra": {
        "series": "Advanced Analytics",
        "model": "SEBIT-DCBPRA",
        "headline_key": "adjusted_expected_return",
        "fallback_key": "baseline_capm_return",
        "currency": "KRW",
    },
    "service/psras": {
        "series": "Insurance & Service Revenue",
        "model": "SEBIT-PSRAS",
        "headline_key": "final_recognised_revenue",
        "fallback_key": "pure_performance_break_even",
        "currency": "KRW",
    },
    "probability/lsmrv": {
        "series": "Probability Revaluation",
        "model": "SEBIT-LSMRV",
        "headline_key": "final_adjustment_amount",
        "fallback_key": "expected_adjustment_value",
        "currency": "KRW",
    },
}


def _select_headline_amount(mapping: Mapping[str, Any], model_output: Mapping[str, Any]) -> float:
    headline_key = mapping["headline_key"]
    fallback_key = mapping["fallback_key"]

    headline_amount = model_output.get(headline_key)
    if headline_amount is None:
        headline_amount = model_output.get(fallback_key)

    if headline_amount is None:
        raise ValueError(
            f"Unable to determine headline amount: '{headline_key}' and '{fallback_key}' missing from output."
        )

    return float(headline_amount)


def map_model_output_to_summary_entry(endpoint: str, model_output: Dict[str, Any]) -> SummaryEntry:
    """Convert a SEBIT model output to a summary entry."""
    mapping = MODEL_MAPPING.get(endpoint)
    if mapping is None:
        raise KeyError(f"Endpoint '{endpoint}' is not registered in MODEL_MAPPING.")

    headline_amount = _select_headline_amount(mapping, model_output)
    try:
        return SummaryEntry(
            series=mapping["series"],
            model=mapping["model"],
            headline_amount=headline_amount,
            currency=mapping["currency"],
            details=dict(model_output),
        )
    except ValidationError as exc:
        raise ValueError(f"Failed to construct SummaryEntry: {exc}") from exc


async def post_summary_report(
    base_url: str,
    internal_token: str,
    entries: Iterable[SummaryEntry],
    *,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Send the summary report payload to the external summary API."""
    payload = SummaryReportRequest(generated_at=datetime.now(timezone.utc).isoformat(), entries=list(entries))

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/summary/report",
            json=payload.model_dump(),
            headers={
                "Content-Type": "application/json",
                "X-Internal-Token": internal_token,
            },
        )

        response.raise_for_status()
        return response.json()


async def bridge_and_send_summary(
    summary_base_url: str,
    internal_token: str,
    model_outputs: Iterable[Tuple[str, Dict[str, Any]]],
    *,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Build summary entries from model outputs and forward them."""
    entries = [map_model_output_to_summary_entry(endpoint, output) for endpoint, output in model_outputs]
    return await post_summary_report(summary_base_url, internal_token, entries, timeout=timeout)
