#!/bin/bash

cd /home/metacat
. /home/metacat/test/config.env

export FLASK_APP=app.py
export FLASK_ENV=development

cd catalogue_ui
flask run -h $FLASKHOST -p $FLASKPORT