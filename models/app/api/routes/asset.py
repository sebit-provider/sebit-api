from fastapi import APIRouter

from ...schemas.asset import DDARequest, DDAResponse, LAMRequest, LAMResponse, RVMRequest, RVMResponse
from ...services.asset import (
    calculate_dynamic_depreciation,
    calculate_lease_amortization,
    calculate_resource_valuation,
)

router = APIRouter()


@router.post("/dda", response_model=DDAResponse, summary="Dynamic Depreciation Algorithm")
def run_dynamic_depreciation(payload: DDARequest) -> DDAResponse:
    """
    Execute the SEBIT-DDA model with the provided asset parameters.

    Returns a depreciation schedule with yearly adjustments.
    """
    return calculate_dynamic_depreciation(payload)


@router.post("/lam", response_model=LAMResponse, summary="Lease Amortisation Model")
def run_lease_amortisation(payload: LAMRequest) -> LAMResponse:
    """
    Generate a lease amortisation schedule aligned with SEBIT-LAM principles.
    """
    return calculate_lease_amortization(payload)


@router.post("/rvm", response_model=RVMResponse, summary="Resource Valuation Model")
def run_resource_valuation(payload: RVMRequest) -> RVMResponse:
    """
    Evaluate the present value of projected resource cashflows following SEBIT-RVM.
    """
    return calculate_resource_valuation(payload)
