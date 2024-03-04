#!/usr/bin/env bash
# Example: ./run_group_labelling.sh /home/shared/data/body_parts/group_labelling/ yes

if [ $# -lt 2 ]; then
    echo "Error: Usage $0 <ABS_OUTPUT_PATH> <CREATE_TABLES> [args...]"
    exit 1
fi

set -ex

OUTPUT="$1"
TABLES="$2"
DATE=`date +"%Y-%m-%d"`
DATETIME=`date +"%Y-%m-%d-%H-%M-%S"`
LOG_PATH="/home/metacat/metadata_studies/body_part_labelling/logs"
LOG="$LOG_PATH"/"$DATETIME"_bodypart_labelling.log

if [ ! -d "$OUTPUT" ]; then
  mkdir "$OUTPUT"
fi

if [ ! -d "$LOG_PATH" ]; then
  mkdir "$LOG_PATH"
fi

cd /home/metacat/metadata_studies/body_part_labelling/

Modalities=("CT" "MR")

for modality in ${Modalities[@]}; do
  python3 group_labelling.py -d smi -t data/terms.csv -m "$modality" -o "$OUTPUT" -l "$LOG_PATH" && 

  if [ "$TABLES" = "yes" ]; then
    python3 create_tables.py -d labels -m "$modality" -i "$OUTPUT"/"$modality"_mod_labelled_"$DATE".csv -l "$LOG_PATH" &
  fi
done > "$LOG" 2>&1 &&

study_descr () {
  python3 tag_labelling.py -d smi -c StudyDescription -ta StudyTable -t data/terms.csv -m "CT,MR" -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1 &&

  python3 plot.py -t "$OUTPUT"/StudyDescription_col_labelled_"$DATE".csv -c StudyDescriptionCount -b studies -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1

  if [ -f "$OUTPUT"/StudyDescription_col_unlabelled.csv ]; then
    python3 plot.py -t "$OUTPUT"/StudyDescription_col_unlabelled_"$DATE".csv -c StudyDescriptionCount -b studies -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1
  fi
}

series_descr () {
  python3 tag_labelling.py -d smi -c SeriesDescription -ta SeriesTable -t data/terms.csv -m "CT,MR" -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1 &&

  python3 plot.py -t "$OUTPUT"/SeriesDescription_col_labelled_"$DATE".csv -c SeriesDescriptionCount -b series -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1  &

  if [ -f "$OUTPUT"/SeriesDescription_unlabelled.csv ]; then
    python3 plot.py -t "$OUTPUT"/SeriesDescription_col_unlabelled_"$DATE".csv -c SeriesDescriptionCount -b series -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1  &
  fi
}

body_part_examined () {
  python3 tag_labelling.py -d smi -c BodyPartExamined -ta SeriesTable -t data/terms.csv -m "CT,MR" -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1 &&

  python plot.py -t "$OUTPUT"/BodyPartExamined_col_labelled_"$DATE".csv -c BodyPartExaminedCount -b studies -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1  &

  if [ -f "$OUTPUT"/BodyPartExamined_unlabelled.csv ]; then
    python plot.py -t "$OUTPUT"/BodyPartExamined_col_unlabelled_"$DATE".csv -c BodyPartExaminedCount -b studies -o "$OUTPUT" -l "$LOG_PATH" > "$LOG" 2>&1
  fi
}

study_descr & series_descr & body_part_examined
