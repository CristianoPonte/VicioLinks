# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy frontend static files (serving them via FastAPI for simplicity in MVP)
COPY frontend ./frontend

# Environment variables
ENV PORT=8080
ENV GOOGLE_CLOUD_PROJECT=your-project-id

# Expose port
EXPOSE 8080

# Command to run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
