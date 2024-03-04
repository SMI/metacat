#!/bin/bash

set -euo pipefail

export FLASK_APP=/home/metacat/catalogue_ui/app.py
export FLASK_ENV=development

flask run --host 0.0.0.0