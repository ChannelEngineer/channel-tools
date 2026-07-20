FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY channel_platform ./channel_platform
COPY mcp-servers ./mcp-servers
COPY micro-apps ./micro-apps
RUN pip install --no-cache-dir -e ".[dashboard]"
ENV CHANNEL_DB=/data/channel.db
VOLUME /data
# Default: run the lead dashboard; override command for MCP servers or CLI
CMD ["uvicorn", "micro-apps.lead-dashboard.main:app", "--host", "0.0.0.0", "--port", "8080"]
