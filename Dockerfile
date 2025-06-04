FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Remove collectstatic from here as it will be run in docker-compose command
# RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "zip_league.wsgi:application", "--bind", "0.0.0.0:8000"]
