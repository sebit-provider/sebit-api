from __future__ import annotations

import math
from typing import List, Optional

from ..schemas.risk import (
    COCIMQuarterResult,
    COCIMRequest,
    COCIMResponse,
    CPRMRequest,
    CPRMResponse,
    FAREXRequest,
    FAREXResponse,
)


def calculate_cprm(payload: CPRMRequest) -> CPRMResponse:
    """
    SEBIT-CPRM implementation for convertible bond risk measurement.

    Follows steps:
      1. Assumed bad debt occurrence rate.
      2. Convertible bond rate.
      3. Initial convertible bond amount.
      4. Average past bad debt recovery.
      5. Average convertible bond transaction price.
      6. Additional adjustment beta.
      7. Final convertible bond amount with triggers when thresholds are hit.
    """
    assumed_bad_debt_occurrence_rate = payload.allowance_for_bad_debts / payload.total_bond_related_assets

    log_ratio = math.log(
        payload.stock_purchase_transaction_value / payload.stock_sale_transaction_value
    )
    denominator = (
        payload.transaction_value_per_bond_unit
        * payload.total_convertible_bond_transaction_value
        * log_ratio
    )
    if denominator == 0:
        convertible_bond_rate = 0.0
    else:
        convertible_bond_rate = (payload.bad_debt_amount * (1 + assumed_bad_debt_occurrence_rate)) / denominator

    convertible_bond_first = payload.total_scope_bonds_for_conversion * convertible_bond_rate

    average_past_bad_debt_recovery = payload.current_debt_repayments / payload.number_of_debt_repayments

    total_transactions_count = payload.total_number_purchase_transactions + payload.total_number_sale_transactions
    average_convertible_bond_price = (
        (payload.total_convertible_bond_purchases + payload.total_convertible_bond_sales) / total_transactions_count
    )

    ratio_bond_stock = payload.total_bond_transactions_value / payload.total_stock_transaction_value
    if average_past_bad_debt_recovery == 0 or ratio_bond_stock == 0:
        additional_adjustment_beta = 0.0
    else:
        additional_adjustment_beta = (average_convertible_bond_price / average_past_bad_debt_recovery) / ratio_bond_stock

    final_convertible_bond_amount = (
        convertible_bond_first + payload.value_of_convertible_bond_products * additional_adjustment_beta
    )

    total_debt_repayment = (
        payload.total_debt_repayment_for_trigger if payload.total_debt_repayment_for_trigger is not None else payload.current_debt_repayments
    )

    trigger_applied = False
    convertible_bond_rate_adjustment: Optional[float] = None
    final_adjusted_rate = additional_adjustment_beta

    if convertible_bond_rate >= payload.rate_trigger_threshold:
        values = {
            "stock": payload.total_stock_transaction_value,
            "debt": total_debt_repayment,
            "product": payload.value_of_convertible_bond_products,
        }
        max_key = max(values, key=values.get)
        max_value = values[max_key]
        other_sum = sum(values.values()) - max_value
        denominator_adjustment = max_value - payload.total_stock_transaction_value
        if denominator_adjustment != 0:
            convertible_bond_rate_adjustment = (max_value - other_sum) / denominator_adjustment
        else:
            convertible_bond_rate_adjustment = 0.0
        final_adjusted_rate = additional_adjustment_beta * (1 - convertible_bond_rate_adjustment)
        trigger_applied = True

    return CPRMResponse(
        exposure_id=payload.exposure_id,
        assumed_bad_debt_occurrence_rate=round(assumed_bad_debt_occurrence_rate, 6),
        convertible_bond_rate=round(convertible_bond_rate, 6),
        convertible_bond_first_amount=round(convertible_bond_first, 2),
        average_past_bad_debt_recovery=round(average_past_bad_debt_recovery, 2),
        average_convertible_bond_price=round(average_convertible_bond_price, 2),
        additional_adjustment_beta=round(additional_adjustment_beta, 6),
        final_convertible_bond_amount=round(final_convertible_bond_amount, 2),
        trigger_applied=trigger_applied,
        convertible_bond_rate_adjustment=round(convertible_bond_rate_adjustment, 6) if convertible_bond_rate_adjustment is not None else None,
        final_adjusted_convertible_bond_rate=round(final_adjusted_rate, 6),
    )


def calculate_cocim(payload: COCIMRequest) -> COCIMResponse:
    """
    Compound-Other Comprehensive Income Model implementation.

    Steps:
      1) Account ratio for the target OCI account.
      2) Initial compound measurement using the policy rate.
      3) Quarterly compound adjustments following the specified formula.
      4) Annual compound growth rate and optional trigger adjustment.
    """
    account_ratio = payload.oci_account_balance / payload.total_oci_amount
    initial_compound_measurement = payload.oci_account_balance / ((1 + payload.policy_rate) ** payload.useful_life_years_remaining)

    quarterly_results: List[COCIMQuarterResult] = []
    for quarter in payload.quarterly_data:
        numerator = payload.initial_recognition_amount + (quarter.pre_compound_balance - quarter.post_compound_balance)
        denominator = (
            1
            + ((quarter.current_quarter_yield + quarter.previous_quarter_yield) - (quarter.previous_quarter_rate + quarter.current_quarter_rate))
            - payload.initial_recognition_amount
        )
        adjustment_value = numerator / denominator if denominator != 0 else 0.0
        quarterly_results.append(
            COCIMQuarterResult(
                quarter_index=quarter.quarter_index,
                adjustment_value=round(adjustment_value, 6),
                pre_compound_balance=round(quarter.pre_compound_balance, 2),
                post_compound_balance=round(quarter.post_compound_balance, 2),
            )
        )

    annual_compound_growth_rate = (
        (payload.year_end_balance - payload.initial_recognition_amount) / payload.initial_recognition_amount
        if payload.initial_recognition_amount != 0
        else 0.0
    )

    final_compound_increase = payload.year_end_balance - payload.initial_recognition_amount
    compound_adjustment_amount = 0.0
    trigger_applied = False
    if annual_compound_growth_rate >= 0.30:
        compound_adjustment_amount = final_compound_increase * annual_compound_growth_rate
        trigger_applied = True

    final_adjusted_balance = payload.year_end_balance + compound_adjustment_amount

    return COCIMResponse(
        portfolio_label=payload.portfolio_label,
        account_ratio=round(account_ratio, 6),
        initial_compound_measurement=round(initial_compound_measurement, 6),
        quarterly_adjustments=quarterly_results,
        annual_compound_growth_rate=round(annual_compound_growth_rate, 6),
        compound_growth_trigger_applied=trigger_applied,
        compound_adjustment_amount=round(compound_adjustment_amount, 6),
        final_adjusted_balance=round(final_adjusted_balance, 2),
    )


def calculate_farex(payload: FAREXRequest) -> FAREXResponse:
    """
    Foreign Adjustment & Real Exchange Model (FAREX) approximation.

    Implements the SEBIT-FAREX workflow following the specification.
    """
    numerator_last_year = (
        (payload.last_year_prev_month_export - payload.last_year_prev_month_import) / payload.last_year_prev_month_export
        - (payload.last_year_prev_month_import - payload.last_year_prev_month_export) / payload.last_year_prev_month_import
    )
    denominator_last_year = (
        (payload.last_year_current_month_export - payload.last_year_current_month_import) / payload.last_year_current_month_export
        - (payload.last_year_current_month_import - payload.last_year_current_month_export) / payload.last_year_current_month_import
    )
    last_year_trade_ratio = numerator_last_year / denominator_last_year if denominator_last_year != 0 else 0.0

    numerator_current = (
        (payload.current_year_prev_month_export - payload.last_year_current_month_export)
        - (payload.current_year_prev_month_import - payload.last_year_current_month_import)
    )
    denominator_current = (
        (payload.current_year_prev_month_import - payload.last_year_current_month_export)
        - (payload.current_year_prev_month_export - payload.last_year_current_month_import)
    )
    adjustment_term = numerator_current / denominator_current if denominator_current != 0 else 0.0
    current_year_trade_ratio = last_year_trade_ratio - adjustment_term

    def _normalise_ratio(value: float) -> float:
        if value >= 0:
            return value
        adjusted = value
        while adjusted < 0:
            adjusted += 1
        adjusted = 1 - abs(adjusted)
        if adjusted == 0:
            adjusted = 1e-6
        return adjusted

    norm_last_year = _normalise_ratio(last_year_trade_ratio)
    norm_current_year = _normalise_ratio(current_year_trade_ratio)
    export_import_beta = math.log(norm_last_year / norm_current_year) if norm_current_year not in {0.0, None} else 0.0

    ratio_component_numerator = (
        payload.last_year_prev_month_export
        + payload.last_year_current_month_export
        - payload.current_year_prev_month_export
    )
    ratio_component_denominator = (
        payload.last_year_prev_month_import
        + payload.last_year_current_month_import
        - payload.last_year_prev_month_import
    ) or payload.last_year_current_month_import
    if ratio_component_denominator == 0:
        ratio_component_denominator = 1e-6
    ratio_component = ratio_component_numerator / ratio_component_denominator
    if export_import_beta >= 0:
        indicator_term = export_import_beta * ratio_component
        adjustment_indicator = 1 - indicator_term
    else:
        beta_abs = abs(export_import_beta)
        indicator_term = beta_abs * ratio_component
        adjustment_indicator = 1 + indicator_term

    inflation_adjusted_rate = payload.spot_rate * ((1 + payload.inflation_rate_home) / (1 + payload.inflation_rate_foreign))

    if abs(adjustment_indicator) >= 1.5 and adjustment_indicator != 0:
        final_adjusted_rate = inflation_adjusted_rate / adjustment_indicator
    else:
        final_adjusted_rate = inflation_adjusted_rate * adjustment_indicator

    revaluation_amount = payload.base_currency_amount * (final_adjusted_rate - payload.spot_rate)

    return FAREXResponse(
        contract_id=payload.contract_id,
        last_year_trade_ratio=round(last_year_trade_ratio, 6),
        current_year_trade_ratio=round(current_year_trade_ratio, 6),
        export_import_beta=round(export_import_beta, 6),
        adjustment_indicator=round(adjustment_indicator, 6),
        inflation_adjusted_rate=round(inflation_adjusted_rate, 6),
        final_adjusted_rate=round(final_adjusted_rate, 6),
        revaluation_amount=round(revaluation_amount, 2),
    )
