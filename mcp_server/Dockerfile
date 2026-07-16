FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the API and Web UI port
EXPOSE 8000

# Start the FastAPI server
CMD ["python", "server.py"]
