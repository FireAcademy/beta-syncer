FROM python:3.10

RUN DEBIAN_FRONTEND=noninteractive apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y python3-psycopg2

WORKDIR /beta-syncer
COPY src/* ./
COPY requirements.txt .

RUN python3 -m pip install -U pip
RUN python3 -m pip install psycopg2-binary
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "-u", "main.py"]