from __future__ import annotations

import math
from typing import List, Optional, Tuple

from ..schemas.analysis import (
    CPMRVRequest,
    CPMRVResponse,
    DCBPRARequest,
    DCBPRAResponse,
    LSMRVRequest,
    LSMRVResponse,
    PSRASRequest,
    PSRASResponse,
    TCTBeamRequest,
    TCTBeamResponse,
    TCTBeamYearEntry,
)


def _normalize_profit_angle(angle_deg: float) -> float:
    remainder = angle_deg % 180.0
    if abs(remainder - 90.0) < 1e-6:
        tweak = 0.001 if angle_deg >= 90.0 else -0.001
        return angle_deg + tweak
    return angle_deg


def _calculate_profit_wave(angle_deg: float, angle_adjustment: float) -> Tuple[float, bool, bool]:
    adjusted_angle = _normalize_profit_angle(angle_deg + angle_adjustment)
    tangent_value = math.tan(math.radians(adjusted_angle))

    denominator = 180.0 - angle_adjustment
    if abs(denominator) < 1e-6:
        denominator = 1e-6

    raw_wave = -tangent_value / denominator
    break_even_reached = adjusted_angle >= 180.0
    break_even_crossed = adjusted_angle >= 181.0

    if break_even_crossed:
        profit_wave = abs(raw_wave)
    else:
        profit_wave = raw_wave

    return profit_wave, break_even_reached, break_even_crossed


def calculate_tct_beam(payload: TCTBeamRequest) -> TCTBeamResponse:
    years = min(len(payload.fixed_costs), 5)
    schedule: List[TCTBeamYearEntry] = []

    prev_fixed_ratio: Optional[float] = None
    prev_variable_ratio: Optional[float] = None
    cumulative_fixed = 0.0
    cumulative_variable = 0.0
    cumulative_profit = 0.0
    break_even_year_index: Optional[int] = None

    for idx in range(years):
        fixed = payload.fixed_costs[idx]
        variable = payload.variable_costs[idx]
        operating_profit = payload.operating_profits[idx]

        total_cost = fixed + variable
        if total_cost == 0:
            fixed_ratio = 0.0
            variable_ratio = 0.0
        else:
            fixed_ratio = fixed / total_cost
            variable_ratio = variable / total_cost

        if prev_fixed_ratio is None:
            fixed_change = 0.0
            variable_change = 0.0
        else:
            fixed_change = fixed_ratio - prev_fixed_ratio
            variable_change = variable_ratio - prev_variable_ratio  # type: ignore[arg-type]

        angle_adjustment = (fixed_change + variable_change) * 180.0

        fixed_angle = fixed_ratio * 180.0 + angle_adjustment
        variable_angle = variable_ratio * 180.0 + angle_adjustment

        fixed_wave = math.sin(math.radians(fixed_angle))
        variable_wave = math.cos(math.radians(variable_angle))

        operating_profit_ratio = operating_profit / total_cost if total_cost != 0 else 0.0
        baseline_profit_angle = operating_profit_ratio * 180.0

        profit_wave, break_even_reached, break_even_crossed = _calculate_profit_wave(
            baseline_profit_angle,
            angle_adjustment,
        )

        if break_even_reached and break_even_year_index is None:
            break_even_year_index = idx + 1

        notes: List[str] = []
        if break_even_reached:
            notes.append("Break-even threshold reached")
        if break_even_crossed:
            notes.append("Break-even surpassed; profit wave sign flipped")
        if abs(angle_adjustment) > 90.0:
            notes.append("High variability adjustment (>90 degrees)")

        schedule.append(
            TCTBeamYearEntry(
                year_index=idx + 1,
                fixed_cost_total=round(fixed, 2),
                variable_cost_total=round(variable, 2),
                operating_profit=round(operating_profit, 2),
                total_cost=round(total_cost, 2),
                fixed_cost_ratio=round(fixed_ratio, 6),
                variable_cost_ratio=round(variable_ratio, 6),
                fixed_ratio_change=round(fixed_change, 6),
                variable_ratio_change=round(variable_change, 6),
                angle_adjustment_degrees=round(angle_adjustment, 6),
                fixed_cost_wave=round(fixed_wave, 6),
                variable_cost_wave=round(variable_wave, 6),
                operating_profit_ratio=round(operating_profit_ratio, 6),
                baseline_profit_angle_degrees=round(baseline_profit_angle, 6),
                adjusted_profit_angle_degrees=round(
                    _normalize_profit_angle(baseline_profit_angle + angle_adjustment),
                    6,
                ),
                profit_wave_value=round(profit_wave, 6),
                break_even_reached=break_even_reached,
                break_even_crossed=break_even_crossed,
                notes="; ".join(notes) if notes else None,
            )
        )

        prev_fixed_ratio = fixed_ratio
        prev_variable_ratio = variable_ratio
        cumulative_fixed += fixed
        cumulative_variable += variable
        cumulative_profit += operating_profit

    return TCTBeamResponse(
        model_label=payload.model_label,
        evaluation_years=years,
        cumulative_fixed_cost=round(cumulative_fixed, 2),
        cumulative_variable_cost=round(cumulative_variable, 2),
        cumulative_operating_profit=round(cumulative_profit, 2),
        break_even_year_index=break_even_year_index,
        schedule=schedule,
    )


def _safe_log_ratio(numerator: float, denominator: float) -> float:
    eps = 1e-9
    safe_numerator = numerator if numerator > eps else eps
    safe_denominator = denominator if denominator > eps else eps
    return math.log(safe_numerator / safe_denominator)


def calculate_cpmrv(payload: CPMRVRequest) -> CPMRVResponse:
    last_year_growth = payload.last_year_growth_rate
    last_year_drawdown = abs(payload.last_year_drawdown)

    current_growth = payload.current_year_cumulative_growth
    current_drawdown = abs(payload.current_year_cumulative_drawdown)

    last_year_average = _safe_log_ratio(last_year_growth, last_year_drawdown)
    current_year_ratio = _safe_log_ratio(current_growth, current_drawdown)

    if payload.months_elapsed is not None:
        remaining_months = max(1, 12 - payload.months_elapsed)
    else:
        remaining_months = 12

    monthly_growth_risk = (last_year_average - current_year_ratio) / remaining_months

    denom = 1.0 + monthly_growth_risk
    if abs(denom) < 1e-9:
        denom = 1e-9 if denom >= 0 else -1e-9

    risk_adjustment_component = abs(1.0 / denom)

    if monthly_growth_risk < 0:
        relative_risk = 1.0 - risk_adjustment_component
        risk_direction = "downside"
    else:
        relative_risk = 1.0 + risk_adjustment_component
        risk_direction = "upside"

    adjusted_value = payload.current_fair_value * relative_risk

    return CPMRVResponse(
        asset_label=payload.asset_label,
        last_year_average_performance=round(last_year_average, 6),
        current_year_log_ratio=round(current_year_ratio, 6),
        monthly_growth_risk=round(monthly_growth_risk, 6),
        risk_direction=risk_direction,
        relative_asset_risk=round(relative_risk, 6),
        adjusted_crypto_value=round(adjusted_value, 2),
    )


def _growth_adjustment_factor(actual_growth_rate: float) -> Tuple[float, float]:
    percentage_factor = actual_growth_rate / 100.0
    abs_percentage = abs(percentage_factor) if abs(percentage_factor) > 1e-9 else 1e-9
    adjustment_component = abs(1.0 / abs_percentage)
    if percentage_factor < 0:
        real_adjustment = 1.0 - adjustment_component
    else:
        real_adjustment = 1.0 + adjustment_component
    return percentage_factor, real_adjustment


def calculate_dcbpra(payload: DCBPRARequest) -> DCBPRAResponse:
    growth_percentage_factor, real_growth_adjustment = _growth_adjustment_factor(payload.actual_growth_rate)

    last_year_average = _safe_log_ratio(payload.last_year_growth_rate, abs(payload.last_year_drawdown))
    current_year_ratio = _safe_log_ratio(
        payload.current_year_cumulative_growth,
        abs(payload.current_year_cumulative_drawdown),
    )

    if payload.months_elapsed is not None:
        remaining_months = max(1, 12 - payload.months_elapsed)
    else:
        remaining_months = 12

    monthly_growth_risk = (last_year_average - current_year_ratio) / remaining_months

    denom = 1.0 + monthly_growth_risk
    if abs(denom) < 1e-9:
        denom = 1e-9 if denom >= 0 else -1e-9

    risk_adjustment_component = abs(1.0 / denom)

    if monthly_growth_risk < 0:
        adjustment_multiplier = 1.0 - risk_adjustment_component
        risk_direction = "downside"
    else:
        adjustment_multiplier = 1.0 + risk_adjustment_component
        risk_direction = "upside"

    adjusted_beta = payload.beta * adjustment_multiplier

    baseline_capm_return = payload.risk_free_rate + (payload.market_return_rate - payload.risk_free_rate) * payload.beta
    adjusted_expected_return = (
        payload.risk_free_rate
        + (payload.market_return_rate - payload.risk_free_rate) * adjusted_beta
    ) * real_growth_adjustment

    return DCBPRAResponse(
        asset_label=payload.asset_label,
        growth_percentage_factor=round(growth_percentage_factor, 6),
        real_growth_adjustment=round(real_growth_adjustment, 6),
        last_year_average_performance=round(last_year_average, 6),
        current_year_log_ratio=round(current_year_ratio, 6),
        monthly_growth_risk=round(monthly_growth_risk, 6),
        risk_adjustment_component=round(risk_adjustment_component, 6),
        risk_direction=risk_direction,
        adjusted_beta=round(adjusted_beta, 6),
        baseline_capm_return=round(baseline_capm_return, 6),
        adjusted_expected_return=round(adjusted_expected_return, 6),
    )


def calculate_psras(payload: PSRASRequest) -> PSRASResponse:
    eps = 1e-9

    base_ratio_numerator = payload.prepaid_cost_average_1y * payload.subscriber_count
    base_ratio_denominator = payload.prepaid_cost_total_1y if abs(payload.prepaid_cost_total_1y) > eps else eps
    base_ratio = base_ratio_numerator / base_ratio_denominator
    base_ratio = base_ratio if base_ratio > 0 else eps

    if payload.retained_contract_count and abs(payload.retained_contract_count) > eps:
        exponent_component = 1.0 - (payload.new_contract_count / payload.retained_contract_count)
    else:
        exponent_component = 1.0

    assumed_recognition_rate = base_ratio ** exponent_component

    new_avg_payment = payload.new_subscriber_total_payment / (
        payload.new_subscriber_count if abs(payload.new_subscriber_count) > eps else eps
    )

    existing_payment_total = payload.total_customer_payments - payload.cancelled_customer_payments
    existing_customer_count = payload.total_subscribers_in_period - payload.cancelled_customers_in_period
    existing_customer_count = existing_customer_count if abs(existing_customer_count) > eps else eps
    existing_avg_payment = existing_payment_total / existing_customer_count

    denominator_payments = payload.new_subscriber_total_payment + existing_payment_total
    payment_comparison_index = _safe_log_ratio(
        payload.cancelled_customer_payments if abs(payload.cancelled_customer_payments) > eps else eps,
        denominator_payments if abs(denominator_payments) > eps else eps,
    )

    if payment_comparison_index >= 0:
        payment_multiplier = 1.0 - payment_comparison_index
    else:
        payment_multiplier = 1.0 + abs(payment_comparison_index)

    payment_baseline_amount = payload.total_prepaid_and_unearned * payment_multiplier

    adjustment_factor = 1.0 - assumed_recognition_rate
    pure_performance_break_even = ((existing_avg_payment + new_avg_payment) * adjustment_factor) - (
        payment_baseline_amount * adjustment_factor
    )

    if abs(payload.variance_contract_equity_adjustment) > eps:
        beta_style_factor = payload.covariance_contract_equity_vs_prepaid / payload.variance_contract_equity_adjustment
    else:
        beta_style_factor = 0.0

    final_recognised_revenue = (payload.total_contract_deposits * payload.current_year_yield) + (
        pure_performance_break_even * beta_style_factor
    )

    return PSRASResponse(
        portfolio_label=payload.portfolio_label,
        assumed_revenue_recognition_rate=round(assumed_recognition_rate, 6),
        new_subscriber_average_payment=round(new_avg_payment, 2),
        existing_subscriber_average_payment=round(existing_avg_payment, 2),
        payment_comparison_index=round(payment_comparison_index, 6),
        payment_index_baseline_amount=round(payment_baseline_amount, 2),
        pure_performance_break_even=round(pure_performance_break_even, 2),
        final_recognised_revenue=round(final_recognised_revenue, 2),
    )

def calculate_lsmrv(payload: LSMRVRequest) -> LSMRVResponse:
    eps = 1e-9

    probability_distribution_a = 100.0 / payload.price_band_count_a
    probability_distribution_b = 100.0 / payload.price_band_count_b

    growth_sum = payload.last_evaluation_growth_a + payload.last_evaluation_growth_b
    growth_sum = growth_sum if abs(growth_sum) > eps else eps

    log_ratio = math.log(
        max(payload.last_evaluation_growth_a, eps) / max(payload.last_evaluation_growth_b, eps)
    )
    if log_ratio >= 0:
        growth_modifier = 1.0 + log_ratio
    else:
        growth_modifier = 1.0 - abs(log_ratio)
    if abs(growth_modifier) < eps:
        growth_modifier = eps

    growth_correction_value = (payload.highest_preference_a - payload.highest_preference_b) / (
        growth_sum * growth_modifier
    )

    adjustment_denominator = payload.standard_sample_size - (
        payload.price_band_criterion_count + payload.total_standard_usage
    )
    adjustment_denominator = adjustment_denominator if abs(adjustment_denominator) > eps else eps
    cumulative_adjustment_value = growth_correction_value / adjustment_denominator

    paired_length = min(len(payload.returns_a), len(payload.returns_b))
    if paired_length < 2:
        covariance = eps
    else:
        trimmed_a = payload.returns_a[:paired_length]
        trimmed_b = payload.returns_b[:paired_length]
        avg_a = sum(trimmed_a) / paired_length
        avg_b = sum(trimmed_b) / paired_length
        covariance = sum(
            (a - avg_a) * (b - avg_b) for a, b in zip(trimmed_a, trimmed_b)
        ) / (paired_length - 1)
        covariance = covariance if abs(covariance) > eps else eps

    baseline_covariance = payload.previous_covariance if abs(payload.previous_covariance) > eps else eps
    covariance_growth = math.log(
        max(abs(covariance), eps) / max(abs(baseline_covariance), eps)
    )
    if abs(covariance_growth) < eps:
        covariance_growth = eps
    covariance = math.copysign(abs(covariance_growth), covariance)

    operating_ratio = payload.operating_profit_previous / (
        payload.accounts_receivable_previous if abs(payload.accounts_receivable_previous) > eps else eps
    )
    sqrt_input = (operating_ratio / covariance) * payload.roi
    sqrt_component = math.sqrt(max(sqrt_input, 0.0))
    operating_adjustment = math.exp(sqrt_component)

    cash_flow_ratio = (payload.market_price * payload.actual_cash_flow) / (
        payload.estimated_cash_flow if abs(payload.estimated_cash_flow) > eps else eps
    )
    operating_component = operating_adjustment * cash_flow_ratio

    noise_discount_sum = payload.noise_factor + payload.discount_rate
    noise_discount_sum = noise_discount_sum if abs(noise_discount_sum) > eps else eps
    noise_discount_component = (1.0 / noise_discount_sum) * cumulative_adjustment_value

    investment_ratio = abs(
        payload.current_investment_cash_flow
        / (payload.current_total_cash_flow if abs(payload.current_total_cash_flow) > eps else eps)
    )
    log_cashflow_ratio = math.log(
        max(payload.current_investment_cash_flow, eps) / max(payload.previous_investment_cash_flow, eps)
    )
    if log_cashflow_ratio >= 0:
        cashflow_exponent = 1.0 - log_cashflow_ratio
    else:
        cashflow_exponent = 1.0 + abs(log_cashflow_ratio)

    cashflow_component = investment_ratio ** cashflow_exponent

    expected_adjustment_value = operating_component * noise_discount_component * cashflow_component

    final_adjustment_amount = (
        payload.highest_preference_a + payload.highest_preference_b
    ) * expected_adjustment_value

    return LSMRVResponse(
        evaluation_label=payload.evaluation_label,
        probability_distribution_a=round(probability_distribution_a, 6),
        probability_distribution_b=round(probability_distribution_b, 6),
        growth_correction_value=round(growth_correction_value, 6),
        cumulative_adjustment_value=round(cumulative_adjustment_value, 6),
        expected_adjustment_value=round(expected_adjustment_value, 6),
        final_adjustment_amount=round(final_adjustment_amount, 2),
    )
