FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine

ENV NGINX_WORKER_PROCESSES 1
ENV UWSGI_CHEAPER 0
ENV UWSGI_PROCESSES 1

RUN apk add gcc musl-dev libffi-dev make
RUN pip install --upgrade pip
RUN pip install pipenv

WORKDIR /app

COPY ./Pipfile .
COPY ./Pipfile.lock .
RUN pipenv lock --keep-outdated --requirements > requirements.txt
RUN pip install -r requirements.txt
COPY src/*.py /app/