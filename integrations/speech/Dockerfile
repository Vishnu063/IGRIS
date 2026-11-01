FROM ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
RUN --mount=type=secret,id=proxy_ca,required=true \
    apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca update \
    && apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca install -y --no-install-recommends espeak-ng \
    && dpkg-query -W > /usr/local/share/igris-speech-system-packages.txt \
    && rm -rf /var/lib/apt/lists/*
USER 1000:1000
