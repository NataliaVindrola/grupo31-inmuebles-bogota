# Modelos entrenados

Aquí quedan los modelos **elegidos** (no todas las corridas: esas viven en MLflow).

```
models/
├── rango/
│   └── v1/            q10.joblib, q50.joblib, q90.joblib, metadata.json
└── reventa/
    └── v1/            modelo.joblib, metadata.json
```

- Los crea `rango.guardar(...)` y `reventa.guardar(...)` (ver `src/`); el tablero los carga con `rango.cargar("v1")`.
- `metadata.json` guarda la fecha, las variables, los parámetros, las ventanas de entrenamiento y prueba, y las métricas.
- Regla de tamaño: si cada archivo pesa menos de 25 MB se versiona en Git; si pesa más, se versiona con DVC (`dvc add`) como los datos.
- Una versión nueva (`v2`, ...) se agrega al lado; no se sobrescribe una versión ya usada por el tablero ni por el reporte.
