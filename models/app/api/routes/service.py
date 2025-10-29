from fastapi import APIRouter

from ...schemas.analysis import PSRASRequest, PSRASResponse
from ...services.analysis import calculate_psras

router = APIRouter()


@router.post(
    "/psras",
    response_model=PSRASResponse,
    summary="Presumed Service Revenue Accrual System",
)
def run_psras(payload: PSRASRequest) -> PSRASResponse:
    """
    Estimate insurance/service revenue recognition using SEBIT-PSRAS.
    """
    return calculate_psras(payload)

