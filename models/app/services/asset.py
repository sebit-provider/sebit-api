from __future__ import annotations

import math
from typing import List

from ..schemas.asset import (
    DDARequest,
    DDAResponse,
    DDAScheduleEntry,
    LAMRequest,
    LAMResponse,
    LAMScheduleEntry,
    RVMRequest,
    RVMResponse,
)


def calculate_dynamic_depreciation(payload: DDARequest) -> DDAResponse:
    """
    Implementation of the SEBIT Dynamic Depreciation Algorithm (DDA) with market
    sensitivity, usage variance, and demand-supply adjustments.
    """
    years = payload.useful_life_years
    planned_usage = payload.planned_usage_days_per_year or [365] * years
    actual_usage = payload.actual_usage_days_per_year or planned_usage
    if payload.unused_days_per_year:
        unused_days = payload.unused_days_per_year
    else:
        unused_days = [
            max(plan - actual, 0) if actual <= plan else 0
            for plan, actual in zip(planned_usage, actual_usage)
        ]

    market_series: List[float]
    if payload.market_price_series:
        market_series = list(payload.market_price_series)
        if len(market_series) < years:
            raise ValueError("market_price_series must contain at least useful_life_years entries.")
        if len(market_series) == years:
            market_series.append(market_series[-1])
    else:
        market_series = [payload.acquisition_cost] * (years + 1)

    schedule: List[DDAScheduleEntry] = []
    remaining_value = payload.acquisition_cost
    cumulative_depreciation = 0.0
    total_revaluation_gain_loss = 0.0
    total_unrecognised_revaluation = 0.0

    depreciable_total = max(payload.acquisition_cost - payload.salvage_value, 0.0)
    effective_total_days = sum(
        max(plan - unused, 0) for plan, unused in zip(planned_usage, unused_days)
    )
    daily_depreciation = (
        depreciable_total / effective_total_days if effective_total_days > 0 else 0.0
    )

    for year in range(1, years + 1):
        if remaining_value <= payload.salvage_value:
            break

        plan_days = planned_usage[year - 1]
        actual_days = actual_usage[year - 1]
        usage_ratio = (
            (actual_days - plan_days) / plan_days if plan_days > 0 else 0.0
        )

        annual_base = daily_depreciation * max(actual_days, 0)
        usage_factor = 1 + usage_ratio

        prev_index = min(year - 1, len(market_series) - 1)
        curr_index = min(year, len(market_series) - 1)
        prev_price = market_series[prev_index]
        curr_price = market_series[curr_index]

        if prev_price > 0 and curr_price > 0:
            r = math.log(curr_price / prev_price)
        else:
            r = 0.0

        market_sensitivity = math.exp(r * payload.usage_elasticity) * payload.beta
        depreciation_raw = annual_base * usage_factor * payload.adjustment_factor
        depreciation_cap = max(remaining_value - payload.salvage_value, 0.0)
        depreciation_expense = min(max(depreciation_raw, 0.0), depreciation_cap)
        post_depreciation_value = remaining_value - depreciation_expense

        baseline_revaluation_value = post_depreciation_value * market_sensitivity
        baseline_gain_loss = baseline_revaluation_value - post_depreciation_value

        projected_cumulative = cumulative_depreciation + depreciation_expense
        trigger_stage: Optional[str] = None
        unrecognised_revaluation = 0.0

        if baseline_gain_loss < 0:
            baseline_loss = -baseline_gain_loss
            allowed_loss = max(0.0, 1.2 * payload.acquisition_cost - projected_cumulative)
            recognised_loss_abs = min(baseline_loss, allowed_loss)
            recognised_loss = -recognised_loss_abs
            if recognised_loss_abs < baseline_loss:
                trigger_stage = "6-3-1"
            final_revaluation_value = post_depreciation_value + recognised_loss
            final_revaluation_value = max(final_revaluation_value, payload.salvage_value)
            revaluation_gain_loss = recognised_loss
            unrecognised_revaluation = baseline_loss - recognised_loss_abs
        else:
            final_revaluation_value = baseline_revaluation_value
            revaluation_gain_loss = baseline_gain_loss
            unrecognised_revaluation = 0.0

        closing_book_value = final_revaluation_value
        adjustment_multiplier = (
            depreciation_expense / annual_base if annual_base else 0.0
        )

        schedule.append(
            DDAScheduleEntry(
                year_index=year,
                opening_book_value=round(remaining_value, 2),
                depreciation_expense=round(depreciation_expense, 2),
                closing_book_value=round(closing_book_value, 2),
                baseline_revaluation_value=round(baseline_revaluation_value, 2),
                final_revaluation_value=round(final_revaluation_value, 2),
                revaluation_gain_loss=round(revaluation_gain_loss, 2),
                trigger_stage=trigger_stage,
                unrecognised_revaluation=round(unrecognised_revaluation, 2),
                adjustment_multiplier=round(adjustment_multiplier, 4),
                usage_ratio=round(usage_ratio, 4),
                market_sensitivity=round(market_sensitivity, 4),
            )
        )

        remaining_value = closing_book_value
        cumulative_depreciation = projected_cumulative
        total_revaluation_gain_loss += revaluation_gain_loss
        total_unrecognised_revaluation += unrecognised_revaluation

    return DDAResponse(
        asset_label=payload.asset_label,
        schedule=schedule,
        total_depreciation=round(cumulative_depreciation, 2),
        total_revaluation_gain_loss=round(total_revaluation_gain_loss, 2),
        total_unrecognised_revaluation=round(total_unrecognised_revaluation, 2),
    )


def calculate_lease_amortization(payload: LAMRequest) -> LAMResponse:
    """
    Compute the SEBIT-LAM lease amortisation sequence following the documented steps.

    Each period represents an evaluation point (typically annual). For every period we derive:
      1) Daily lease amortisation amount.
      2) Usage variance ratio.
      3) Interest expense (constant across periods).
      4) Market change index/log-return of fair values.
      5) Market sensitivity multiplier.
      6) Final revaluation value, including trigger logic (6-1 ~ 6-3-1).
    """
    periods = payload.lease_term_years
    planned_days = payload.planned_usage_days_per_period or [365] * periods
    actual_days = payload.actual_usage_days_per_period or planned_days
    unused_days = payload.unused_days_per_period or [
        max(plan - actual, 0) if plan >= actual else 0 for plan, actual in zip(planned_days, actual_days)
    ]
    actual_hours = payload.actual_daily_usage_hours or []
    standard_hours = payload.standard_daily_usage_hours or []

    fair_values: List[float]
    if payload.market_fair_values:
        fair_values = list(payload.market_fair_values)
        if len(fair_values) == periods:
            fair_values.insert(0, payload.initial_asset_value)
    else:
        fair_values = [payload.initial_asset_value]

    ifrs_losses = payload.ifrs_revaluation_losses or [0.0] * periods
    if len(ifrs_losses) < periods:
        ifrs_losses = list(ifrs_losses) + [0.0] * (periods - len(ifrs_losses))

    schedule: List[LAMScheduleEntry] = []
    opening_balance = payload.initial_asset_value
    accumulated_depreciation = payload.accumulated_depreciation_opening
    total_interest_expense = 0.0
    total_gain_loss = 0.0
    total_termination_adjustment = 0.0

    interest_expense = payload.initial_asset_value * payload.discount_rate

    total_planned_days = sum(planned_days) if planned_days else payload.lease_term_years * 365
    total_unused_days = sum(unused_days) if unused_days else 0
    effective_total_days = max(total_planned_days - total_unused_days, 1)
    base_daily_amortization = payload.initial_asset_value / effective_total_days

    for period in range(1, periods + 1):
        plan_days = planned_days[period - 1]
        actual_used_days = actual_days[period - 1]
        unused = unused_days[period - 1]
        effective_days = max(plan_days - unused, 1)

        daily_lease_amortization = base_daily_amortization

        if standard_hours:
            standard_usage = standard_hours[period - 1]
        else:
            standard_usage = plan_days
        if actual_hours:
            actual_usage_measure = actual_hours[period - 1]
        else:
            actual_usage_measure = actual_used_days

        usage_ratio = (
            (actual_usage_measure - standard_usage) / standard_usage
            if standard_usage
            else 0.0
        )

        depreciation_component = daily_lease_amortization * actual_used_days * (1 + usage_ratio)
        current_depreciation = max(depreciation_component, 0.0)
        projected_accumulated = accumulated_depreciation + current_depreciation

        base_after_depreciation = max(opening_balance - depreciation_component, payload.residual_value)

        if len(fair_values) > period:
            prev_fair_value = fair_values[period - 1]
            current_fair_value = fair_values[period]
        elif fair_values:
            prev_fair_value = fair_values[-1]
            current_fair_value = prev_fair_value
        else:
            prev_fair_value = opening_balance
            current_fair_value = opening_balance

        if prev_fair_value > 0 and current_fair_value > 0:
            market_change_index = math.log(current_fair_value / prev_fair_value)
        else:
            market_change_index = 0.0

        market_sensitivity = math.exp(market_change_index * payload.lease_term_years) * payload.beta

        baseline_revaluation_value = base_after_depreciation * market_sensitivity

        trigger_stage = None
        post_trigger_value = baseline_revaluation_value

        baseline_gain_loss = baseline_revaluation_value - opening_balance
        baseline_loss_magnitude = max(0.0, -baseline_gain_loss)
        termination_adjustment = 0.0

        total_loss_projection = projected_accumulated + baseline_loss_magnitude

        if total_loss_projection >= 1.2 * payload.initial_asset_value:
            capacity = max(
                0.0, 1.2 * payload.initial_asset_value - projected_accumulated
            )
            recognised_loss = -min(baseline_loss_magnitude, capacity)
            post_trigger_value = opening_balance + recognised_loss
            trigger_stage = "6-3-1"
            revaluation_gain_loss = recognised_loss
            termination_adjustment = baseline_gain_loss - recognised_loss
        else:
            usage_condition = (
                actual_used_days / max(payload.lease_term_years * 365, 1) >= 0.75
            )
            revaluation_condition = abs(baseline_gain_loss) > 2 * payload.initial_asset_value

            if usage_condition and revaluation_condition:
                reverse_impairment = (baseline_revaluation_value - payload.residual_value) * (1 - 0.3)
                current_value = reverse_impairment
                trigger_stage = "6-1"

                if abs(current_value) > 2 * payload.initial_asset_value:
                    current_value = current_value - ifrs_losses[period - 1]
                    trigger_stage = "6-2"

                    if abs(current_value) > 2 * payload.initial_asset_value:
                        current_value = current_value - ifrs_losses[period - 1]
                        trigger_stage = "6-3"

                post_trigger_value = current_value

            revaluation_gain_loss = post_trigger_value - opening_balance
            loss_component = max(0.0, -revaluation_gain_loss)

            if projected_accumulated + loss_component > payload.initial_asset_value:
                termination_adjustment = baseline_gain_loss - revaluation_gain_loss
                post_trigger_value = opening_balance
                revaluation_gain_loss = 0.0
                trigger_stage = trigger_stage or "cap"
            else:
                termination_adjustment = baseline_gain_loss - revaluation_gain_loss

        accumulated_depreciation = projected_accumulated
        closing_balance = post_trigger_value

        total_interest_expense += interest_expense
        total_gain_loss += revaluation_gain_loss
        total_termination_adjustment += termination_adjustment

        schedule.append(
            LAMScheduleEntry(
                period_index=period,
                opening_balance=round(opening_balance, 2),
                closing_balance=round(closing_balance, 2),
                daily_lease_amortization=round(daily_lease_amortization, 4),
                usage_ratio=round(usage_ratio, 4),
                interest_expense=round(interest_expense, 2),
                market_change_index=round(market_change_index, 6),
                market_sensitivity=round(market_sensitivity, 4),
                baseline_revaluation_value=round(baseline_revaluation_value, 2),
                trigger_stage=trigger_stage,
                post_trigger_value=round(post_trigger_value, 2),
                revaluation_gain_loss=round(revaluation_gain_loss, 2),
                termination_adjustment=round(termination_adjustment, 2),
            )
        )

        opening_balance = closing_balance

    return LAMResponse(
        lease_label=payload.lease_label,
        schedule=schedule,
        total_revaluation_gain_loss=round(total_gain_loss, 2),
        total_interest_expense=round(total_interest_expense, 2),
        total_termination_adjustment=round(total_termination_adjustment, 2),
    )


def calculate_resource_valuation(payload: RVMRequest) -> RVMResponse:
    """
    Implement the SEBIT-RVM (Resource Valuation Model) according to the specification.

    Steps:
      1. Daily average extraction amount.
      2. Standard and total extraction values.
      3. Extraction rate (%).
      4. Market change index (log change vs. previous evaluation).
      5. Market sensitivity value (CAPM beta scaling).
      6. Final revaluation value.
    """
    daily_average_extraction = payload.cumulative_extraction_amount / payload.cumulative_extraction_days

    total_days = payload.total_extraction_days_at_evaluation or payload.cumulative_extraction_days
    standard_extraction_value = daily_average_extraction * payload.current_unit_extraction_value * total_days

    total_extraction_value = payload.cumulative_extraction_amount * payload.current_unit_extraction_value

    if standard_extraction_value == 0:
        extraction_rate = 0.0
    else:
        extraction_rate = (total_extraction_value - standard_extraction_value) / standard_extraction_value

    previous_value = payload.previous_extraction_value or standard_extraction_value or total_extraction_value
    if previous_value and previous_value > 0 and total_extraction_value > 0:
        market_change_index = math.log(total_extraction_value / previous_value)
    else:
        market_change_index = 0.0

    effective_years = max(payload.total_years_of_useful_life - payload.elapsed_years, 0.0)
    market_sensitivity = math.exp(market_change_index * effective_years) * payload.beta

    if extraction_rate >= 0:
        extraction_multiplier = 1 + extraction_rate
    else:
        extraction_multiplier = 1 + extraction_rate  # extraction_rate already negative, reduces total value

    final_revaluation_value = total_extraction_value * extraction_multiplier * market_sensitivity

    return RVMResponse(
        resource_label=payload.resource_label,
        daily_average_extraction=round(daily_average_extraction, 6),
        standard_extraction_value=round(standard_extraction_value, 2),
        total_extraction_value=round(total_extraction_value, 2),
        extraction_rate=round(extraction_rate, 6),
        market_change_index=round(market_change_index, 6),
        market_sensitivity=round(market_sensitivity, 6),
        final_revaluation_value=round(final_revaluation_value, 2),
    )
