from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Iterable, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from pydantic_settings import BaseSettings

from ...schemas.analysis import (
    CPMRVRequest,
    DCBPRARequest,
    LSMRVRequest,
    PSRASRequest,
    TCTBeamRequest,
)
from ...schemas.asset import DDARequest, LAMRequest, RVMRequest
from ...schemas.expense import BDMRequest, BELMRequest, CEEMRequest
from ...schemas.risk import COCIMRequest, CPRMRequest, FAREXRequest
from ...services.analysis import (
    calculate_cpmrv,
    calculate_dcbpra,
    calculate_lsmrv,
    calculate_psras,
    calculate_tct_beam,
)
from ...services.asset import (
    calculate_dynamic_depreciation,
    calculate_lease_amortization,
    calculate_resource_valuation,
)
from ...services.expense import calculate_bdm, calculate_belm, calculate_ceem
from ...services.risk import calculate_cocim, calculate_cprm, calculate_farex
from ...services.summary_bridge import bridge_and_send_summary


class BridgeSettings(BaseSettings):
    """Environment configuration for the summary bridge."""

    summary_base_url: str = Field(..., alias="SUMMARY_BASE_URL")
    internal_token: str = Field(..., alias="SUMMARY_INTERNAL_TOKEN")

    model_config = {"extra": "ignore"}


_settings: BridgeSettings | None = None


def get_settings() -> BridgeSettings:
    """Load bridge settings lazily so tests can override them."""
    global _settings
    if _settings is None:
        _settings = BridgeSettings()
    return _settings


async def execute_model(func: Callable[[Any], Any], payload: Any) -> Dict[str, Any]:
    """Execute a SEBIT model in a worker thread and normalise the response."""
    try:
        result = await asyncio.to_thread(func, payload)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Model returned unsupported response type.",
    )


async def call_summary(
    endpoint: str,
    model_output: Dict[str, Any],
    settings: BridgeSettings,
) -> Dict[str, Any]:
    """Forward the model output to the summary service and return its response."""
    try:
        return await bridge_and_send_summary(
            summary_base_url=settings.summary_base_url,
            internal_token=settings.internal_token,
            model_outputs=[(endpoint, model_output)],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


router = APIRouter(prefix="/auto", tags=["SEBIT Bridge"])


@router.post("/asset/dda", summary="Run SEBIT-DDA and forward the result to the summary service")
async def run_asset_dda(payload: DDARequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_dynamic_depreciation, payload)
    return await call_summary("asset/dda", model_output, settings)


@router.post("/asset/lam", summary="Run SEBIT-LAM and forward the result to the summary service")
async def run_asset_lam(payload: LAMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_lease_amortization, payload)
    return await call_summary("asset/lam", model_output, settings)


@router.post("/asset/rvm", summary="Run SEBIT-RVM and forward the result to the summary service")
async def run_asset_rvm(payload: RVMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_resource_valuation, payload)
    return await call_summary("asset/rvm", model_output, settings)


@router.post("/expense/ceem", summary="Run SEBIT-CEEM and forward the result to the summary service")
async def run_expense_ceem(payload: CEEMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_ceem, payload)
    return await call_summary("expense/ceem", model_output, settings)


@router.post("/expense/bdm", summary="Run SEBIT-BDM and forward the result to the summary service")
async def run_expense_bdm(payload: BDMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_bdm, payload)
    return await call_summary("expense/bdm", model_output, settings)


@router.post("/expense/belm", summary="Run SEBIT-BELM and forward the result to the summary service")
async def run_expense_belm(payload: BELMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_belm, payload)
    return await call_summary("expense/belm", model_output, settings)


@router.post("/risk/cprm", summary="Run SEBIT-CPRM and forward the result to the summary service")
async def run_risk_cprm(payload: CPRMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_cprm, payload)
    return await call_summary("risk/cprm", model_output, settings)


@router.post("/risk/c-ocim", summary="Run SEBIT-C-OCIM and forward the result to the summary service")
async def run_risk_cocim(payload: COCIMRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_cocim, payload)
    return await call_summary("risk/c-ocim", model_output, settings)


@router.post("/risk/farex", summary="Run SEBIT-FAREX and forward the result to the summary service")
async def run_risk_farex(payload: FAREXRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_farex, payload)
    return await call_summary("risk/farex", model_output, settings)


@router.post("/analysis/tct-beam", summary="Run SEBIT-TCT-BEAM and forward the result to the summary service")
async def run_analysis_tct_beam(payload: TCTBeamRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_tct_beam, payload)
    return await call_summary("analysis/tct-beam", model_output, settings)


@router.post("/analysis/cpmrv", summary="Run SEBIT-CPMRV and forward the result to the summary service")
async def run_analysis_cpmrv(payload: CPMRVRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_cpmrv, payload)
    return await call_summary("analysis/cpmrv", model_output, settings)


@router.post("/analysis/dcbpra", summary="Run SEBIT-DCBPRA and forward the result to the summary service")
async def run_analysis_dcbpra(payload: DCBPRARequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_dcbpra, payload)
    return await call_summary("analysis/dcbpra", model_output, settings)


@router.post("/service/psras", summary="Run SEBIT-PSRAS and forward the result to the summary service")
async def run_service_psras(payload: PSRASRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_psras, payload)
    return await call_summary("service/psras", model_output, settings)


@router.post("/probability/lsmrv", summary="Run SEBIT-LSMRV and forward the result to the summary service")
async def run_probability_lsmrv(payload: LSMRVRequest, settings: BridgeSettings = Depends(get_settings)) -> Dict[str, Any]:
    model_output = await execute_model(calculate_lsmrv, payload)
    return await call_summary("probability/lsmrv", model_output, settings)
