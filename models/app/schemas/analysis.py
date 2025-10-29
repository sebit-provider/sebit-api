from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class TCTBeamRequest(BaseModel):
    model_label: Optional[str] = Field(
        default=None,
        description="Identifier for the scenario (e.g., product line or cost centre).",
    )
    fixed_costs: List[float] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Annual fixed cost totals for up to five years.",
    )
    variable_costs: List[float] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Annual variable cost totals matching the fixed cost periods.",
    )
    operating_profits: List[float] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Operating profit (or loss) realised in each period.",
    )

    @model_validator(mode="after")
    def _validate_lengths(self) -> "TCTBeamRequest":
        length = len(self.fixed_costs)
        if len(self.variable_costs) != length or len(self.operating_profits) != length:
            raise ValueError("fixed_costs, variable_costs, and operating_profits must contain the same number of periods.")
        if length > 5:
            raise ValueError("SEBIT-TCT-BEAM only evaluates the first five years.")
        return self


class TCTBeamYearEntry(BaseModel):
    year_index: int = Field(..., ge=1)
    fixed_cost_total: float
    variable_cost_total: float
    operating_profit: float
    total_cost: float
    fixed_cost_ratio: float
    variable_cost_ratio: float
    fixed_ratio_change: float
    variable_ratio_change: float
    angle_adjustment_degrees: float
    fixed_cost_wave: float
    variable_cost_wave: float
    operating_profit_ratio: float
    baseline_profit_angle_degrees: float
    adjusted_profit_angle_degrees: float
    profit_wave_value: float
    break_even_reached: bool
    break_even_crossed: bool
    notes: Optional[str] = None


class TCTBeamResponse(BaseModel):
    model_label: Optional[str]
    evaluation_years: int = Field(..., ge=1, le=5)
    cumulative_fixed_cost: float
    cumulative_variable_cost: float
    cumulative_operating_profit: float
    break_even_year_index: Optional[int] = None
    schedule: List[TCTBeamYearEntry]


class CPMRVRequest(BaseModel):
    asset_label: Optional[str] = Field(
        default=None,
        description="Identifier for the crypto asset under review.",
    )
    last_year_growth_rate: float = Field(
        ...,
        description="Aggregate 1-year growth (RSI-based) for the prior period.",
    )
    last_year_drawdown: float = Field(
        ...,
        description="Aggregate drawdown magnitude for the prior period.",
    )
    current_year_cumulative_growth: float = Field(
        ...,
        description="Cumulative growth observed in the current year-to-date.",
    )
    current_year_cumulative_drawdown: float = Field(
        ...,
        description="Cumulative drawdown magnitude observed in the current year-to-date.",
    )
    current_fair_value: float = Field(
        ...,
        description="Current fair value estimate of the crypto asset.",
    )
    months_elapsed: Optional[int] = Field(
        default=None,
        ge=0,
        le=12,
        description="Optional months elapsed in the fiscal year (adjusts the monthly risk divisor).",
    )


class CPMRVResponse(BaseModel):
    asset_label: Optional[str]
    last_year_average_performance: float
    current_year_log_ratio: float
    monthly_growth_risk: float
    risk_direction: str
    relative_asset_risk: float
    adjusted_crypto_value: float


class DCBPRARequest(BaseModel):
    asset_label: Optional[str] = Field(
        default=None,
        description="Identifier for the capital asset being assessed.",
    )
    actual_growth_rate: float = Field(
        ...,
        description="Real growth rate expressed as a percentage.",
    )
    last_year_growth_rate: float = Field(
        ...,
        description="Prior-year growth metric used for logarithmic performance.",
    )
    last_year_drawdown: float = Field(
        ...,
        description="Prior-year drawdown magnitude (absolute value applied).",
    )
    current_year_cumulative_growth: float = Field(
        ...,
        description="Current year cumulative growth metric.",
    )
    current_year_cumulative_drawdown: float = Field(
        ...,
        description="Current year cumulative drawdown magnitude.",
    )
    beta: float = Field(
        ...,
        description="Baseline CAPM beta.",
    )
    risk_free_rate: float = Field(
        ...,
        description="Risk-free rate R_f.",
    )
    market_return_rate: float = Field(
        ...,
        description="Market return R_m.",
    )
    months_elapsed: Optional[int] = Field(
        default=None,
        ge=0,
        le=12,
        description="Optional number of months elapsed in the fiscal year.",
    )


class DCBPRAResponse(BaseModel):
    asset_label: Optional[str]
    growth_percentage_factor: float
    real_growth_adjustment: float
    last_year_average_performance: float
    current_year_log_ratio: float
    monthly_growth_risk: float
    risk_adjustment_component: float
    risk_direction: str
    adjusted_beta: float
    baseline_capm_return: float
    adjusted_expected_return: float


class PSRASRequest(BaseModel):
    portfolio_label: Optional[str] = Field(
        default=None,
        description="Identifier for the insurance/service revenue cohort.",
    )
    prepaid_cost_average_1y: float = Field(..., description="Average prepaid cost during the prior year.")
    subscriber_count: float = Field(..., description="Subscriber count considered for evaluation.")
    prepaid_cost_total_1y: float = Field(..., description="Total prepaid cost over the past year.")
    new_contract_count: float = Field(..., description="Number of new contracts signed in the period.")
    retained_contract_count: float = Field(..., description="Number of contracts retained from prior periods.")
    new_subscriber_total_payment: float = Field(
        ..., description="Total payments from new subscribers (excluding quick re-signs)."
    )
    new_subscriber_count: float = Field(..., description="Count of new subscribers contributing to payments.")
    total_customer_payments: float = Field(..., description="Total customer payments in the evaluation period.")
    cancelled_customer_payments: float = Field(
        ..., description="Payments made by customers who cancelled during the period."
    )
    total_subscribers_in_period: float = Field(..., description="Total subscriber base during the period.")
    cancelled_customers_in_period: float = Field(..., description="Number of cancellations in the period.")
    total_prepaid_and_unearned: float = Field(..., description="Prepaid expenses and unearned revenue to recognise.")
    total_contract_deposits: float = Field(..., description="Contract deposits generated in the period.")
    current_year_yield: float = Field(..., description="Current year revenue yield applied to deposits.")
    covariance_contract_equity_vs_prepaid: float = Field(
        ..., description="Covariance of contract-holder equity adjustment vs prepaid totals."
    )
    variance_contract_equity_adjustment: float = Field(
        ..., description="Variance of contract-holder equity adjustment metric."
    )


class PSRASResponse(BaseModel):
    portfolio_label: Optional[str]
    assumed_revenue_recognition_rate: float
    new_subscriber_average_payment: float
    existing_subscriber_average_payment: float
    payment_comparison_index: float
    payment_index_baseline_amount: float
    pure_performance_break_even: float
    final_recognised_revenue: float


class LSMRVRequest(BaseModel):
    evaluation_label: Optional[str] = Field(
        default=None,
        description="Identifier for the derivative revaluation scenario.",
    )
    price_band_count_a: float = Field(..., gt=0, description="Number of price bands for asset A.")
    price_band_count_b: float = Field(..., gt=0, description="Number of price bands for asset B.")
    highest_preference_a: float = Field(..., description="Top preferred price level for asset A.")
    highest_preference_b: float = Field(..., description="Top preferred price level for asset B.")
    last_evaluation_growth_a: float = Field(..., description="Growth rate for asset A at the last evaluation.")
    last_evaluation_growth_b: float = Field(..., description="Growth rate for asset B at the last evaluation.")
    price_band_criterion_count: float = Field(..., description="Number of price band criteria applied.")
    total_standard_usage: float = Field(..., description="Total standards used for assets A and B.")
    standard_sample_size: float = Field(..., description="Total number of market standards n.")
    returns_a: List[float] = Field(..., min_length=2, description="Return series for asset A.")
    returns_b: List[float] = Field(..., min_length=2, description="Return series for asset B.")
    roi: float = Field(..., description="Return on investment multiplier.")
    operating_profit_previous: float = Field(..., description="Prior period operating profit.")
    accounts_receivable_previous: float = Field(..., description="Prior period accounts receivable.")
    market_price: float = Field(..., description="Current market price reference.")
    actual_cash_flow: float = Field(..., description="Actual cash flow observed.")
    estimated_cash_flow: float = Field(..., description="Estimated cash flow for evaluation.")
    noise_factor: float = Field(..., description="Noise adjustment ε.")
    discount_rate: float = Field(..., description="Discount rate δ.")
    current_investment_cash_flow: float = Field(
        ...,
        description="Current cash flow arising from investment activities.",
    )
    current_total_cash_flow: float = Field(..., description="Current total cash flow.")
    previous_investment_cash_flow: float = Field(
        ...,
        description="Previous period investment cash flow.",
    )
    previous_covariance: float = Field(
        ...,
        description="Covariance measured at the previous evaluation.",
    )


class LSMRVResponse(BaseModel):
    evaluation_label: Optional[str]
    probability_distribution_a: float
    probability_distribution_b: float
    growth_correction_value: float
    cumulative_adjustment_value: float
    expected_adjustment_value: float
    final_adjustment_amount: float
