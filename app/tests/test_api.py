import pytest
from fastapi.testclient import TestClient
from dashboard import servicios

from app.config import settings

PREFIJO = settings.API_V1_STR  # "/api/v1"

PAYLOAD_RANGO = {"zona": "Sur", "anio": 2023, "precio_musd": 520}
PAYLOAD_REVENTA = {"zona": "Sur", "tipo_predio": "URBANO", "ventas_previas": 2}

ESTADOS_RANGO = {"por debajo del rango", "dentro del rango", "por encima del rango"}


# ---------- Raíz y health ----------
def test_index(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Welcome to the API" in r.text


def test_health(client: TestClient) -> None:
    r = client.get(f"{PREFIJO}/health")
    assert r.status_code == 200
    datos = r.json()
    assert datos["name"] == settings.PROJECT_NAME
    assert datos["model_version"] == servicios.VERSION_MODELOS
    assert datos["api_version"]


# ---------- Rango ----------
@pytest.mark.parametrize("zona", ["Norte", "Centro", "Sur"])
def test_rango_ok_por_zona(client: TestClient, zona: str) -> None:
    t = servicios.tabla("rango_historico")
    anio = int(t[t["zona"] == zona]["anio"].max())
    payload = {"zona": zona, "anio": anio, "precio_musd": 100}
    r = client.post(f"{PREFIJO}/rango", json=payload)
    assert r.status_code == 200
    datos = r.json()
    assert datos["zona"] == zona
    assert datos["anio"] == anio
    assert datos["estado"] in ESTADOS_RANGO
    h = datos["historico"]
    assert h["p10"] <= h["p25"] <= h["p50"] <= h["p75"] <= h["p90"]
    assert h["n"] > 0

def test_rango_estado_coherente_con_historico(client: TestClient) -> None:
    r = client.post(f"{PREFIJO}/rango", json=PAYLOAD_RANGO)
    assert r.status_code == 200
    datos = r.json()
    h = datos["historico"]
    precio = datos["precio_musd"]
    if precio < h["p10"]:
        assert datos["estado"] == "por debajo del rango"
    elif precio > h["p90"]:
        assert datos["estado"] == "por encima del rango"
    else:
        assert datos["estado"] == "dentro del rango"
    m = datos["modelo"]
    assert m["p10"] <= m["p50"] <= m["p90"]



def test_rango_sin_campos_devuelve_422(client: TestClient) -> None:
    r = client.post(f"{PREFIJO}/rango", json={})
    assert r.status_code == 422

def test_rango_combinacion_sin_historico_devuelve_404(client: TestClient) -> None:
    t = servicios.tabla("rango_historico")
    existentes = set(zip(t["zona"], t["anio"].astype(int)))
    faltantes = [
        (z, a) for z in servicios.ZONAS for a in range(2021, 2027)
        if (z, a) not in existentes
    ]
    if not faltantes:
        pytest.skip("Hay histórico para todas las combinaciones zona-año")
    zona, anio = faltantes[0]
    r = client.post(f"{PREFIJO}/rango", json={"zona": zona, "anio": anio, "precio_musd": 100})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "cambio",
    [
        {"zona": "Oriente"},      # zona fuera de Norte/Centro/Sur
        {"anio": 1900},           # año fuera de 2021-2026
        {"anio": 2030},
        {"precio_musd": 0},       # el precio debe ser > 0
        {"precio_musd": -10},
    ],
)
def test_rango_entradas_invalidas_devuelven_422(client: TestClient, cambio: dict) -> None:
    r = client.post(f"{PREFIJO}/rango", json={**PAYLOAD_RANGO, **cambio})
    assert r.status_code == 422


# ---------- Reventa ----------
def test_reventa_ok(client: TestClient) -> None:
    r = client.post(f"{PREFIJO}/reventa", json=PAYLOAD_REVENTA)
    assert r.status_code == 200
    datos = r.json()
    assert datos["zona"] == "Sur"
    assert datos["tipo_predio"] == "URBANO"
    assert datos["ventas_previas"] == 2
    assert 0 <= datos["prob_reventa_3a"] <= 1
    assert datos["prob_zona_3a"] is None or 0 <= datos["prob_zona_3a"] <= 1


def test_reventa_tipo_predio_por_defecto_es_urbano(client: TestClient) -> None:
    r = client.post(f"{PREFIJO}/reventa", json={"zona": "Sur", "ventas_previas": 0})
    assert r.status_code == 200
    assert r.json()["tipo_predio"] == "URBANO"


def test_reventa_sin_campos_devuelve_422(client: TestClient) -> None:
    r = client.post(f"{PREFIJO}/reventa", json={})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "cambio",
    [
        {"zona": "Oriente"},
        {"tipo_predio": "COMERCIAL"},   # fuera de URBANO/RURAL/SIN INFORMACION
        {"ventas_previas": -1},         # mínimo 0
        {"ventas_previas": 51},         # máximo 50
    ],
)
def test_reventa_entradas_invalidas_devuelven_422(client: TestClient, cambio: dict) -> None:
    r = client.post(f"{PREFIJO}/reventa", json={**PAYLOAD_REVENTA, **cambio})
    assert r.status_code == 422


# ---------- Segmentos ----------
@pytest.mark.parametrize("n", [3, 4, 5])
def test_segmentos_ok(client: TestClient, n: int) -> None:
    r = client.get(f"{PREFIJO}/segmentos", params={"n": n})
    assert r.status_code == 200
    datos = r.json()
    assert datos["criterio"]
    lista = datos["segmentos"]
    assert 1 <= len(lista) <= n
    assert [s["posicion"] for s in lista] == list(range(1, len(lista) + 1))
    assert all(s["ic_inf"] > 0 for s in lista)
    retornos = [s["retorno_real_anual"] for s in lista]
    assert retornos == sorted(retornos, reverse=True)


def test_segmentos_por_defecto_son_cinco_o_menos(client: TestClient) -> None:
    r = client.get(f"{PREFIJO}/segmentos")
    assert r.status_code == 200
    assert len(r.json()["segmentos"]) <= 5


@pytest.mark.parametrize("n", [2, 6])
def test_segmentos_n_fuera_de_rango_devuelve_422(client: TestClient, n: int) -> None:
    r = client.get(f"{PREFIJO}/segmentos", params={"n": n})
    assert r.status_code == 422