FROM ubuntu:24.04

ENV DEBIAN_FRONTEND="noninteractive"
ENV LOG4J_FORMAT_MSG_NO_LOOKUPS=true

ARG BUILD_ARCH
ARG BUILD_VERSION

RUN useradd -g root -M crafty \
    && mkdir -p /crafty \
    && chown -R crafty:root /crafty \
    && apt-get update \
    && apt-get -y --no-install-recommends install \
        sudo \
        gcc \
        curl \
        libcurl4 \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        libmariadb-dev \
        default-jre \
        openjdk-8-jre-headless \
        openjdk-11-jre-headless \
        openjdk-17-jre-headless \
        openjdk-21-jre-headless \
        openjdk-25-jre-headless \
        tzdata \
        jq \
        nginx-light \
        gettext-base \
        iproute2 \
    && if [ "$BUILD_ARCH" = "amd64" ]; then \
         apt-get -y --no-install-recommends install lib32gcc-s1; \
       fi \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER crafty
WORKDIR /crafty
COPY --chown=crafty:root rootfs/requirements.txt ./
RUN python3 -m venv ./.venv \
    && . .venv/bin/activate \
    && pip3 install --no-cache-dir --upgrade setuptools pip \
    && pip3 install --no-cache-dir -r requirements.txt \
    && deactivate

USER root
COPY --chown=crafty:root rootfs/app ./app
COPY --chown=crafty:root rootfs/main.py ./main.py
COPY run.sh /run.sh
COPY nginx/nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY nginx/ingress.conf.template /etc/nginx/templates/ingress.conf.template
COPY nginx/direct.conf.template /etc/nginx/templates/direct.conf.template
COPY nginx/direct-ssl.conf.template /etc/nginx/templates/direct-ssl.conf.template
RUN mv ./app/config ./app/config_original \
    && mv ./app/config_original/default.json.example ./app/config_original/default.json \
    && rm -rf /etc/nginx/sites-enabled /etc/nginx/sites-available /etc/nginx/conf.d \
    && mkdir -p /etc/nginx/conf.d /var/log/nginx /var/lib/nginx/body \
    && chown -R crafty:root /etc/nginx /var/log/nginx /var/lib/nginx \
    && chmod +x /run.sh

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

CMD [ "/run.sh" ]
