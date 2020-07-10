FROM python:3.8-slim

RUN apt-get update && apt-get install gcc -y && apt-get clean
RUN mkdir /opt/expense-app
WORKDIR /opt/expense-app
COPY . .
RUN pip install --no-cache-dir -r requirements

EXPOSE 5000

CMD ["uwsgi", "--ini", "app.ini"]
