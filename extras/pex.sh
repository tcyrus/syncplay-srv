#!/bin/sh

pip freeze > requirements.txt

pex \
  --requirement=requirements.txt \
  -e syncplay \
  --sources-directory=. \
  --output-file=syncplay.pex

rm requirements.txt
