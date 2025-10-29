from fastapi import APIRouter

from ...schemas.analysis import (
    CPMRVRequest,
    CPMRVResponse,
    DCBPRARequest,
    DCBPRAResponse,
    TCTBeamRequest,
    TCTBeamResponse,
)
from ...services.analysis import calculate_cpmrv, calculate_dcbpra, calculate_tct_beam

router = APIRouter()


@router.post(
    "/tct-beam",
    response_model=TCTBeamResponse,
    summary="Trigonomatric Cost Tracking & Break-Even Analysis Model",
)
def run_tct_beam(payload: TCTBeamRequest) -> TCTBeamResponse:
    """
    Run the SEBIT-TCT-BEAM model to analyse fixed/variable cost dynamics and break-even behaviour.
    """
    return calculate_tct_beam(payload)


@router.post(
    "/cpmrv",
    response_model=CPMRVResponse,
    summary="Crypto Performance-based Real Value Model",
)
def run_cpmrv(payload: CPMRVRequest) -> CPMRVResponse:
    """
    Compute the RSI-based real value adjustment for a crypto asset under SEBIT-CPMRV.
    """
    return calculate_cpmrv(payload)


@router.post(
    "/dcbpra",
    response_model=DCBPRAResponse,
    summary="Dynamic CAPM with Percentage-adjusted Relative Strength",
)
def run_dcbpra(payload: DCBPRARequest) -> DCBPRAResponse:
    """
    Calculate the CAPM-based adjusted return using SEBIT-DCBPRA logic.
    """
    return calculate_dcbpra(payload)

