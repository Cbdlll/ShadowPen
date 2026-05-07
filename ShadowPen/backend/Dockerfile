FROM kalilinux/kali-rolling:latest

# Install system dependencies for Python, Playwright, and Go
# This layer is only rebuilt when the Dockerfile is modified
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-full \
    wget \
    curl \
    git \
    golang-go \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libatspi2.0-0 \
    fonts-liberation \
    fonts-unifont \
    xdg-utils \
    libglib2.0-0 \
    libnss3 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Install Katana (ProjectDiscovery crawler tool)
RUN GO111MODULE=on go install github.com/projectdiscovery/katana/cmd/katana@latest \
    && mv /root/go/bin/katana /usr/local/bin/katana \
    && chmod +x /usr/local/bin/katana

# Install GoSpider (fast web spider)
RUN GO111MODULE=on go install github.com/jaeles-project/gospider@latest \
    && mv /root/go/bin/gospider /usr/local/bin/gospider \
    && chmod +x /usr/local/bin/gospider

WORKDIR /app

# Create and activate virtual environment (outside /app to avoid volume mount override)
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies (separate layer, only rebuilt when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (separate layer, will be cached)
RUN playwright install chromium

# Copy application code (copy last to ensure code changes only affect this layer)
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
