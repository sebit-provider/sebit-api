from fastapi import APIRouter

from ...schemas.risk import (
    COCIMRequest,
    COCIMResponse,
    CPRMRequest,
    CPRMResponse,
    FAREXRequest,
    FAREXResponse,
)
from ...services.risk import calculate_cocim, calculate_cprm, calculate_farex

router = APIRouter()


@router.post("/cprm", response_model=CPRMResponse, summary="Collateral-adjusted Probabilistic Risk")
def run_cprm(payload: CPRMRequest) -> CPRMResponse:
    """
    Assess collateral-adjusted exposure and losses using SEBIT-CPRM logic.
    """
    return calculate_cprm(payload)


@router.post(
    "/c-ocim",
    response_model=COCIMResponse,
    summary="Compound Other Comprehensive Income Model",
)
def run_cocim(payload: COCIMRequest) -> COCIMResponse:
    """
    Compute the evolution of other comprehensive income under SEBIT-C-OCIM.
    """
    return calculate_cocim(payload)


@router.post("/farex", response_model=FAREXResponse, summary="Foreign Adjustment & Real Exchange")
def run_farex(payload: FAREXRequest) -> FAREXResponse:
    """
    Derive the real exchange rate differential and hedged revaluation amount.
    """
    return calculate_farex(payload)
