#!/bin/bash
# Example: ./metadata_collection/scripts/dicom_standard_download.sh ./metadata_collection/data

if [ $# -lt 1 ]; then
    echo "Error: Usage $0 <OUTPUT_PATH> [args...]"
    exit 1
fi

set -ex

OUTPUT_PATH="$1/dicom_standard"

echo "Creating 'dicom_standard' directory..."
mkdir -p $OUTPUT_PATH

echo "Downloading modalities..."
curl https://raw.githubusercontent.com/innolitics/dicom-standard/master/standard/ciods.json -o $OUTPUT_PATH/modalities.json ;

echo "Downloading tags..."
curl https://raw.githubusercontent.com/innolitics/dicom-standard/master/standard/attributes.json -o $OUTPUT_PATH/tags.json ;

echo "Downloading tag confidentiality profiles..."
curl https://raw.githubusercontent.com/innolitics/dicom-standard/master/standard/confidentiality_profile_attributes.json -o $OUTPUT_PATH/tag_confidentiality.json ;

echo "Downloading tag to modality mapping..."
curl https://raw.githubusercontent.com/innolitics/dicom-standard/master/standard/module_to_attributes.json -o $OUTPUT_PATH/modality_tags.json ;

echo "Downloading modality levels/modules..."
curl https://raw.githubusercontent.com/innolitics/dicom-standard/master/standard/ciod_to_modules.json -o $OUTPUT_PATH/modality_levels.json ;
