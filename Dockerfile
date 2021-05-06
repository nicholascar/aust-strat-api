FROM python:3.7.8-slim-buster

EXPOSE 5000

# Python requirements
RUN apt update && apt install -y git
COPY ./requirements.txt ./
COPY ./requirements-deploy.txt ./
RUN pip install -r ./requirements.txt
RUN pip install -r ./requirements-deploy.txt

# API
COPY ./api ./api

# data
COPY ./data ./data

WORKDIR ./api

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
