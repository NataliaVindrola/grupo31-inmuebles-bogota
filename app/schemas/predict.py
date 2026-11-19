from typing import Any, Literal, Optional,List

from pydantic import BaseModel, Field

# Esquema de lo que el tablero le manda a la API
class RangoEntrada(BaseModel):
    zona: Literal["Norte", "Centro", "Sur"]
    anio: int = Field(ge=2021, le=2026, description="Año de la oferta")
    precio_musd: float = Field(gt=0, description="Precio de la oferta en millones de pesos constantes")

    model_config = {"json_schema_extra": {"example": {"zona": "Sur", "anio": 2023, "precio_musd": 520}}}

# ---------------------------------------------------------------------- rango
# Esquema para resultados
class RangoHistorico(BaseModel):
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    n: int
    mes_ref: str


class RangoModelo(BaseModel):
    p10: float
    p50: float
    p90: float


class RangoRespuesta(BaseModel):
    zona: str
    anio: int
    precio_musd: float
    estado: str
    historico: RangoHistorico
    modelo: Optional[RangoModelo] = None

# ---------------------------------------------------------------------- reventa
# Esquema reventa
class ReventaEntrada(BaseModel):
    zona: Literal["Norte", "Centro", "Sur"]
    tipo_predio: Literal["URBANO", "RURAL", "SIN INFORMACION"] = "URBANO"
    ventas_previas: int = Field(ge=0, le=50, description="Número de ventas previas del predio")

    model_config = {"json_schema_extra": {"example": {"zona": "Sur", "tipo_predio": "URBANO", "ventas_previas": 2}}}


class ReventaRespuesta(BaseModel):
    zona: str
    tipo_predio: str
    ventas_previas: int
    prob_reventa_3a: float
    prob_zona_3a: Optional[float] = None



# ---------------------------------------------------------------------- segmentos
class SegmentoRecomendado(BaseModel):
    posicion: int
    zona: str
    q: int = Field(description="Rango de valor de la primera venta (quintil 1 a 5)")
    rango_min_musd: float
    rango_max_musd: float
    n: int = Field(description="Pares de ventas repetidas que respaldan la cifra")
    retorno_real_anual: float = Field(description="Mediana del retorno real anual (0.05 = 5 %)")
    ic_inf: float
    ic_sup: float
    prob_reventa_3a_zona: float = Field(description="Probabilidad de reventa a 3 años promedio de la zona")


class SegmentosRespuesta(BaseModel):
    criterio: str
    segmentos: List[SegmentoRecomendado]
