# Backend image: API, engine, ML package and the demo data. The frontend is deployed separately.
FROM python:3.10-slim
WORKDIR /app
COPY ml ml
COPY backend backend
COPY data data
RUN pip install --no-cache-dir -r backend/requirements.txt && pip install --no-cache-dir -e ml
ENV LLM_MODE=cache_only
# Load the demo data and run the whole-year analysis at build time so the first Run is fast.
RUN cd backend && python -m app.warm
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
