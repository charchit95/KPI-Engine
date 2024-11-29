# app/main.py

from fastapi import FastAPI, Depends, HTTPException
from src.app.db import get_connection
from src.app.kpi_engine.kpi_engine import KPIEngine
from src.app.kpi_engine.kpi_request import KPIRequest
from src.app.kpi_engine.kpi_response import KPIResponse
import uvicorn


app = FastAPI()


def start():
    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8000, reload=True)


@app.post("/kpi/")
async def get_kpi(
    request: KPIRequest,
    db=Depends(get_connection),
) -> KPIResponse:
    """
    Endpoint to get a calculated KPI by item_id using data from two databases.
    """
    try:
        print("Request", request)
        return KPIEngine.compute(db, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")
