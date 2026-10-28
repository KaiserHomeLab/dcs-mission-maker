# ---- build stage: Python packages (pydcs comes from git) and pinned third-party data
FROM python:3.12-slim AS build

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
ENV PYTHONPATH=/install/lib/python3.12/site-packages

# Third-party mission scripts, pinned to exact versions and checksummed.
# MOOSE (GPL-3.0), MIST (GPL-3.0), Skynet IADS (Apache-2.0),
# Hound ELINT (GPL-3.0), EWRS (MIT).
RUN mkdir -p /srv/vendor && cd /srv/vendor \
 && curl -fsSL -o Moose_.lua https://raw.githubusercontent.com/FlightControl-Master/MOOSE_INCLUDE/37c2001e63f715d2e6be14b49ddc3b84656a3f4e/Moose_Include_Static/Moose_.lua \
 && curl -fsSL -o mist.lua https://raw.githubusercontent.com/mrSkortch/MissionScriptingTools/da53d53087677745443d5df9a7225eaff98438dc/mist_4_5_126.lua \
 && curl -fsSL -o skynet-iads-compiled.lua https://raw.githubusercontent.com/walder/Skynet-IADS/62aab46901eed16dbfe17fb482ba05f74d056355/demo-missions/skynet-iads-compiled.lua \
 && curl -fsSL -o HoundElint.lua https://github.com/uriba107/DCS-Hound/releases/download/v0.5.2/HoundElint.lua \
 && curl -fsSL -o EWRS.lua https://raw.githubusercontent.com/Bob7heBuilder/EWRS/6e67a8844e40e9ce8d4b30a0f989a769a6b2be61/EWRS.lua \
 && printf '%s  %s\n' \
    5d307f804d656ace0566123383b43cc70e156df783ab339a17858a391d30ace7 Moose_.lua \
    85e78e6cb5d2191b4148241e1a77c4884049b51295508d3d38b20793a0968c39 mist.lua \
    6b95b407f99ddf3933addcf3cfda2288d53519af652ffb90b779c26ba7608ba7 skynet-iads-compiled.lua \
    b7a863374bbc83368a1c02bfc618a8acdf6157331df51e704173efbe7ae3f0ca HoundElint.lua \
    48380672cb916b6d5e747b398324d4131de9fd06933060f370a3c0df6c266ccb EWRS.lua \
    | sha256sum -c -

# Airfield beacon frequencies (TACAN/ILS) from DCS Retribution (LGPL-3.0),
# extracted from DCS. Pinned and checksummed.
RUN mkdir -p /srv/vendor/beacons && cd /srv/vendor/beacons \
 && for m in caucasus persiangulf syria nevada marianaislands sinai kola falklands germanycoldwar; do \
      curl -fsSL -o $m.json https://raw.githubusercontent.com/dcs-retribution/dcs-retribution/49e8067f691301eb796bcc9d70c26c92ea190a97/resources/dcs/beacons/$m.json; \
    done \
 && printf '%s  %s\n' \
    b69ba4138d4acf41867e950af4c83c947d350c54a469c03abc8b00d04afbec49 caucasus.json \
    6378c724a3497a67f6b889a3aa617d62d3eeb82da6267d413cc311cdb7ee7987 persiangulf.json \
    97bbccf127429d761e49c98209d55ab11259f72cde4646d9888c16cc8969e71e syria.json \
    7beab9fa92ff358890c5c1e04133e9a838b661a59841aa30bf3dbc8b05d2abba nevada.json \
    2e11b1558c0d9d608f6c89d7e8d5b154ff7c647e9c6245941c1e6a7a183a29be marianaislands.json \
    f03fb2a2f7fdbfe621c8c05e5c0041c7220814048e14f05353935047e56282b9 sinai.json \
    b639b1cb90f3473158b1044a39cc085c4ce150efced7c95ba7b7f59a582d746f kola.json \
    f009e9e6ce6d043281a266d873d662932941efd4b8b8fd60857278d365883d42 falklands.json \
    0de8320aab24db4ec6ff7b10f1e28866dfe9500aa57efb9715fa11cff430b4ad germanycoldwar.json \
    | sha256sum -c -

# Real 3-view drawings for the Threat ID blueprints (Wikimedia Commons; public
# domain / CC0 / CC BY / CC BY-SA, credited on each sheet). Pinned by SHA-1.
# Soft-fails: anything that can't be fetched falls back to a generated drawing.
COPY drawings.json tools/fetch_drawings.py ./
RUN python fetch_drawings.py drawings.json /srv/drawings

# ---- runtime stage: no git or curl; the app runs as an unprivileged user (see docker-entrypoint.sh)
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 1000 --create-home --shell /usr/sbin/nologin app \
 && mkdir -p /output /scripts /server-missions && chown app:app /output /server-missions

COPY --from=build /install /usr/local
COPY --from=build /srv/vendor /srv/vendor
COPY --from=build /srv/drawings /srv/drawings
WORKDIR /srv
COPY docker-entrypoint.sh /usr/local/bin/
COPY gunicorn.conf.py ./
COPY app ./app
COPY dcs-hook ./dcs-hook

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    VENDOR_DIR=/srv/vendor DRAWINGS_DIR=/srv/drawings CUSTOM_SCRIPTS_DIR=/scripts OUTPUT_DIR=/output
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"
# The entrypoint fixes volume ownership, then runs gunicorn as the unprivileged "app" user.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "app.server:app"]
