#!/bin/sh

podman build -t ghcr.io/weeb-poly/syncplay-server .

# kubectl create secret tls syncplay-tls-secret \
#   "--cert=${SYNCPLAY_TLS_PATH}/fullchain.pem" \
#   "--key=${SYNCPLAY_TLS_PATH}/privkey.pem" \
#   --dry-run -o yaml | kubectl apply -f -
# kubectl label secret syncplay-tls-secret app=syncplay

kubectl rollout restart deployment/syncplay-tcp-deployment

# podman create \
#     --env "SYNCPLAY_PASSWORD=${SYNCPLAY_PASSWORD}" \
#     --env "SYNCPLAY_SALT=${SYNCPLAY_SALT}" \
#     --env "SYNCPLAY_PORT=${SYNCPLAY_PORT}" \
#     --publish "${SYNCPLAY_PORT}:${SYNCPLAY_PORT}" \
#     --network bridge \
#     --env "SYNCPLAY_TLS_PATH=/app/cert" \
#     --mount "type=bind,source=${SYNCPLAY_TLS_PATH}/privkey.pem,target=/app/cert/privkey.pem,ro=true" \
#     --mount "type=bind,source=${SYNCPLAY_TLS_PATH}/fullchain.pem,target=/app/cert/fullchain.pem,ro=true" \
#     --name syncplay-server \
#     ghcr.io/weeb-poly/syncplay-server

# podman start syncplay-server
