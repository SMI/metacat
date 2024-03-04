'''Extract unique, cleaned (lowercased, no symbols or additional spacing) values
   of a specified column from across a list of specified modalities.
'''
import os
import re
import argparse
import logging
from datetime import datetime
from typing import Dict
import modules.file_lib as flib
from modules.mysql_lib import MySQLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", "-d",
                        help="Name of relational database. Default to smi.",
                        type=str, required=False, default="smi")
    parser.add_argument("--terms", "-t",
                        help="Path to terms CSV file.", type=str,
                        required=True)
    parser.add_argument("--modalities", "-m",
                        help="Comma separated list of modalities. "
                             "Default to CT.", type=str, required=False,
                        default="CT")
    parser.add_argument("--column", "-c",
                        help="Column name. Default to StudyDescription.",
                        type=str, required=False, default="StudyDescription")
    parser.add_argument("--table", "-ta",
                        help="Table name. Default to StudyTable.", type=str,
                        required=False, default="StudyTable")
    parser.add_argument("--output", "-o",
                        help=("Output directory path. "
                              "Default to current directory."),
                        type=str, required=False, default=".")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. "
                              "Default to current directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()

def main(args: argparse.Namespace) -> None:
    '''Main function.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    rdb = args.db
    term_file = args.terms
    modalities = args.modalities.split(",")
    column = args.column
    table = args.table
    output = args.output
    log_path = args.log

    log = flib.setup_logging(log_path, f"{column}_labelling", "debug")
    logging.getLogger(log)

    now = datetime.now()
    timestamp = f"{now.year}-{now.month:02}-{now.day:02}"

    # Extract variables from each modality tables
    mysql = MySQLib(log)
    mysql.use_db(rdb)

    col_values: Dict = {}

    for modality in modalities:
        modality_values = mysql.group_by_col(f"{modality}_{table}", column)

        for modality_value in modality_values:
            value = str(modality_value[0])
            count = int(modality_value[1])
            # Clean value
            cleaned_value = re.sub(r'[^A-Za-z\s]', ' ', value)
            cleaned_value = ' '.join(cleaned_value.split()).lower()

            if cleaned_value and cleaned_value != "" and cleaned_value != "none":
                # If cleaned value exists in value list, append modality and count
                if col_values.get(cleaned_value, None):
                    col_values[cleaned_value]["Modalities"].append(modality)
                    col_values[cleaned_value]["Modalities"] = list(set(col_values[cleaned_value]["Modalities"]))
                    col_values[cleaned_value]["SeriesCount"] += count
                # If cleaned value is not in value list, add it
                else:
                    col_values[cleaned_value] = {
                        "Modalities": [modality],
                        "SeriesCount": count
                    }

    # Gather the total number of values and items for later statistics
    total_no_vals = len(col_values)
    total_no_items = sum(col_values[value]["SeriesCount"] for value in col_values)

    # Import terms dictionary: [{"Term": "Term", "Label": "label/label"}]
    terms = flib.load_csv(term_file)
    term_dict = {term["Term"]: term["Label"] for term in terms}

    # Initialise labelled and unlabelled value lists
    labelled_values = []
    unlabelled_values = []

    # Values: {column: {"Modalities": [], column"Count": #}}
    for col_value, col_details in col_values.items():
        # For each value, apply dictionary
        for term, labels in term_dict.items():
            if term in col_value or term.replace(" ", "") in col_value:
                # If value already has labels, extend existing labels
                if col_details.get("Labels", None):
                    col_details["Labels"].extend(labels.split("/"))
                    col_details["Labels"] = list(set(col_details["Labels"]))
                # If a value does not have labels, initialise labels
                else:
                    col_details["Labels"] = labels.split("/")

        # If a value has labels, add value to labelled list
        if col_details.get("Labels", None):
            labelled_values.append({
                column: col_value,
                "Labels": "/".join(col_details["Labels"]),
                "Modalities": "/".join(col_details["Modalities"]),
                "SeriesCount": col_details["SeriesCount"]
            })
        # If a value has no labels, add value to unlabelled list
        else:
            unlabelled_values.append({
                column: col_value,
                "Modalities": "/".join(col_details["Modalities"]),
                "SeriesCount": col_details["SeriesCount"]
            })

    if labelled_values:
        # Sort values by {column}Count
        labelled = sorted(labelled_values, key=lambda d: int(d["SeriesCount"]), reverse=True)
        # Calculate the % of labelled values
        perc_lab_vals = "{:.2f}".format((len(labelled) * 100) / total_no_vals)
        logging.info("%s (%s%s) of unique values were labelled", len(labelled), perc_lab_vals, "%")
        # Calculate the % of labelled items with value
        no_lab_items = sum(int(value["SeriesCount"]) for value in labelled)
        perc_lab_items = "{:.2f}".format((no_lab_items * 100) / total_no_items)
        logging.info("%s (%s%s) of items can be labelled", no_lab_items, perc_lab_items, "%")
        # Prepare and save output file
        labelled_header = list(labelled[0].keys())
        labelled_file = os.path.join(output, f"{column}_col_labelled_{timestamp}.csv")
        flib.csv_dump(labelled, labelled_file, labelled_header)

    if unlabelled_values:
        # Sort values by {column}Count
        unlabelled = sorted(unlabelled_values, key=lambda d: int(d["SeriesCount"]), reverse=True)
        # Calculate the % of unlabelled values
        perc_unlab_vals = "{:.2f}".format((len(unlabelled) * 100)/ total_no_vals)
        logging.info("%s (%s%s) of unique values were unlabelled", len(unlabelled), perc_unlab_vals, "%")
        # Calculate the % of unlabelled items with value
        no_unlab_items = sum(int(value["SeriesCount"]) for value in unlabelled)
        perc_unlab_items = "{:.2f}".format((no_unlab_items * 100)/ total_no_items)
        logging.info("%s (%s%s) of items can not be labelled", no_unlab_items, perc_unlab_items, "%")
        # Prepare and save output file
        unlabelled_header = list(unlabelled[0].keys())
        unlabelled_file = os.path.join(output, f"{column}_col_unlabelled_{timestamp}.csv")
        flib.csv_dump(unlabelled, unlabelled_file, unlabelled_header)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
