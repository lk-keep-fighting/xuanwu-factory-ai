FROM nexus.aimstek.cn/xuanwu/xuanwu-factory-ai-base:python3.11-nodejs20

WORKDIR /app

# Copy dependency definitions and source
COPY requirements.txt .
COPY . .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Qwen Code CLI via npm
RUN npm install -g @qwen-code/qwen-code

# Set default workspace directory
WORKDIR /workspace

# Entrypoint command
CMD ["python", "/app/main.py"]
