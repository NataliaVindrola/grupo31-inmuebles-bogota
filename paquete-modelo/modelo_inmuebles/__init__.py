"""modelo_inmuebles: modelos de rango del valor y de reventa a 3 años para compraventas de Bogotá (Grupo 31)."""
from pathlib import Path

with open(Path(__file__).resolve().parent / "VERSION", encoding="utf-8") as _f:
    __version__ = _f.read().strip()
