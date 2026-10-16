# FlowMusic Supabase CLI lab, isolated from the Asterisk host packages.
FROM node:22.14.0-bookworm-slim AS node
FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git ffmpeg tini \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN mkdir -p vendor && git clone --no-checkout https://github.com/deluxebear/flowmusic-cli.git vendor/flowmusic-cli \
    && git -C vendor/flowmusic-cli checkout --detach 08491dc3319ae9f530c5c05c431196bbbbb10607 \
    && npm --prefix vendor/flowmusic-cli ci --ignore-scripts
COPY . .
RUN groupadd --gid 1001 music && useradd -m --uid 1001 --gid 1001 music \
    && mkdir -p /app/data && chown 1001:1001 /app/data
USER 1001:1001
ENV HOME=/home/music
EXPOSE 8765
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8765","--workers","1","--no-access-log"]
