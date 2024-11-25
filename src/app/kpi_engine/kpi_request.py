from datetime import datetime
from pydantic import BaseModel, validator
from src.app.kpi_engine import grammar


class KPIRequest(BaseModel):
    """
    KPI Request details for incoming requests. A request should contain:
    - KPI name
    - Machine name
    - Aggregation function
    - Start date
    - End date
    """

    # sono andato ad aggiungere operation e aggregation
    name: str
    machines: list
    operations: list
    time_aggregation: str
    start_date: datetime
    end_date: datetime
    step: int

    #devo inserire l'operazione e lo step

    @validator("start_date", "end_date", pre=True)
    def validate_datetime(cls, value):
        if not isinstance(value, datetime):
            raise ValueError("The date must be a datetime object.")
        return value

    @validator("name")
    def validate_name(cls, value):
        if not isinstance(value, str):
            raise ValueError("KPI name must be a string.")
        return value

    @validator("machines")
    def validate_machines(cls, value):
        if not isinstance(value, list):
            raise ValueError("Machine name must be a list.")
        return value
    
    
    @validator("operations")
    def validate_operations(cls, value):
        if not isinstance(value, list):
            raise ValueError("Operation name must be a list.")
        return value
    
    
    @validator("step")
    def validate_step(cls, value):
        if not isinstance(value, int):
            raise ValueError("The step must be a integer.")
        return value
    

    @validator("time_aggregation")
    def validate_time_aggregation(cls, value):
        if not isinstance(value, str):
            raise ValueError("Aggregation function must be a string.")
        if value not in grammar.aggregations:
            raise ValueError(
                f"Invalid aggregation function. Must be one of {grammar.aggregations}"
            )
        return value
