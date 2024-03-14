#!/bin/bash

. /home/metacat/test/config.env
cd /home/metacat/test

python3 generate_synthetic_docs.py -s ../docs/general_doc_schema.json -n 100 -m CT -l logs/
python3 generate_synthetic_docs.py -s ../docs/general_doc_schema.json -n 80 -m MR -l logs/
python3 generate_synthetic_docs.py -s ../docs/general_doc_schema.json -n 60 -m US -l logs/
python3 generate_synthetic_docs.py -s ../docs/general_doc_schema.json -n 40 -m PR -l logs/
python3 generate_synthetic_docs.py -s ../docs/general_doc_schema.json -n 20 -m "*" -l logs/

python3 generate_synthetic_tables.py -k ../docs/general_table_schema.jinjasql -i -d data_load2 -m CT -c series -a -l logs/
python3 generate_synthetic_tables.py -k ../docs/general_table_schema.jinjasql -i -d data_load2 -m MR -c image_MR -l logs/
python3 generate_synthetic_tables.py -k ../docs/general_table_schema.jinjasql -i -d data_load2 -m US -c image_US -l logs/

python3 generate_synthetic_tables.py -k ../docs/general_table_schema.jinjasql -i -d smi -m CT -c series -a -l logs/
python3 generate_synthetic_tables.py -k ../docs/general_table_schema.jinjasql -i -d smi -m MR -c image_MR -l logs/
