from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CEEMRequest(BaseModel):
    expense_label: Optional[str] = None
    cumulative_usage_units: float = Field(..., gt=0, description="Total consumable units used to date.")
    cumulative_usage_days: float = Field(..., gt=0, description="Number of days over which the consumable was used.")
    current_unit_cost: float = Field(..., gt=0, description="Current unit cost of the consumable asset.")
    quantitative_usage_limit: Optional[float] = Field(
        default=None,
        gt=0,
        description="Optional contractual usage limit for the consumable asset.",
    )
    previous_year_standard_usage_value: float = Field(
        ...,
        gt=0,
        description="Standard usage value calculated for the previous period.",
    )
    useful_life_years: float = Field(..., gt=0, description="Base useful life in years (typically starts at 1).")
    elapsed_years: float = Field(
        default=0.0,
        ge=0.0,
        description="Elapsed years since measurement began; added to useful life from year two onward.",
    )
    beta: float = Field(
        default=1.0,
        description="CAPM-style beta used for market sensitivity.",
    )

    @model_validator(mode="after")
    def _check_usage(self) -> "CEEMRequest":
        if self.quantitative_usage_limit is not None and self.quantitative_usage_limit <= 0:
            raise ValueError("quantitative_usage_limit must be positive when provided.")
        return self


class CEEMResponse(BaseModel):
    expense_label: Optional[str]
    daily_average_usage_units: float
    standard_usage_value_non_quantitative: float
    standard_usage_value_quantitative: Optional[float]
    selected_standard_usage_value: float
    total_consumable_usage_value: float
    adjusted_consumable_usage_value: float
    usage_change_rate: float
    market_change_index: float
    market_sensitivity_value: float
    final_revaluation_value: float


class BDMRequest(BaseModel):
    bond_label: Optional[str] = None
    bond_issue_price: float = Field(..., gt=0, description="Original issue price of the bond.")
    bond_contract_days: float = Field(..., gt=0, description="Total contract days (e.g., years * 365).")
    elapsed_days_since_contract: float = Field(..., ge=0, description="Elapsed days since contract inception.")
    previous_valuation: Optional[float] = Field(
        default=None,
        gt=0,
        description="Valuation from the previous amortisation evaluation.",
    )
    current_fair_value: float = Field(..., gt=0, description="Current fair value (PV) at evaluation date.")

    @model_validator(mode="after")
    def _validate_elapsed(self) -> "BDMRequest":
        if self.elapsed_days_since_contract > self.bond_contract_days:
            raise ValueError("elapsed_days_since_contract cannot exceed bond_contract_days.")
        return self


class BDMResponse(BaseModel):
    bond_label: Optional[str]
    daily_estimated_usage: float
    estimated_value_ps: float
    market_beta: float
    final_book_value: float
    interest_cost: float
    interest_type: str


class BELMRequest(BaseModel):
    debtor_label: Optional[str] = None
    debtor_total_amount: float = Field(..., gt=0, description="Outstanding debt amount for the counterparty.")
    remaining_years: float = Field(..., gt=0, description="Years remaining until expected settlement.")
    elapsed_days: float = Field(..., ge=0, description="Elapsed days since loan inception.")
    actual_repayment_amount: float = Field(..., ge=0, description="Actual repayment amount observed at evaluation.")
    interest_rate: float = Field(..., ge=0, description="Nominal interest rate on the debt.")
    total_debt_balance_all_counterparties: float = Field(
        ...,
        gt=0,
        description="Aggregate remaining debt balance for all counterparties.",
    )
    last_year_counterparty_repayment: float = Field(
        ...,
        ge=0,
        description="Previous year's repayment amount for the counterparty.",
    )
    last_year_total_repayment_all: float = Field(
        ...,
        gt=0,
        description="Aggregate previous-year repayment amount for all counterparties.",
    )


class BELMResponse(BaseModel):
    debtor_label: Optional[str]
    daily_estimated_repayment: float
    expected_repayment_at_evaluation: float
    interest_rate_adjustment: float
    actual_interest_cost: float
    preliminary_bad_debt_ratio: float
    final_bad_debt_ratio: float
