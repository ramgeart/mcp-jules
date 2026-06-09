FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8080
ENV JULES_API_BASE=https://jules.googleapis.com/v1alpha

WORKDIR /app

# Copy python dependencies requirements (we can install from pyproject.toml directly)
COPY pyproject.toml README.md /app/
COPY src /app/src/

# Install the application and its dependencies
RUN pip install --no-cache-dir .

# Expose the server port
EXPOSE 8080

# Run the FastAPI server via Uvicorn
CMD ["sh", "-c", "uvicorn jules_mcp_server.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8080}"]
