#!/usr/bin/env bash
# exit on error
set -o errexit

pipenv install

pipenv shell
# pip install -r requirements/production.txt

# python manage.py collectstatic --no-input
python manage.py migrate