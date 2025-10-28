from __future__ import annotations

import math
from typing import Optional

from ..schemas.expense import (
    CEEMRequest,
    CEEMResponse,
    BDMRequest,
    BDMResponse,
    BELMRequest,
    BELMResponse,
)


def calculate_ceem(payload: CEEMRequest) -> CEEMResponse:
    """
    Consumable Expense Evaluation Model implementation following SEBIT-CEEM.

    Steps:
      1) Daily average usage units.
      2) Standard usage value (non-quantitative & optional quantitative).
      3) Usage change rate.
      4) Market change index (log ratio to previous year).
      5) Market sensitivity value.
      6) Final revaluation value.
    """
    daily_avg_usage_units = payload.cumulative_usage_units / payload.cumulative_usage_days

    standard_value_non_quant = daily_avg_usage_units * payload.current_unit_cost * 365

    standard_value_quant: Optional[float] = None
    if payload.quantitative_usage_limit is not None:
        standard_value_quant = payload.quantitative_usage_limit * payload.current_unit_cost

    if standard_value_quant is not None:
        selected_standard_value = standard_value_quant
    else:
        selected_standard_value = standard_value_non_quant

    total_usage_value = payload.cumulative_usage_units * payload.current_unit_cost

    if selected_standard_value == 0:
        usage_change_rate = 0.0
    else:
        usage_change_rate = (total_usage_value - selected_standard_value) / selected_standard_value

    market_change_index = math.log(selected_standard_value / payload.previous_year_standard_usage_value)

    effective_years = payload.useful_life_years + max(payload.elapsed_years - 1, 0)
    market_sensitivity_value = math.exp(market_change_index * effective_years) * payload.beta

    final_revaluation_value = total_usage_value * (1 + usage_change_rate) * market_sensitivity_value

    return CEEMResponse(
        expense_label=payload.expense_label,
        daily_average_usage_units=round(daily_avg_usage_units, 6),
        standard_usage_value_non_quantitative=round(standard_value_non_quant, 2),
        standard_usage_value_quantitative=round(standard_value_quant, 2) if standard_value_quant is not None else None,
        selected_standard_usage_value=round(selected_standard_value, 2),
        total_consumable_usage_value=round(total_usage_value, 2),
        usage_change_rate=round(usage_change_rate, 6),
        market_change_index=round(market_change_index, 6),
        market_sensitivity_value=round(market_sensitivity_value, 6),
        final_revaluation_value=round(final_revaluation_value, 2),
    )


def calculate_bdm(payload: BDMRequest) -> BDMResponse:
    """
    Bond Depreciation Model implementation.

    Steps:
      1) Daily estimated bond usage.
      2) Estimated value P_s based on elapsed days.
      3) Market beta relative to previous valuation.
      4) Final book value using current fair value.
      5) Interest cost classification (discount or premium).
    """
    daily_usage = payload.bond_issue_price / payload.bond_contract_days
    estimated_ps = payload.bond_issue_price - (daily_usage * payload.elapsed_days_since_contract)

    previous_value = payload.previous_valuation or payload.current_fair_value
    if previous_value == 0:
        market_beta = 1.0
    else:
        market_beta = 1 + ((estimated_ps - previous_value) / previous_value)

    final_book_value = payload.current_fair_value * market_beta

    if final_book_value < estimated_ps:
        interest_cost = estimated_ps - final_book_value
        interest_type = "discount"
    else:
        interest_cost = final_book_value - estimated_ps
        interest_type = "premium"

    return BDMResponse(
        bond_label=payload.bond_label,
        daily_estimated_usage=round(daily_usage, 6),
        estimated_value_ps=round(estimated_ps, 2),
        market_beta=round(market_beta, 6),
        final_book_value=round(final_book_value, 2),
        interest_cost=round(interest_cost, 2),
        interest_type=interest_type,
    )


def calculate_belm(payload: BELMRequest) -> BELMResponse:
    """
    Bad debt Expected Loss Model implementation.

    Steps:
      1) Daily estimated repayment.
      2) Expected repayment at evaluation.
      3) Interest-rate adjustment factor.
      4) Actual interest cost.
      5) Preliminary and final bad debt ratios.
    """
    days_remaining = payload.remaining_years * 365
    daily_estimated_repayment = payload.debtor_total_amount / days_remaining

    expected_repayment = daily_estimated_repayment * payload.elapsed_days

    numerator = (
        (payload.debtor_total_amount - expected_repayment)
        - (expected_repayment - payload.actual_repayment_amount)
    )
    interest_rate_adjustment = 1
    if payload.debtor_total_amount != 0:
        adjustment_fraction = numerator / payload.debtor_total_amount
        interest_rate_adjustment = 1 + adjustment_fraction

    actual_interest_cost = (payload.debtor_total_amount - payload.actual_repayment_amount) * (
        payload.interest_rate * interest_rate_adjustment
    )

    preliminary_bad_debt_ratio = payload.debtor_total_amount / payload.total_debt_balance_all_counterparties

    additional_component = payload.last_year_counterparty_repayment / payload.last_year_total_repayment_all

    final_bad_debt_ratio = preliminary_bad_debt_ratio + max(0.0, additional_component)

    return BELMResponse(
        debtor_label=payload.debtor_label,
        daily_estimated_repayment=round(daily_estimated_repayment, 6),
        expected_repayment_at_evaluation=round(expected_repayment, 2),
        interest_rate_adjustment=round(interest_rate_adjustment, 6),
        actual_interest_cost=round(actual_interest_cost, 2),
        preliminary_bad_debt_ratio=round(preliminary_bad_debt_ratio, 6),
        final_bad_debt_ratio=round(final_bad_debt_ratio, 6),
    )
