FROM python:3.13-slim

# Crear usuario que ejecuta la app
RUN adduser --disabled-password --gecos '' api-user

# Definir directorio de trabajo 
WORKDIR /opt/code

# Instalar dependencias
COPY requirements-api.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-api.txt


# Copiar solo lo que la API necesita
COPY app/ app/
COPY src/ src/
COPY dashboard/servicios.py dashboard/servicios.py
COPY dashboard/data/ dashboard/data/
COPY models/ models/

# Cambiar propiedad de la carpeta a api-user
RUN chown -R api-user:api-user /opt/code
USER api-user


# Puerto a exponer para la api 
EXPOSE 8001

# Comandos a ejecutar al correr el contenedor 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
