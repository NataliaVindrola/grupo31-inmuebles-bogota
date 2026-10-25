# Maqueta del tablero (Entrega 1)

Prototipo visual de las 3 pantallas del tablero. Las cifras son las de la exploración (notebooks 01 y 02); no hay API ni modelo conectado todavía.

- `mockup_tablero.html`: versión interactiva, se abre directo en el navegador (pestañas, intervalo al pasar el cursor y consulta de una oferta).
- `mockup_tablero.png`: imagen estática usada en el reporte (sección 5).

| Pantalla | Decisión que apoya | Origen de las cifras |
|---|---|---|
| 1. Segmentos | Dónde concentrar la búsqueda | Retorno real por zona × rango, con n e intervalo del 90 % |
| 2. Liquidez | Dónde concentrar la búsqueda | Probabilidad de reventa a 1, 3 y 5 años (Kaplan-Meier) |
| 3. Rango de una oferta | Si el precio está dentro de lo habitual | Percentiles p10, mediana y p90 del valor registrado |

Criterios de diseño: cada cifra lleva su n y su intervalo, los segmentos con n < 100 se marcan como no concluyentes, y el texto habla de referencia histórica, no de avalúo.
