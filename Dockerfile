FROM python:3.7-alpine

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN apk update && \
	apk add build-base python3-dev gcc libc-dev

RUN pip install -U pip && \
    pip install -r requirements.txt

CMD ["gunicorn", "app:gunicorn_prod_app()", "-c", "gunicorn.conf.py"]
