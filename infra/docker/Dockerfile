# FlowMusic Supabase CLI lab, isolated from the Asterisk host packages.
FROM node:22.14.0-bookworm-slim AS node
FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg git ffmpeg tini xvfb x11vnc xfonts-base \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main' > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN mkdir -p vendor && git clone --no-checkout https://github.com/deluxebear/flowmusic-cli.git vendor/flowmusic-cli \
    && git -C vendor/flowmusic-cli checkout --detach 08491dc3319ae9f530c5c05c431196bbbbb10607
COPY . .
RUN groupadd --gid 1001 music && useradd -m --uid 1001 --gid 1001 music \
    && mkdir -p /app/data && chown 1001:1001 /app/data
USER 1001:1001
ENV HOME=/app/data/home XDG_CONFIG_HOME=/app/data/config XDG_CACHE_HOME=/app/data/cache XDG_DATA_HOME=/app/data/share
EXPOSE 8765
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8765","--workers","1","--no-access-log"]
