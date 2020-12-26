FROM python:alpine

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN apk update && \
	apk add python3-dev gcc libc-dev

RUN pip install -U pip && \
    pip install -r requirements.txt

CMD ["gunicorn", "app:gunicorn_prod_app()", "-c", "gunicorn.conf.py"]
