'''Generates a given number of synthetic documents matching a given
   document schema. Can output these to file or upload them into a MongoDB.

   https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
   https://pydicom.github.io/pydicom/stable/guides/element_value_types.html
'''

import argparse
import logging
import random
import string
from typing import Dict, List, Union
import modules.file_lib as flib
from datetime import timedelta, datetime
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", "-s",
                        help="Path to document schema.", type=str,
                        required=True)
    parser.add_argument("--number", "-n",
                        help="Number of documents to produce. Default to 1.",
                        type=int, required=False, default=1)
    parser.add_argument("--output", "-o",
                        help="Location and name of JSON output.",
                        type=str, required=False, default=None)
    parser.add_argument("--database", "-d",
                        help=("Name of database to upload files to."
                              "Default to dicom."), type=str,
                        required=False, default="dicom")
    parser.add_argument("--modality", "-m",
                        help=("Modality as a prefix to destination tables. "
                              "Default to CT."), type=str, required=False,
                        default="CT")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current"
                              " directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def generate_value(type: str, pattern: str = None) -> Union[str, int]:
    value: Union[str, int] = ""

    if type in ["IS", "US", "SL"]:
        if pattern:
            length = len(pattern)
        else:
            length = 1

        value = random.randint(1, (10 ** length) - 1)

    if type in ["DS", "FL"]:
        if pattern:
            length = len(pattern)
        else:
            length = 1

        value = str(random.uniform(1, (10 ** length) - 1))

    if type in ["CS", "LO", "SH", "PN"]:
        if pattern:
            if "|" in pattern:
                patterns = pattern.split("|")
                value_position = random.randint(0, len(patterns) - 1)
                value = str(patterns[value_position])
            else:
                length = len(pattern)

                if pattern.isdigit():
                    value = str(random.randint(1, (10 ** length) - 1))
                else:
                    value = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        else:
            value = ''.join(random.choices(string.ascii_letters + string.digits, k=5))

    if type == "DA":
        start_date = datetime(2018, 1, 1)
        end_date = datetime.now()
        date_range = end_date - start_date
        random_days = random.randint(0, date_range.days)
        random_date = start_date + timedelta(days=random_days)

        pattern = pattern if pattern else "%Y%m%d"
        value = random_date.strftime(pattern)

    if type == "TM":
        random_time = datetime.now().replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )

        pattern = pattern if pattern else "%H%M%S"
        value = random_time.strftime(pattern)

    if type == "UI":
        if pattern:
            if "." in pattern:
                parts = pattern.split(".")
                synthetic_parts = []

                for part in parts:
                    length = len(part)
                    synthetic_parts.append(str(random.randint(1, (10 ** length) - 1)))

                value = ".".join(synthetic_parts)
        else:
            value = ''.join(random.choices(string.ascii_letters + string.digits, k=5))

    return value


def generate_doc(schema: Dict) -> Dict:
    '''Generates a synthetic document based on a given JSON schema.

    Args:
        schema (Dict): JSON schema for document

    Returns:
        Dict: Synthetic document.
    '''
    def _process_val(value):
        descr = value.split("/")
        synthetic_value = ""

        if descr[0] == "None":
            synthetic_value = None
        elif descr[0] != "":
            if len(descr) == 1:
                synthetic_value = generate_value(descr[0])
            else:
                synthetic_value = generate_value(descr[0], descr[1])

        return synthetic_value

    def _process_list(item_list):
        synthetic_list = []

        for item in item_list:
            if isinstance(item, str):
                synthetic_list.append(_process_val(item))

            if isinstance(item, dict):
                synthetic_list.append(_process_dict(item))

        return synthetic_list

    def _process_dict(item_dict):
        synthetic_dict = {}

        for key, value in item_dict.items():
            if isinstance(value, str):
                synthetic_dict[key] = (_process_val(value))

            if isinstance(value, list):
                synthetic_dict[key] = (_process_list(value))

            if isinstance(value, dict):
                synthetic_dict[key] = (_process_dict(value))

        return synthetic_dict

    synthetic_doc: Dict = {}

    for key, value in schema.items():
        if isinstance(value, str):
            synthetic_doc[key] = _process_val(value)

        if isinstance(value, list):
            synthetic_doc[key] = _process_list(value)

        if isinstance(value, dict):
            synthetic_doc[key] = _process_dict(value)

    return synthetic_doc


def main(args: argparse.Namespace) -> None:
    '''Main function for generating synthetic data.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    schema_file = args.schema
    number = args.number
    output = args.output
    database = args.database
    modality = args.modality
    img_coll = f"image_{modality}"
    log_path = args.log

    log = flib.setup_logging(log_path, f"{modality}_synthetic_doc_generation", "debug")
    logging.getLogger(log)

    schema = flib.load_json(schema_file)

    series = []
    images = []

    for doc in range(number):
        series_doc = generate_doc(schema)
        series_doc["Modality"] = modality

        series.append(series_doc)
        img_count = 0

        while img_count in range(series_doc["header"]["ImagesInSeries"]):
            series_img = generate_doc(schema)
            series_img["Modality"] = modality
            series_img["SeriesInstanceUID"] = series_doc["SeriesInstanceUID"]
            series_img["StudyInstanceUID"] = series_doc["StudyInstanceUID"]
            series_img["StudyDate"] = series_doc["StudyDate"]

            images.append(series_img)
            img_count += 1

        logging.info("Generated synthetic document no. %s out of %s",
                     doc + 1, number)

    if database:
        mongo = MongoLib(log)
        mongo.switch_db(database)

        try:
            mongo.db[img_coll].insert_many(images)
            mongo.db["series"].insert_many(series)

            logging.info("Successfully inserted %s synthetic documents in the "
                         "%s and series collections.", number, img_coll)
        except (Exception) as error:
            logging.exception("Failed inserting synthetic documents in the "
                              "%s collection: %s", img_coll, error)

        mongo.disconnect()

    if output:
        flib.json_dump(series, output)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
