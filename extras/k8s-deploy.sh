#!/bin/sh

kubectl label secret syncplay-tls-secret "app.kubernetes.io/part-of=syncplay"

kubectl rollout restart deployment/syncplay-main
