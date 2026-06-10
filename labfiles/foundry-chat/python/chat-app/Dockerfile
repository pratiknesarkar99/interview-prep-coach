# Dockerfile

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy dependencies first (lets Docker cache this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY context.py .
COPY prompts.py .
COPY templates/ templates/

# Expose Flask port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]