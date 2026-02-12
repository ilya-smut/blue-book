# Stage 1: Build
FROM python:3.13-alpine AS builder
WORKDIR /build
COPY pyproject.toml poetry.lock README.md ./
COPY bluebook/ bluebook/
RUN pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.13-alpine
WORKDIR /bluebook
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/bluebook /usr/local/bin/bluebook
CMD ["bluebook", "start", "--debug"]
EXPOSE 5000
