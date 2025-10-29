from fastapi import APIRouter

from ...schemas.analysis import LSMRVRequest, LSMRVResponse
from ...services.analysis import calculate_lsmrv

router = APIRouter()


@router.post(
    "/lsmrv",
    response_model=LSMRVResponse,
    summary="Linear Stochastic Monte Carlo Re-valuation Vector Model",
)
def run_lsmrv(payload: LSMRVRequest) -> LSMRVResponse:
    """
    Execute the SEBIT-LSMRV probability-based revaluation model for paired assets.
    """
    return calculate_lsmrv(payload)
