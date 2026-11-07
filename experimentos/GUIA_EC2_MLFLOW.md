# Guía: MLflow en una EC2 (Entrega 2, Grupo 31)

Responsable: Jorge. Objetivo: servidor de MLflow en una EC2, con las 4 corridas de `experimentos/algoritmos_rango.py`
(HistGradientBoosting y LightGBM, cada uno con parámetros estándar y afinado con Optuna), y los pantallazos que exige la guía de la entrega.
Al terminar, la instancia queda **detenida (Stop), no terminada**. Cada integrante hace sus corridas en su propia VM y con su propio servidor; esta guía es la de Jorge.

Reemplazar `IP` por la IP pública vigente y `LLAVE.pem` por la ruta de la llave. **La IP pública cambia cada vez que se detiene e inicia la instancia.**

## 0. Antes de empezar (en el computador)

- `experimentos/algoritmos_rango.py` es autónomo (carga y prepara los datos él mismo, según el notebook 02), así que **no depende de `src/`**. Solo necesita estar en la rama que se clona (`estructura-entrega2` con este cambio subido).
- Hay que tener el CSV `compraventas_0125_bogota.csv` (98 MB) y `ipc.csv`. Dos opciones (ver parte 5): `dvc pull` con credenciales de DagsHub, o copiarlos con `scp` desde quien los tenga.
- Acceso de lectura al repositorio desde la VM (token de GitHub propio; nunca pegarlo en el chat ni en archivos).

## 1. Crear la instancia (pantallazo M1)

En EC2, *Launch instance*:

| Campo | Valor |
|---|---|
| Nombre | `Proyecto_G31_MLflow` |
| Imagen | buscar y elegir por nombre **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type** (no pegar ids) |
| Tipo | **`t3.medium`** (4 GB de RAM; el CSV y los modelos necesitan más que los 2 GB de un `t3.small`) |
| Llave | par nuevo o existente (`.pem`, guardarlo fuera del repositorio) |
| Almacenamiento | **20 GB** |
| Grupo de seguridad | SSH (22) y **TCP personalizado 8050, origen Anywhere IPv4** |

**Pantallazo M1:** EC2, *Instancias*, instancia en ejecución, con el **usuario de AWS Academy** (arriba a la derecha), el estado *En ejecución* y las **IPv4 pública y privada**.

Si Windows rechaza la llave (`UNPROTECTED PRIVATE KEY FILE`), en PowerShell:

```powershell
$k='RUTA\A\LLAVE.pem'
icacls $k /inheritance:r | Out-Null
icacls $k /grant:r "${env:USERNAME}:(R)" | Out-Null
```

## 2. Conectar y preparar el sistema (pantallazo M2)

```powershell
ssh -i "RUTA\A\LLAVE.pem" ubuntu@IP
```

En la VM:

```bash
python3 --version      # debe decir Python 3.12.x; si no, detenerse (no es Ubuntu 24.04)
free -h                # ~4 GB de RAM
sudo apt update
sudo apt install -y python3-pip python3-venv git
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
free -h                # ahora la fila Swap muestra 2.0Gi
```

**Pantallazo M2:** la conexión SSH con `python3 --version` y `free -h`.

## 3. Clonar el repositorio e instalar dependencias (pantallazo M3)

```bash
cd ~
git clone -b estructura-entrega2 https://github.com/NataliaVindrola/grupo31-inmuebles-bogota.git
# usuario: Geo7473 · contraseña: el token (si el repositorio es privado)
cd grupo31-inmuebles-bogota
python3 -m venv ~/.venv
source ~/.venv/bin/activate
pip install -r requirements.txt
mlflow --version
```

Cuando `estructura-entrega2` ya esté en `main`, usar `git clone` sin `-b` (o `git pull`). Si `pip install` agota la memoria (`Killed`), repetirlo después de comprobar que el swap está activo.
`jupyterlab` y `dash` no se necesitan en la VM; para una instalación más corta, que alcanza para las corridas: `pip install pandas numpy scikit-learn lightgbm optuna mlflow dvc`.

**Pantallazo M3:** el final de la instalación y `mlflow --version` con el prompt `(.venv)` visible.

> **Cada nueva sesión SSH:** `source ~/.venv/bin/activate` y `cd ~/grupo31-inmuebles-bogota`.

## 4. Servidor de MLflow (pantallazos M4 y M5)

En una **terminal SSH dedicada** (queda ocupada), con el ambiente activo:

```bash
cd ~
mlflow server -h 0.0.0.0 -p 8050 --workers 1 \
  --backend-store-uri sqlite:///mlflow.db \
  --allowed-hosts "localhost:8050,IP:8050" \
  --cors-allowed-origins "http://IP:8050"
```

Debe aparecer `Listening at: http://0.0.0.0:8050`. **Pantallazo M4:** esa salida. (`--backend-store-uri sqlite:///mlflow.db` guarda las corridas en `~/mlflow.db`; MLflow 3.x ya no admite por defecto el almacenamiento en carpetas `mlruns`.)

En el navegador del computador, abrir `http://IP:8050`. **Pantallazo M5:** la interfaz de MLflow con **la misma IP en la barra de direcciones**.
Si sale `Invalid Host header`, la IP de `--allowed-hosts` no es la vigente; si no carga, revisar la regla del puerto 8050 en el grupo de seguridad.

Alternativa para no depender de la terminal abierta: anteponer `nohup` y terminar con `> ~/mlflow.log 2>&1 &`.

## 5. Datos en la VM

**Opción A, `dvc pull` (requiere acceso a DagsHub de Natalia):**

```bash
cd ~/grupo31-inmuebles-bogota
dvc remote modify origin --local auth basic
dvc remote modify origin --local user USUARIO_DAGSHUB
dvc remote modify origin --local password TOKEN_DAGSHUB     # token propio; queda solo en .dvc/config.local (no se sube a Git)
dvc pull
ls -lh data/
```

(El nombre del remoto se confirma con `dvc remote list`.) Esperado: `compraventas_0125_bogota.csv` de unos 98 MB, `ipc.csv` e `ipc_original.csv`.

**Opción B, `scp` desde un computador que ya tenga los archivos (en PowerShell local):**

```powershell
scp -i "RUTA\A\LLAVE.pem" "RUTA\data\compraventas_0125_bogota.csv" "RUTA\data\ipc.csv" "RUTA\data\ipc_original.csv" ubuntu@IP:/home/ubuntu/grupo31-inmuebles-bogota/data/
```

## 6. Corridas (pantallazos M6 y M7)

**Acuerdo del equipo:** cada integrante hace 2 modelos de prueba en su propia VM. Los de Jorge son **2 algoritmos, cada uno con parámetros estándar y afinado con Optuna**, sobre el modelo de rango (p10, p50, p90), con la validación temporal del notebook 02 (entrena 2021-2022, prueba 2023):

| Corrida en MLflow | Algoritmo | Parámetros |
|---|---|---|
| `hgb_estandar` | `HistGradientBoostingRegressor` (pérdida de cuantiles) | por defecto de la librería |
| `hgb_optuna` | el mismo | afinados con Optuna (20 intentos) |
| `lgbm_estandar` | `LightGBM` (objetivo de cuantiles) | por defecto de la librería |
| `lgbm_optuna` | el mismo | afinados con Optuna (20 intentos) |

- **Optuna** no toca 2023: entrena con 2021 y valida con 2022 minimizando el pinball medio de los tres cuantiles; con los mejores parámetros se reentrena con 2021-2022 y se evalúa en 2023. Una sola corrida por modo: los intentos no aparecen como corridas sueltas, sino como la curva `val_pinball_medio` dentro de la corrida `*_optuna`.
- **Qué registra cada corrida:** etiquetas `autor`, `algoritmo`, `modo`; parámetros (los afinados con prefijo `hp_`); métricas `cobertura_p10_p90`, `ancho_mediano_musd`, `pinball_q10/q50/q90`, las de la línea base con prefijo `base_` y `tiempo_s`.
- El script **no depende de `src/`**; lee `data/compraventas_0125_bogota.csv` y `data/ipc.csv` (parte 5).

En la VM, con el ambiente activo y desde la raíz del repositorio:

```bash
export MLFLOW_TRACKING_URI=http://localhost:8050
python experimentos/algoritmos_rango.py --autor jorge
```

Las cuatro corridas tardan unos minutos (la búsqueda de Optuna es lo más pesado). Variantes útiles:

```bash
python experimentos/algoritmos_rango.py --autor jorge --corridas hgb_estandar lgbm_estandar     # solo las estándar (prueba rápida)
python experimentos/algoritmos_rango.py --autor jorge --trials 30                               # más intentos de Optuna
```

Si una corrida muere con `Killed`, es memoria: comprobar swap y que no haya otro proceso grande corriendo. Si se repite el script, se crean corridas duplicadas en el mismo experimento; conviene correrlo completo una sola vez para los pantallazos.

**Pantallazo M6:** el terminal con la salida del script (las líneas `[linea_base]` y `[hgb_estandar]`, `[hgb_optuna]`, `[lgbm_estandar]`, `[lgbm_optuna]`).
**Pantallazo M7:** en `http://IP:8050`, el experimento `rango-valor` con las 4 corridas y las columnas de métricas visibles (cobertura, ancho, pinball). Después, con las 4 corridas seleccionadas, *Compare* y una vista de gráfico (por ejemplo `pinball_q50` o `cobertura_p10_p90` por corrida). Y la curva `val_pinball_medio` de una corrida `*_optuna`, en la pestaña *Model metrics*. Todas con la IP en la barra.

## 7. Modelo para el tablero

`algoritmos_rango.py` compara algoritmos y **no guarda modelos**. El modelo que consumirá el tablero lo guarda `src/rango.py` (Julián, `models/rango/v1/`). Si el equipo decide usar el ganador de estas corridas, se implementa `entrenar`/`guardar` en `src/rango.py` con ese algoritmo y esos parámetros (están en la corrida de MLflow, columnas `hp_*`).

## 8. Cierre: detener, no terminar

1. Tomar **todos** los pantallazos (M1 a M7) antes de apagar. Si hay que repetir alguno, la IP habrá cambiado: M1, M5 y M7 deben mostrar **la misma IP** en una misma sesión.
2. En la terminal del servidor: `Ctrl+C`.
3. En EC2: *Instance state*, **Stop instance** (no *Terminate*). Verificar el estado *Detenida*.
4. Guardar la llave `.pem` fuera del repositorio. Borrar `.dvc/config.local` y el token de GitHub de la VM solo si se va a *terminar* algo; no se termina nada en esta entrega.
5. Para reanudar: *Start instance*, anotar la **nueva IP pública**, conectar por SSH, activar el ambiente y volver a arrancar el servidor con la nueva IP en `--allowed-hosts` y `--cors-allowed-origins`. Los experimentos siguen ahí (MLflow guarda en `~/mlruns` y `~/mlartifacts`).

## 9. Lista de pantallazos que pide la entrega

| Código | Muestra | Obligatorio |
|---|---|---|
| M1 | EC2 en ejecución, usuario de AWS e IPs | sí |
| M2 | SSH, Python 3.12, memoria | apoyo |
| M3 | instalación y versión de MLflow | apoyo |
| M4 | servidor escuchando en 0.0.0.0:8050 | apoyo |
| M5 | interfaz de MLflow con la IP en la barra | **sí** |
| M6 | salida de una corrida en el terminal | apoyo |
| M7 | experimentos y comparación de corridas con la IP visible | **sí** |
| M8 | instancia en estado *Detenida* | sí (muestra que no se terminó) |

Guardarlos en `docs/capturas/` (sin llaves ni tokens visibles; recortar si es necesario).

## 10. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Invalid Host header` | La IP de `--allowed-hosts` no es la actual; reiniciar el servidor con la IP vigente. |
| La interfaz no carga | Falta la regla TCP 8050 en el grupo de seguridad, o el servidor no está corriendo. |
| `Killed` en pip o en el entrenamiento | Poca memoria: swap de 2 GB activo (`free -h`), una sola corrida a la vez, `--workers 1`. |
| `NotImplementedError` | Aún no están las funciones de `src/`; esperar o actualizar con `git pull`. |
| `ModuleNotFoundError: src` | Correr desde la raíz del repositorio (los scripts ya agregan la raíz a la ruta). |
| `dvc pull` pide credenciales o falla con 401/403 | Faltan permisos en DagsHub: usar la opción B (`scp`). |
| El servidor muere al cerrar la terminal | Mantener la terminal abierta o usar `nohup`. |
| Cambió la IP | Es normal tras detener e iniciar; reiniciar el servidor con la nueva IP. |
