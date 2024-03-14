#!/bin/bash

. /home/metacat/test/config.env
cd /home/metacat/metadata_collection

# Create base metadata for new modalities and tags
python3 populate_catalogue.py -d dicom -i -l logs/ &&
# Create blocklists
python3 create_blocklists.py -m ../docs/modality_blocklist.json -t ../docs/tag_blocklist.json -b "Unknown" -l logs/
# Set tag public status (public/private)
python3 public_status.py -l logs/ &&
# Perform raw counts
python3 mongo_counts.py -d dicom -o modality -l logs/ &&
# Set promotion status for blocked modalities and tags with default to unavailable for all
python3 promotion_status.py -d analytics -s blocked -l logs/ &&
# Perform staging counts
python3 mysql_counts.py -d data_load2 -s Staging -l logs/ &&
# Set promotion status to processing if in the staging database
python3 promotion_status.py -d data_load2 -s processing -l logs/ &&
# Perform live counts
python3 mysql_counts.py -d smi -s Live -l logs/ &&
# Set promotion status to available if in the live database
python3 promotion_status.py -d smi -s available -l logs/ &&
# Analyse tag quality for public tags in the raw database
python3 tag_quality.py -d dicom -p public -l logs/ &&
# Download DICOM standard metadata from Innolitics
./scripts/dicom_standard_download.sh data
# Import DICOM standard metadata
python3 dicom_standard_import.py -f data/dicom_standard -l logs/ &&
# Run body part labelling
cd /home/metacat/test
./body_part_labelling.sh /tmp yes &&
cd /home/metacat/metadata_studies/body_part_labelling
python3 generate_stats.py -v 1 -o /tmp -l logs/ &&
# Start catalogue UI
cd /home/metacat/catalogue_ui
python3 app.py -e dev
