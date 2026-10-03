# Backend image for a Hugging Face Docker Space: API, engine, ML package and the demo data. The frontend is deployed separately.
FROM python:3.10-slim
# Spaces run the container as user 1000, and the app writes its database and cache at run time.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
COPY --chown=user ml ml
COPY --chown=user backend backend
COPY --chown=user data data
RUN pip install --no-cache-dir --user -r backend/requirements.txt && pip install --no-cache-dir --user -e ml
# The API serves only the demo data and has no login, so any site may call it.
ENV LLM_MODE=cache_only CORS_ORIGIN=*
# Load the demo data and run the whole-year analysis at build time so the first Run is fast.
RUN cd backend && python -m app.warm
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "7860"]
