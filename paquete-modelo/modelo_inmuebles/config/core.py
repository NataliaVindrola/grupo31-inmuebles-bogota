"""Lectura de config.yml y rutas del paquete."""
from __future__ import annotations

from pathlib import Path

import yaml

import modelo_inmuebles

PAQUETE_RAIZ = Path(modelo_inmuebles.__file__).resolve().parent
CONFIG_FILE = PAQUETE_RAIZ / "config.yml"
TRAINED_DIR = PAQUETE_RAIZ / "trained"


def cargar_config(ruta: Path | str = CONFIG_FILE) -> dict:
    """Lee config.yml y verifica que estén las secciones que usan el entrenamiento y la predicción."""
    with open(ruta, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    faltan = [s for s in ("datos", "semilla", "rango", "reventa") if s not in cfg]
    if faltan:
        raise ValueError(f"config.yml no tiene las secciones {faltan}")
    for modelo in ("rango", "reventa"):
        for clave in ("variables", "hiperparametros"):
            if clave not in cfg[modelo]:
                raise ValueError(f"config.yml: falta {modelo}.{clave}")
    return cfg


config = cargar_config()
