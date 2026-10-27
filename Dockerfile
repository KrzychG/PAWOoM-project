FROM python:3.12-slim

WORKDIR /workspace

# Kopiujemy wymagania i instalujemy pakiety
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy kod aplikacji
COPY ./app ./app

# Domyślny port dla FastAPI
EXPOSE 8101

# Uruchomienie aplikacji za pomocą uvicorn factory
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8101"]
