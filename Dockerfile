FROM python:3.11-alpine

RUN apk update && apk upgrade
RUN apk add gcc musl-dev libffi-dev make
RUN pip install pipenv
RUN pip install --upgrade pip

COPY ./Pipfile .
COPY ./Pipfile.lock .

RUN pipenv requirements > requirements.txt
RUN pip install -r requirements.txt
COPY gitops_updater /app/gitops_updater
COPY main.py /app/main.py
COPY gunicorn_conf.py /app/gunicorn_conf.py

RUN adduser -u 1001 -D gitops-updater
RUN chown -R gitops-updater:gitops-updater /app

WORKDIR /app
USER gitops-updater

CMD ["gunicorn", "--conf", "/app/gunicorn_conf.py", "--bind", "0.0.0.0:8080", "gitops_updater.main:app", "--logger-class", "gitops_updater.logger.CustomGunicornLogger"]