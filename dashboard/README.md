# Tablero (Dash)

Responsable: Jorge. Tres pantallas según `mockup/mockup_tablero.html`.

```
dashboard/
├── app.py          # aplicación Dash (navegación entre pantallas)
├── servicios.py    # ÚNICO punto de acceso a datos y modelo (luego se cambia por la API)
├── pages/          # segmentos.py, liquidez.py, oferta.py: una pantalla por archivo
├── assets/         # style.css
└── data/           # tablas que genera `python -m src.tablas` (contrato en src/tablas.py)
```

Correr (desde la raíz del repositorio, con las dependencias de `requirements.txt`):

```
python -m src.tablas          # genera dashboard/data/*.csv
python dashboard/app.py       # http://localhost:8050
```

Mientras falten las tablas o el modelo, cada pantalla muestra un aviso en lugar de fallar.
