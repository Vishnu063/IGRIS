FROM ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
# Minimal CPU runtime dependency, installed only at explicit image-build time.
# Signed Ubuntu repositories; session CA stays in a BuildKit secret mount.
RUN --mount=type=secret,id=proxy_ca,required=true \
    apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca update \
    && apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca install -y --no-install-recommends libgomp1=14.2.0-4ubuntu2~24.04.1 \
    && dpkg-query -W libgomp1 > /usr/local/share/igris-system-packages.txt \
    && rm -rf /var/lib/apt/lists/*
USER 1000:1000
