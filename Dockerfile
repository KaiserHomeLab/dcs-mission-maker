# ---- build stage: Python packages and the pinned, checksummed third-party files
FROM python:3.12-slim AS build

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
ENV PYTHONPATH=/install/lib/python3.12/site-packages

# Mission scripts (MOOSE, MIST, Skynet IADS, Hound ELINT, EWRS), airfield beacon data
# (DCS Retribution) and the kneeboard fonts (DejaVu). Same script as windows/setup.bat.
COPY tools/fetch_vendor.py ./
RUN python fetch_vendor.py /srv/vendor

# ---- runtime stage: the app runs as an unprivileged user (see docker-entrypoint.sh)
FROM python:3.12-slim

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin app \
 && mkdir -p /output /scripts /server-missions && chown app:app /output /server-missions

COPY --from=build /install /usr/local
COPY --from=build /srv/vendor /srv/vendor
WORKDIR /srv
COPY docker-entrypoint.sh /usr/local/bin/
COPY gunicorn.conf.py ./
COPY app ./app
COPY dcs-hook ./dcs-hook

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    VENDOR_DIR=/srv/vendor CUSTOM_SCRIPTS_DIR=/scripts OUTPUT_DIR=/output
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"
# The entrypoint fixes volume ownership, then runs gunicorn as the unprivileged "app" user.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "app.server:app"]
