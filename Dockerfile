FROM python:3.8-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install -U pip && \
    pip install -r requirements.txt

CMD ["gunicorn", "app:gunicorn_prod_app()", "-c", "gunicorn.conf.py"]
