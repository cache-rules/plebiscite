FROM python:3.7-alpine

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/plebiscite

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY plebiscite ./plebiscite
COPY templates ./templates
EXPOSE 8080

CMD [ "python", "plebiscite/run.py", "config.json" ]
