'''Group records by StudyDescription, SeriesDescription, BodyPartExamined.
   Label all three columns and measure the agreement of labelling across
   columns.
'''
import os
import re
import argparse
import logging
from datetime import datetime
from typing import List, Dict
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
    parser.add_argument("--modality", "-mo",
                        help="Modality name. Default to CT.", type=str,
                        required=False, default="CT")
    parser.add_argument("--output", "-o",
                        help=("Output directory path. "
                              "Default to current directory."),
                        type=str, required=False, default=".")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. "
                              "Default to current directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def label_list(terms: Dict, values: List) -> Dict:
    '''Takes in a list of unique values for labelling
       by applying a given dictionary.

    Args:
        terms (Dict): [{"Term": "term", "Label": "label/label"}]
        values (List): ["Value"]

    Returns:
        Dict: {"Value": "label/label"}
    '''
    labelled_values: Dict = {}

    for value in values:
        cleaned_value = re.sub(r'[^A-Za-z\s]', ' ', value)
        cleaned_value = ' '.join(cleaned_value.split()).lower()

        for term, labels in terms.items():
            if term in cleaned_value or term.replace(" ", "") in cleaned_value:
                if labelled_values.get(value, None):
                    labelled_values[value].append(labels)
                else:
                    labelled_values[value] = [labels]

        if labelled_values.get(value, None):
            labelled_values[value] = '/'.join(set(labelled_values[value]))

    return labelled_values

def main(args: argparse.Namespace) -> None:
    '''Main function.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    rdb = args.db
    term_file = args.terms
    modality = args.modality
    output = args.output
    log_path = args.log

    log = flib.setup_logging(log_path, f"{modality}_group_labelling", "debug")
    logging.getLogger(log)

    now = datetime.now()
    timestamp = f"{now.year}-{now.month:02}-{now.day:02}"

    # Extract groups from modality table
    mysql = MySQLib(log)
    mysql.use_db(rdb)

    columns = "St.StudyDescription, Se.SeriesDescription, Se.BodyPartExamined"
    study_descr = mysql.group_by_col(f"{modality}_StudyTable", columns)
    groups = [{
        "StudyDescription": str(group[0]).encode("ascii", "ignore").decode(),
        "SeriesDescription": str(group[1]).encode("ascii", "ignore").decode(),
        "BodyPartExamined": str(group[2]).encode("ascii", "ignore").decode(),
        "CombinationCount": int(str(group[3]))
    } for group in study_descr]
    groups_count = len(groups)

    logging.info("%s groups extracted from modality %s", groups_count, modality)

    # Import terms dictionary: [{"Term": "Term", "Label": "label/label"}]
    terms = flib.load_csv(term_file)
    term_dict = {term["Term"]: term["Label"] for term in terms}

    # Extract unique values for each column for labelling
    unique_studies = list({group["StudyDescription"] for group in groups})
    unique_series = list({group["SeriesDescription"] for group in groups})
    unique_bpx = list({group["BodyPartExamined"] for group in groups})

    # Label unique values
    labelled_studies = label_list(term_dict, unique_studies)
    labelled_series = label_list(term_dict, unique_series)
    labelled_bpx = label_list(term_dict, unique_bpx)

    # Initialise labelled and unlabelled group lists
    labelled_groups = []
    unlabelled_groups = []

    # Groups: [{"StudyDescription": "", "SeriesDescription": "", "BodyPartExamined": "", "CombinationCount": #}]
    for group in groups:
        # If the StudyDescription exists and has been labelled
        if group.get("StudyDescription", None) and group["StudyDescription"] in labelled_studies:
            group_copy = group.copy()

            for label in labelled_studies[group["StudyDescription"]].split("/"):
                # For each label applied to StudyDescription, confidence +1
                confidence = 1
                # If SeriesDescription also has this label, confidence +1
                if labelled_series.get(group["SeriesDescription"], None) and label in labelled_series.get(group["SeriesDescription"], None):
                    confidence += 1
                # If BodyPartExamined also has this label, confidence +1
                if labelled_bpx.get(group["BodyPartExamined"], None) and label in labelled_bpx.get(group["BodyPartExamined"], None):
                    confidence += 1
                # Apply StudyDescription labels to the group
                group_copy[label] = "{:.2f}".format((confidence * 100) / 3)

            # Add labelled group to labelled list
            labelled_groups.append(group_copy)
        # If the StudyDescription does not exist and cannot be labelled
        elif group.get("SeriesDescription", None) and group["SeriesDescription"] in labelled_series:
            group_copy = group.copy()

            for label in labelled_series[group["SeriesDescription"]].split("/"):
                # For each label applied to SeriesDescription, confidence +1
                confidence = 1
                # If BodyPartExamined also has this label, confidence +1
                if labelled_bpx.get(group["BodyPartExamined"], None) and label in labelled_bpx.get(group["BodyPartExamined"], None):
                    confidence += 1
                # Apply SeriesDescription labels to the group
                group_copy[label] = "{:.2f}".format((confidence * 100) / 3)

            # Add labelled group to labelled list
            labelled_groups.append(group_copy)
        # If BodyPartExamined is the only one that exists and has been labelled
        elif group.get("BodyPartExamined", None) and group["BodyPartExamined"] in labelled_bpx:
            group_copy = group.copy()

            for label in labelled_bpx[group["BodyPartExamined"]].split("/"):
                # For each label applied to BodyPartExamined, confidence +1
                confidence = 1
                # Apply BodyPartExamined labels to the group
                group_copy[label] = "{:.2f}".format((confidence * 100) / 3)

            # Add labelled group to labelled list
            labelled_groups.append(group_copy)
        # If none of the columns exist nor can be labelled
        else:
            unlabelled_groups.append(group)

    if labelled_groups:
        # Calculate the % of labelled groups
        labelled_groups_count = groups_count - len(unlabelled_groups)
        perc_labelled_groups = "{:.2f}".format((labelled_groups_count * 100) / groups_count)
        logging.info("%s (%s%s) of unique groups were labelled", labelled_groups_count, perc_labelled_groups, "%")
        # Sort groups by CombinationCount
        labelled = sorted(labelled_groups, key=lambda d: d['CombinationCount'], reverse=True)
        # Prepare and save output file
        labelled_header = [
            "StudyDescription",
            "SeriesDescription",
            "BodyPartExamined",
            "head",
            "neck",
            "chest",
            "abdomen",
            "pelvis",
            "upper_limb",
            "lower_limb",
            "spine",
            "whole_body",
            "CombinationCount"
        ]
        labelled_file = os.path.join(output, f"{modality}_mod_labelled_{timestamp}.csv")
        flib.csv_dump(labelled, labelled_file, labelled_header)

    if len(unlabelled_groups) > 1:
        # Count the % of unlabelled groups
        perc_unlabelled_groups = "{:.2f}".format((len(unlabelled_groups) * 100) / groups_count)
        logging.info("%s (%s%s) of groups were not labelled", len(unlabelled_groups), perc_unlabelled_groups, "%")
        # Sort groups by CombinationCount
        unlabelled = sorted(unlabelled_groups, key=lambda d: d['CombinationCount'], reverse=True)
        # Prepare and save output file
        unlabelled_header = [
            "StudyDescription",
            "SeriesDescription",
            "BodyPartExamined",
            "CombinationCount"
        ]
        unlabelled_file = os.path.join(output, f"{modality}_mod_unlabelled_{timestamp}.csv")
        flib.csv_dump(unlabelled, unlabelled_file, unlabelled_header)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
