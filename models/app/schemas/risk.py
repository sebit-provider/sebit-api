from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class CPRMRequest(BaseModel):
    exposure_id: Optional[str] = None
    allowance_for_bad_debts: float = Field(..., gt=0)
    total_bond_related_assets: float = Field(..., gt=0)
    bad_debt_amount: float = Field(..., gt=0)
    transaction_value_per_bond_unit: float = Field(..., gt=0)
    total_convertible_bond_transaction_value: float = Field(..., gt=0)
    stock_purchase_transaction_value: float = Field(..., gt=0)
    stock_sale_transaction_value: float = Field(..., gt=0)
    total_scope_bonds_for_conversion: float = Field(..., gt=0)
    current_debt_repayments: float = Field(..., gt=0)
    number_of_debt_repayments: int = Field(..., gt=0)
    total_convertible_bond_purchases: float = Field(..., gt=0)
    total_convertible_bond_sales: float = Field(..., gt=0)
    total_number_purchase_transactions: int = Field(..., gt=0)
    total_number_sale_transactions: int = Field(..., gt=0)
    total_bond_transactions_value: float = Field(..., gt=0)
    total_stock_transaction_value: float = Field(..., gt=0)
    value_of_convertible_bond_products: float = Field(..., gt=0)
    total_debt_repayment_for_trigger: Optional[float] = Field(
        default=None,
        gt=0,
        description="If provided, overrides current_debt_repayments in trigger calculations.",
    )
    rate_trigger_threshold: float = Field(
        default=0.10,
        ge=0,
        description="Convertible bond rate threshold that activates trigger calculations.",
    )

    @model_validator(mode="after")
    def _validate_transaction_counts(self) -> "CPRMRequest":
        total_trades = self.total_number_purchase_transactions + self.total_number_sale_transactions
        if total_trades <= 0:
            raise ValueError("Total number of purchase and sale transactions must be greater than zero.")
        if self.stock_sale_transaction_value <= 0 or self.stock_purchase_transaction_value <= 0:
            raise ValueError("Stock transaction values must be greater than zero for logarithmic calculations.")
        return self


class CPRMResponse(BaseModel):
    exposure_id: Optional[str]
    assumed_bad_debt_occurrence_rate: float
    convertible_bond_rate: float
    convertible_bond_first_amount: float
    average_past_bad_debt_recovery: float
    average_convertible_bond_price: float
    additional_adjustment_beta: float
    final_convertible_bond_amount: float
    trigger_applied: bool
    convertible_bond_rate_adjustment: Optional[float]
    final_adjusted_convertible_bond_rate: float


class COCIMQuarterData(BaseModel):
    quarter_index: int = Field(..., ge=1)
    pre_compound_balance: float = Field(..., description="Balance before quarterly compounding adjustments.")
    post_compound_balance: float = Field(..., description="Balance after quarterly compounding adjustments.")
    current_quarter_yield: float = Field(..., description="Current quarter yield (rate basis).")
    previous_quarter_yield: float = Field(..., description="Previous quarter yield (rate basis).")
    previous_quarter_rate: float = Field(..., description="Previous quarter policy/market rate.")
    current_quarter_rate: float = Field(..., description="Current quarter policy/market rate.")


class COCIMRequest(BaseModel):
    portfolio_label: Optional[str] = None
    oci_account_balance: float = Field(..., description="Current balance of the OCI account being evaluated.")
    total_oci_amount: float = Field(..., gt=0, description="Total aggregated amount of all OCI items under review.")
    policy_rate: float = Field(..., description="Reference interest rate (e.g., central bank rate).")
    useful_life_years_remaining: float = Field(..., gt=0, description="Remaining years until OCI realization.")
    initial_recognition_amount: float = Field(..., gt=0, description="Opening recognition amount for the OCI account.")
    year_end_balance: float = Field(..., gt=0, description="OCI account balance at the end of the year.")
    quarterly_data: List[COCIMQuarterData] = Field(
        default_factory=list,
        description="Sequential quarterly measurements used for compound adjustments."
    )

    @model_validator(mode="after")
    def _validate_quarter_indices(self) -> "COCIMRequest":
        indices = [q.quarter_index for q in self.quarterly_data]
        if indices and sorted(indices) != indices:
            raise ValueError("quarterly_data entries must be ordered by ascending quarter_index.")
        return self


class COCIMQuarterResult(BaseModel):
    quarter_index: int
    adjustment_value: float
    pre_compound_balance: float
    post_compound_balance: float


class COCIMResponse(BaseModel):
    portfolio_label: Optional[str]
    account_ratio: float
    initial_compound_measurement: float
    quarterly_adjustments: List[COCIMQuarterResult]
    annual_compound_growth_rate: float
    compound_growth_trigger_applied: bool
    compound_adjustment_amount: float
    final_adjusted_balance: float


class FAREXRequest(BaseModel):
    contract_id: Optional[str] = None
    base_currency_amount: float = Field(..., gt=0)
    spot_rate: float = Field(..., gt=0)
    forecast_rate: float = Field(..., gt=0)
    inflation_rate_home: float = Field(..., ge=-1)
    inflation_rate_foreign: float = Field(..., ge=-1)
    hedge_ratio: float = Field(
        default=1.0,
        gt=0,
        description="Portion of exposure hedged, as referenced in SEBIT-FAREX.",
    )
    last_year_prev_month_export: float = Field(..., gt=0)
    last_year_prev_month_import: float = Field(..., gt=0)
    last_year_current_month_export: float = Field(..., gt=0)
    last_year_current_month_import: float = Field(..., gt=0)
    current_year_prev_month_export: float = Field(..., gt=0)
    current_year_prev_month_import: float = Field(..., gt=0)


class FAREXResponse(BaseModel):
    contract_id: Optional[str]
    last_year_trade_ratio: float
    current_year_trade_ratio: float
    export_import_beta: float
    adjustment_indicator: float
    inflation_adjusted_rate: float
    final_adjusted_rate: float
    revaluation_amount: float
