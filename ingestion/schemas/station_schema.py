from datetime import date
from pydantic import BaseModel
from typing import Optional

class StationAPISchema(BaseModel):
    """
    Contrato de dados estrito para ingestão de estações.
    Garante que os dados da API possuem as chaves corretas e os tipos primitivos esperados.
    """
    code: str
    name: str
    basin: str
    latitude: float
    longitude: float
    
    # Campos opcionais que podem vir nulos da API
    altitude: Optional[float] = None
    state: Optional[str] = None
    city: Optional[str] = None
    station_type: Optional[str] = None 
    operator: Optional[str] = None 
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    missing_percentage: Optional[float] = None

    