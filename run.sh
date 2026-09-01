#!/bin/bash
set -e

CONFIG_PATH=/data/options.json
TIMEZONE=$(jq -r '.timezone // "Etc/UTC"' "$CONFIG_PATH")

if [ -f "/usr/share/zoneinfo/$TIMEZONE" ]; then
    ln -snf "/usr/share/zoneinfo/$TIMEZONE" /etc/localtime
    echo "$TIMEZONE" > /etc/timezone
    export TZ="$TIMEZONE"
else
    echo "[crafty4] timezone '$TIMEZONE' not found in /usr/share/zoneinfo, keeping container default"
fi

DATA_LOCATION=$(jq -r '.data_location // ""' "$CONFIG_PATH")
DATA_LOCATION="${DATA_LOCATION%/}"

LOG_LEVEL=$(jq -r '.log_level // "info"' "$CONFIG_PATH")
if [ "$LOG_LEVEL" = "debug" ]; then
    DEBUG_LOGGING="true"
else
    DEBUG_LOGGING="false"
fi

debug_echo() {
    if [ "$DEBUG_LOGGING" = "true" ]; then
        echo "$@"
    fi
}

stop_addon() {
    local message="$1"
    echo "[crafty4] error: $message"
    if [ -n "$SUPERVISOR_TOKEN" ]; then
        curl -s -X POST \
            -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
            -H "Content-Type: application/json" \
            http://supervisor/addons/self/stop >/dev/null 2>&1
    fi
    sleep 5
    exit 1
}

if [ -n "$DATA_LOCATION" ]; then
    case "$DATA_LOCATION" in
        /*) ;;
        *)
            stop_addon "data_location '$DATA_LOCATION' is not an absolute path, expected something like /media/... or /share/..."
            ;;
    esac
    DATA_ROOT="$DATA_LOCATION"
    mkdir -p "$DATA_ROOT"
else
    DATA_ROOT="/data"
fi

echo "[crafty4] using data root: $DATA_ROOT"

mkdir -p "$DATA_ROOT/config" "$DATA_ROOT/servers" "$DATA_ROOT/backups" "$DATA_ROOT/logs" "$DATA_ROOT/import"

if [ -d /crafty/app/config ] && [ ! -L /crafty/app/config ]; then
    rm -rf /crafty/app/config
fi
if [ -d /crafty/backups ] && [ ! -L /crafty/backups ]; then
    rm -rf /crafty/backups
fi
if [ -d /crafty/servers ] && [ ! -L /crafty/servers ]; then
    rm -rf /crafty/servers
fi
if [ -d /crafty/logs ] && [ ! -L /crafty/logs ]; then
    rm -rf /crafty/logs
fi
if [ -d /crafty/import ] && [ ! -L /crafty/import ]; then
    rm -rf /crafty/import
fi

ln -snf "$DATA_ROOT/config" /crafty/app/config
ln -snf "$DATA_ROOT/servers" /crafty/servers
ln -snf "$DATA_ROOT/backups" /crafty/backups
ln -snf "$DATA_ROOT/logs" /crafty/logs
ln -snf "$DATA_ROOT/import" /crafty/import

if [ ! "$(ls -A --ignore=.gitkeep "$DATA_ROOT/config" 2>/dev/null)" ]; then
    cp -r /crafty/app/config_original/* "$DATA_ROOT/config/"
else
    cp -f /crafty/app/config_original/version.json "$DATA_ROOT/config/version.json"
fi

if [ -z "$SUPERVISOR_TOKEN" ]; then
    stop_addon "SUPERVISOR_TOKEN is not set, cannot query the assigned ingress port"
fi

SELF_INFO=$(curl -s -X GET \
    -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
    -H "Content-Type: application/json" \
    http://supervisor/addons/self/info)

if [ "$(echo "$SELF_INFO" | jq -r '.result // empty')" != "ok" ]; then
    stop_addon "Supervisor API call to /addons/self/info failed: $(echo "$SELF_INFO" | jq -r '.message // "unknown error"')"
fi

INGRESS_PORT=$(echo "$SELF_INFO" | jq -r '.data.ingress_port // empty')

if [ -z "$INGRESS_PORT" ] || [ "$INGRESS_PORT" = "0" ]; then
    stop_addon "unable to determine the ingress port assigned by Supervisor"
fi

INGRESS_IP=$(echo "$SELF_INFO" | jq -r '.data.ip_address // empty')

if [ -z "$INGRESS_IP" ] || [ "$INGRESS_IP" = "null" ]; then
    debug_echo "[crafty4] debug: full /addons/self/info response follows"
    debug_echo "$SELF_INFO"
    stop_addon "unable to determine the internal ip address assigned by Supervisor"
fi

DIRECT_PORT=$(echo "$SELF_INFO" | jq -r '(.data.network // {}) | .["8443/tcp"] // empty')
if [ -n "$DIRECT_PORT" ] && [ "$DIRECT_PORT" != "null" ]; then
    echo "[crafty4] direct access additionally enabled on port $DIRECT_PORT"
else
    DIRECT_PORT=""
fi

CRAFTY_INTERNAL_PORT=8000

CRAFTY_CONFIG_JSON="$DATA_ROOT/config/config.json"

if [ -f "$CRAFTY_CONFIG_JSON" ]; then
    TMP_CONFIG_JSON="$(mktemp)"
    jq --argjson port "$CRAFTY_INTERNAL_PORT" '.http_port = $port' "$CRAFTY_CONFIG_JSON" > "$TMP_CONFIG_JSON"
    mv "$TMP_CONFIG_JSON" "$CRAFTY_CONFIG_JSON"
else
    mkdir -p "$(dirname "$CRAFTY_CONFIG_JSON")"
    jq -n --argjson port "$CRAFTY_INTERNAL_PORT" '{http_port: $port}' > "$CRAFTY_CONFIG_JSON"
fi

echo "[crafty4] Crafty web interface will listen internally on http port $CRAFTY_INTERNAL_PORT"
echo "[crafty4] Ingress will be served on $INGRESS_IP:$INGRESS_PORT"

USE_SSL=$(jq -r '.ssl // false' "$CONFIG_PATH")
CERTFILE=$(jq -r '.certfile // "fullchain.pem"' "$CONFIG_PATH")
KEYFILE=$(jq -r '.keyfile // "privkey.pem"' "$CONFIG_PATH")
CERT_DIR="$DATA_ROOT/config/web/certs"
DIRECT_SSL_READY="false"

if [ "$USE_SSL" = "true" ]; then
    if [ -f "/ssl/$CERTFILE" ] && [ -f "/ssl/$KEYFILE" ]; then
        mkdir -p "$CERT_DIR"
        cp -f "/ssl/$CERTFILE" "$CERT_DIR/commander.cert.pem"
        cp -f "/ssl/$KEYFILE" "$CERT_DIR/commander.key.pem"
        DIRECT_SSL_READY="true"
    else
        echo "[crafty4] ssl is enabled but /ssl/$CERTFILE or /ssl/$KEYFILE was not found, falling back to plain http on the direct port"
    fi
fi

chown -R crafty:root /data "$DATA_ROOT"
chmod -R g+rw /data "$DATA_ROOT"

mkdir -p /etc/nginx/conf.d
rm -f /etc/nginx/conf.d/*.conf

if [ "$DEBUG_LOGGING" = "true" ]; then
    ACCESS_LOG_LINE="access_log /dev/stdout debug_redirects;"
else
    ACCESS_LOG_LINE="access_log off;"
fi

ACCESS_LOG_LINE="$ACCESS_LOG_LINE" \
envsubst '${ACCESS_LOG_LINE}' \
    < /etc/nginx/templates/nginx.conf.template \
    > /etc/nginx/nginx.conf

INGRESS_LISTEN_IP="$INGRESS_IP" \
INGRESS_LISTEN_PORT="$INGRESS_PORT" \
CRAFTY_INTERNAL_PORT="$CRAFTY_INTERNAL_PORT" \
envsubst '${INGRESS_LISTEN_IP} ${INGRESS_LISTEN_PORT} ${CRAFTY_INTERNAL_PORT}' \
    < /etc/nginx/templates/ingress.conf.template \
    > /etc/nginx/conf.d/ingress.conf

if [ -n "$DIRECT_PORT" ]; then
    if [ "$DIRECT_SSL_READY" = "true" ]; then
        DIRECT_LISTEN_PORT="$DIRECT_PORT" \
        CRAFTY_INTERNAL_PORT="$CRAFTY_INTERNAL_PORT" \
        DIRECT_SSL_CERTFILE="$CERT_DIR/commander.cert.pem" \
        DIRECT_SSL_KEYFILE="$CERT_DIR/commander.key.pem" \
        envsubst '${DIRECT_LISTEN_PORT} ${CRAFTY_INTERNAL_PORT} ${DIRECT_SSL_CERTFILE} ${DIRECT_SSL_KEYFILE}' \
            < /etc/nginx/templates/direct-ssl.conf.template \
            > /etc/nginx/conf.d/direct.conf
        echo "[crafty4] direct access on port $DIRECT_PORT will use https with the provided certificate"
    else
        DIRECT_LISTEN_PORT="$DIRECT_PORT" \
        CRAFTY_INTERNAL_PORT="$CRAFTY_INTERNAL_PORT" \
        envsubst '${DIRECT_LISTEN_PORT} ${CRAFTY_INTERNAL_PORT}' \
            < /etc/nginx/templates/direct.conf.template \
            > /etc/nginx/conf.d/direct.conf
        echo "[crafty4] direct access on port $DIRECT_PORT will use plain http"
    fi
fi

if [ "$DEBUG_LOGGING" = "true" ]; then
    echo "[crafty4] generated /etc/nginx/nginx.conf:"
    cat /etc/nginx/nginx.conf

    echo "[crafty4] generated /etc/nginx/conf.d/ingress.conf:"
    cat /etc/nginx/conf.d/ingress.conf

    echo "[crafty4] network interfaces visible to this container:"
    ip -4 addr show 2>/dev/null | grep -E "inet |^[0-9]+:" || echo "[crafty4] 'ip' command unavailable"
fi

nginx -t

CRAFTY_ARGS="-d -i"
if [ "$DEBUG_LOGGING" = "true" ]; then
    CRAFTY_ARGS="$CRAFTY_ARGS -v"
fi
echo "[crafty4] log_level is '$LOG_LEVEL', starting Crafty with: $CRAFTY_ARGS"

cd /crafty
sudo --preserve-env=TZ,CRAFTY_DATA_ROOT -u crafty env TZ="$TZ" CRAFTY_DATA_ROOT="$DATA_ROOT" bash -c "source ./.venv/bin/activate && exec python3 main.py $CRAFTY_ARGS" &
CRAFTY_PID=$!

nginx &
NGINX_PID=$!

sleep 2
if kill -0 "$NGINX_PID" 2>/dev/null; then
    if [ "$DEBUG_LOGGING" = "true" ]; then
        echo "[crafty4] nginx is running, listening sockets:"
        ss -ltnp 2>/dev/null | grep nginx || netstat -ltnp 2>/dev/null | grep nginx || echo "[crafty4] could not list sockets (ss/netstat unavailable)"
    fi
else
    echo "[crafty4] error: nginx exited immediately after start, ingress will not work"
fi

on_term() {
    kill -TERM "$CRAFTY_PID" "$NGINX_PID" 2>/dev/null
    wait "$CRAFTY_PID" "$NGINX_PID" 2>/dev/null
}
trap on_term TERM INT

wait -n "$CRAFTY_PID" "$NGINX_PID"
EXIT_CODE=$?

on_term

exit "$EXIT_CODE"
