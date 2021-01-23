#!/usr/bin/env bash

rm syncplay.pyz

pip install -r <(pipenv lock -r) --target dist/

cp -r -t dist syncplay

shiv \
  --site-packages dist \
  --uncompressed \
  --reproducible \
  -p '/usr/bin/env python3' \
  -o syncplay.pyz \
  -e syncplay.ep_server:main

rm -r dist
