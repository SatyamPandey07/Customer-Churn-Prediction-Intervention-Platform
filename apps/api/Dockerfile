FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

COPY pyproject.toml .
COPY api ./api
RUN uv pip install --system -e .

COPY . /app/apps/api

ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
