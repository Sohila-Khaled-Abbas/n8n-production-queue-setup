FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py llm_generator.py ./

# Expose the port
EXPOSE 8000

# Run the FastMCP SSE Server
CMD ["python", "server.py"]
