from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class DDARequest(BaseModel):
    asset_label: Optional[str] = Field(
        default=None,
        description="Identifier for the asset; useful when batching requests.",
    )
    acquisition_cost: float = Field(..., gt=0, description="Gross acquisition cost.")
    salvage_value: float = Field(
        default=0.0,
        ge=0,
        description="Expected residual value at the end of useful life.",
    )
    useful_life_years: int = Field(..., gt=0, description="Depreciable life in years.")
    adjustment_factor: float = Field(
        default=1.0,
        gt=0,
        description=(
            "Dynamic scaling factor reflecting market/operational adjustments "
            "described in the SEBIT-DDA specification."
        ),
    )
    method: Literal["double_declining", "straight_line"] = Field(
        default="double_declining",
        description="Baseline depreciation method prior to dynamic adjustments.",
    )
    planned_usage_days_per_year: Optional[List[int]] = Field(
        default=None,
        description="Planned usage days for each year of the asset's useful life.",
    )
    actual_usage_days_per_year: Optional[List[int]] = Field(
        default=None,
        description="Actual usage days realised for each year of the useful life.",
    )
    unused_days_per_year: Optional[List[int]] = Field(
        default=None,
        description="Optional override for non-operating days deducted from planned usage.",
    )
    market_price_series: Optional[List[float]] = Field(
        default=None,
        description=(
            "Reference market price series for the asset's class. "
            "If provided, length should be useful_life_years + 1 including the opening reference."
        ),
    )
    usage_elasticity: float = Field(
        default=1.0,
        description="Elasticity factor applied when scaling market shocks to usage (SEBIT-DDA step 5).",
    )
    beta: float = Field(
        default=1.0,
        description="CAPM-style beta used to weight market sensitivity (SEBIT-DDA step 5).",
    )

    @model_validator(mode="after")
    def _validate_lengths(self) -> "DDARequest":
        years = self.useful_life_years
        for name, series in (
            ("planned_usage_days_per_year", self.planned_usage_days_per_year),
            ("actual_usage_days_per_year", self.actual_usage_days_per_year),
            ("unused_days_per_year", self.unused_days_per_year),
        ):
            if series is not None and len(series) != years:
                raise ValueError(f"{name} must have exactly {years} entries.")
        if self.market_price_series is not None and len(self.market_price_series) not in {years, years + 1}:
            raise ValueError(
                "market_price_series must have either useful_life_years or useful_life_years + 1 entries."
            )
        return self


class DDAScheduleEntry(BaseModel):
    year_index: int = Field(..., ge=1)
    opening_book_value: float
    depreciation_expense: float
    closing_book_value: float
    baseline_revaluation_value: float = Field(
        ...,
        description="Revaluation amount before trigger adjustments (Step 6).",
    )
    final_revaluation_value: float = Field(
        ...,
        description="Carrying amount after applying trigger logic.",
    )
    revaluation_gain_loss: float = Field(
        ...,
        description="Recognised revaluation gain/loss for the period.",
    )
    trigger_stage: Optional[str] = Field(
        default=None,
        description="Applied trigger identifier (6-1/6-2/6-3/6-3-1) if any.",
    )
    unrecognised_revaluation: float = Field(
        ...,
        description="Portion of revaluation gain/loss not recognised under trigger limits.",
    )
    adjustment_multiplier: float = Field(
        ...,
        description="Effective multiplier applied to the baseline depreciation for the year.",
    )
    usage_ratio: float = Field(
        ...,
        description="Relative variance between actual and planned usage for the year.",
    )
    market_sensitivity: float = Field(
        ...,
        description="Exponentiated market sensitivity factor applied to the year.",
    )


class DDAResponse(BaseModel):
    asset_label: Optional[str]
    schedule: List[DDAScheduleEntry]
    total_depreciation: float
    total_revaluation_gain_loss: float
    total_unrecognised_revaluation: float


class LAMRequest(BaseModel):
    lease_label: Optional[str] = None
    initial_asset_value: float = Field(..., gt=0)
    lease_term_years: int = Field(
        ...,
        gt=0,
        description="Number of evaluation periods (typically years) to project.",
    )
    discount_rate: float = Field(
        ...,
        gt=0,
        description="Annual nominal discount rate (implicit interest rate).",
    )
    residual_value: float = Field(default=0.0, ge=0)
    planned_usage_days_per_period: Optional[List[int]] = Field(
        default=None,
        description="Planned usage days for each evaluation period.",
    )
    actual_usage_days_per_period: Optional[List[int]] = Field(
        default=None,
        description="Actual usage days realised for each evaluation period.",
    )
    unused_days_per_period: Optional[List[int]] = Field(
        default=None,
        description="Days intentionally unused or unavailable for each period.",
    )
    actual_daily_usage_hours: Optional[List[float]] = Field(
        default=None,
        description="Actual daily usage hours per period (used for usage ratio).",
    )
    standard_daily_usage_hours: Optional[List[float]] = Field(
        default=None,
        description="Standard (planned) daily usage hours per period.",
    )
    market_fair_values: Optional[List[float]] = Field(
        default=None,
        description="Fair value observations per evaluation. Provide length = periods or periods + 1 (including opening).",
    )
    ifrs_revaluation_losses: Optional[List[float]] = Field(
        default=None,
        description="Revaluation losses computed under IFRS baseline per period.",
    )
    usage_elasticity: float = Field(
        default=1.0,
        description="Elasticity factor scaling market shocks to usage (per documentation).",
    )
    beta: float = Field(
        default=1.0,
        description="CAPM beta applied in market sensitivity computation.",
    )
    accumulated_depreciation_opening: float = Field(
        default=0.0,
        ge=0.0,
        description="Accumulated depreciation recognised before the first evaluation period.",
    )

    @model_validator(mode="after")
    def _validate_usage_lengths(self) -> "LAMRequest":
        periods = self.lease_term_years
        for name, series in (
            ("planned_usage_days_per_period", self.planned_usage_days_per_period),
            ("actual_usage_days_per_period", self.actual_usage_days_per_period),
            ("unused_days_per_period", self.unused_days_per_period),
            ("actual_daily_usage_hours", self.actual_daily_usage_hours),
            ("standard_daily_usage_hours", self.standard_daily_usage_hours),
            ("ifrs_revaluation_losses", self.ifrs_revaluation_losses),
        ):
            if series is not None and len(series) != periods:
                raise ValueError(f"{name} must have exactly {periods} entries.")
        if self.market_fair_values is not None and len(self.market_fair_values) not in {periods, periods + 1}:
            raise ValueError("market_fair_values must have either periods or periods + 1 entries.")
        return self


class LAMScheduleEntry(BaseModel):
    period_index: int = Field(..., ge=1)
    opening_balance: float
    closing_balance: float
    daily_lease_amortization: float = Field(
        ...,
        description="Daily lease amortization amount (Step 1).",
    )
    usage_ratio: float = Field(
        ...,
        description="Usage variance ratio (Step 2).",
    )
    interest_expense: float = Field(
        ...,
        description="Interest expense derived from initial acquisition cost and discount rate (Step 3).",
    )
    market_change_index: float = Field(
        ...,
        description="Market change index r (Step 4).",
    )
    market_sensitivity: float = Field(
        ...,
        description="Market sensitivity multiplier (Step 5).",
    )
    baseline_revaluation_value: float = Field(
        ...,
        description="Revaluation result before trigger adjustments (Step 6).",
    )
    trigger_stage: Optional[str] = Field(
        default=None,
        description="Applied trigger identifier (6-1/6-2/6-3/6-3-1) if any.",
    )
    post_trigger_value: float = Field(
        ...,
        description="Value after trigger processing or baseline if no trigger applied.",
    )
    revaluation_gain_loss: float = Field(
        ...,
        description="Post-trigger value minus opening balance.",
    )
    termination_adjustment: float = Field(
        ...,
        description=(
            "Amount deferred to lease termination settlement when revaluation cannot "
            "be recognised under the model's IFRS limits."
        ),
    )


class LAMResponse(BaseModel):
    lease_label: Optional[str]
    schedule: List[LAMScheduleEntry]
    total_revaluation_gain_loss: float
    total_interest_expense: float
    total_termination_adjustment: float


class RVMRequest(BaseModel):
    resource_label: Optional[str] = None
    cumulative_extraction_amount: float = Field(
        ...,
        gt=0,
        description="Cumulative amount of resource extracted since the last evaluation.",
    )
    cumulative_extraction_days: float = Field(
        ...,
        gt=0,
        description="Number of extraction days corresponding to the cumulative amount.",
    )
    total_extraction_days_at_evaluation: Optional[float] = Field(
        default=None,
        gt=0,
        description="Total number of extraction days considered at evaluation (defaults to cumulative_extraction_days).",
    )
    current_unit_extraction_value: float = Field(
        ...,
        gt=0,
        description="Current market unit value for the resource (e.g., price per barrel).",
    )
    previous_extraction_value: Optional[float] = Field(
        default=None,
        gt=0,
        description="Total extraction value calculated at the previous evaluation date.",
    )
    total_years_of_useful_life: float = Field(
        ...,
        gt=0,
        description="Total useful life expressed in years for the resource asset.",
    )
    elapsed_years: float = Field(
        default=0.0,
        ge=0.0,
        description="Elapsed years since the resource entered service (used for exponent adjustments).",
    )
    beta: float = Field(
        default=1.0,
        description="CAPM beta factor referenced by the model.",
    )

    @model_validator(mode="after")
    def _validate_rvm_inputs(self) -> "RVMRequest":
        if self.total_extraction_days_at_evaluation is None:
            self.total_extraction_days_at_evaluation = self.cumulative_extraction_days
        return self


class RVMResponse(BaseModel):
    resource_label: Optional[str]
    daily_average_extraction: float
    standard_extraction_value: float
    total_extraction_value: float
    extraction_rate: float
    market_change_index: float
    market_sensitivity: float
    final_revaluation_value: float
