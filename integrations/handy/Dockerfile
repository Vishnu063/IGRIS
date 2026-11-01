FROM ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
COPY Handy.deb /tmp/Handy.deb
RUN --mount=type=secret,id=proxy_ca,required=true \
    apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca update \
    && apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca install -y --no-install-recommends /tmp/Handy.deb xvfb python3 libopenblas0 libgomp1 \
    && dpkg-query -W > /usr/local/share/igris-handy-system-packages.txt \
    && rm -rf /var/lib/apt/lists/* /tmp/Handy.deb
RUN --mount=type=secret,id=proxy_ca,required=true \
    apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca update \
    && apt-get -o Acquire::https::CaInfo=/run/secrets/proxy_ca install -y --no-install-recommends libasound2t64 \
    && dpkg-query -W > /usr/local/share/igris-handy-system-packages.txt \
    && rm -rf /var/lib/apt/lists/*
USER 1000:1000
