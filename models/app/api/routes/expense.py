from fastapi import APIRouter

from ...schemas.expense import (CEEMRequest, CEEMResponse, BDMRequest, BDMResponse, BELMRequest, BELMResponse)
from ...services.expense import calculate_ceem, calculate_bdm, calculate_belm

router = APIRouter()


@router.post("/ceem", response_model=CEEMResponse, summary="Consumable Expense Evaluation Model")
def run_ceem(payload: CEEMRequest) -> CEEMResponse:
    """
    Evaluate consumable asset usage and produce SEBIT-CEEM metrics.
    """
    return calculate_ceem(payload)


@router.post("/bdm", response_model=BDMResponse, summary="Bond Depreciation Model")
def run_bdm(payload: BDMRequest) -> BDMResponse:
    """
    Evaluate bond depreciation using SEBIT-BDM formulas.
    """
    return calculate_bdm(payload)


@router.post("/belm", response_model=BELMResponse, summary="Bad Debt Expected Loss Model")
def run_belm(payload: BELMRequest) -> BELMResponse:
    """Estimate bad debt ratios using SEBIT-BELM."""
    return calculate_belm(payload)

