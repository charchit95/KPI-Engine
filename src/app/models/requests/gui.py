from datetime import datetime

from pydantic import BaseModel


class RealTimeKPIRequest(BaseModel):
    """Represents a request for real-time KPI data with specific machines, operations,
    and aggregation details.

    :param name: The name of the KPI to be requested.
    :type name: str
    :param machines: A list of machines for which the KPI data is requested.
    :type machines: list
    :param operations: A list of operations related to the KPI request.
    :type operations: list
    :param time_aggregation: The time aggregation method
    :type time_aggregation: str
    :param start_date: The start date and time for the KPI data request (YYYY-MM-DD HH:MM:SS).
    :type start_date: datetime
    """
    name: str
    machines: list
    operations: list
    time_aggregation: str
    start_date: datetime  # (YYYY-MM-DD HH:MM:SS)
