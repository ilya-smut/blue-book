FROM python:3.13-alpine
WORKDIR /bluebook
COPY . .
RUN pip install -e .
CMD ["bluebook", "start", "--debug"]
EXPOSE 5000

