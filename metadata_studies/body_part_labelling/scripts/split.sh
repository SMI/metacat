#!/usr/bin/env bash
# Example: split.sh BodyPartExamined_labelled.csv 4 10000 BodyPartExamined_labelled_top_10000_validate.csv

if [ $# -lt 4 ]; then
  echo "Error: Usage $0 <FILE> <COUNT_COL_POSITION> <GREATER_THAN_OR_EQUAL_TO_VALUE> <OUTPUT_FILE> [args...]"
  exit 1
fi

set -ex

FILE="$1"
POS="$2"
VAL="$3"
OUT="$4"

find "$FILE" | xargs -n 1 -I {} awk -F',' 'NR==2 || $'${POS}'>='${VAL} "{}" > "$OUT" &&

wc -l "$FILE"
wc -l "$OUT"
