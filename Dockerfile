# Ovladač myčky Candy – obraz pro provoz na Linux serveru (viz docs/nasazeni.md).
FROM python:3.14-slim

# uv jen jako nástroj pro instalaci závislostí podle uv.lock (pevná verze).
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Závislosti zvlášť od kódu – při změně kódu se vrstva s knihovnami nepřestavuje.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY candy_netscan ./candy_netscan
COPY ovladac ./ovladac

# Neprivilegovaný uživatel; UID 1000 = běžný první uživatel na hostiteli (práva k ./data).
RUN useradd --uid 1000 --no-create-home app && mkdir /data && chown app /data
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    DATA_DIR=/data \
    TZ=Europe/Prague
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/stav', timeout=3)"

CMD ["uvicorn", "ovladac.main:app", "--host", "0.0.0.0", "--port", "8000"]
