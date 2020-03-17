FROM python:3

RUN pip install requests scrapy

WORKDIR /app

COPY . .

ENTRYPOINT ["./entrypoint.sh"]