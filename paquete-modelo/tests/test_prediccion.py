"""Pruebas del paquete: usan los modelos guardados en modelo_inmuebles/trained/ (no necesitan los datos)."""
import json

import pytest

from modelo_inmuebles.predict import TIPOS_PREDIO, ZONAS, predecir_rango, predecir_reventa


@pytest.mark.parametrize("zona", ZONAS)
@pytest.mark.parametrize("anio", [2021, 2022, 2023])
def test_rango_ordenado_y_plausible(zona, anio, version):
    r = predecir_rango(zona, anio)
    assert r["version"] == version
    assert 0 < r["p10"] <= r["p50"] <= r["p90"]
    # valores en millones de pesos constantes: una vivienda típica de Bogotá está entre 20 y 3.000 M$
    assert 20 < r["p50"] < 3000


def test_rango_distingue_zonas():
    medianas = {z: predecir_rango(z, 2023)["p50"] for z in ZONAS}
    assert medianas["Norte"] > medianas["Sur"]          # el Norte es la zona más cara del registro


def test_rango_zona_invalida():
    with pytest.raises(ValueError):
        predecir_rango("Chapinero", 2023)


@pytest.mark.parametrize("zona", ZONAS)
@pytest.mark.parametrize("tipo", TIPOS_PREDIO)
def test_reventa_probabilidad(zona, tipo, version):
    r = predecir_reventa(zona, tipo, 1, "2023-06-15")
    assert r["version"] == version
    assert 0 < r["probabilidad_3a"] < 1


def test_reventa_entradas_invalidas():
    with pytest.raises(ValueError):
        predecir_reventa("Norte", "CASA", 0)
    with pytest.raises(ValueError):
        predecir_reventa("Norte", "URBANO", -1)


@pytest.mark.parametrize("modelo", ["rango", "reventa"])
def test_metadatos_con_metricas(modelo, version, dir_modelos):
    meta = json.loads((dir_modelos / modelo / version / "metadata.json").read_text(encoding="utf-8"))
    assert meta["version"] == version
    assert "metricas" in meta and "linea_base" in meta
    if modelo == "rango":
        assert 0.75 < meta["metricas"]["cobertura_p10_p90"] < 0.90      # intervalo p10-p90: cerca del 80 % nominal
    else:
        assert meta["metricas"]["auc"] > meta["linea_base"]["auc"]       # supera a la tasa por zona
