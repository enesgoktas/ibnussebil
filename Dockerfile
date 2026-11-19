FROM node:20-alpine AS web-build

WORKDIR /web
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/api

COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

COPY api /app/api
COPY --from=web-build /web/dist /app/web/dist

WORKDIR /app/api
EXPOSE 8000

CMD ["sh", "-c", "python -m app.seed_demo && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
