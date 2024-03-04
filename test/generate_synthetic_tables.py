'''Pulls metadata documents from the MongoDB or a JSON file and creates or
   updates tables with the metadata split in image, series, studies tables.
'''
import argparse
import logging
from typing import Dict
from jinjasql import JinjaSql
import modules.file_lib as flib
from modules.mysql_lib import MySQLib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--sourcedb", "-s",
                        help=("Name of database to pull metadata from."
                              "Default to dicom."), type=str,
                        required=False, default="dicom")
    parser.add_argument("--collection", "-c",
                        help=("Name of collection to pull metadata from."
                              "Default to series."), type=str,
                        required=False, default="series")
    parser.add_argument("--destinationdb", "-d",
                        help=("Name of database to create/update tables to. "
                              "Default to 'smi'"), type=str, required=False,
                        default="smi")
    parser.add_argument("--modality", "-m",
                        help=("Modality as a prefix to destination tables. "
                              "Default to CT."), type=str, required=False,
                        default="CT")
    parser.add_argument("--schema", "-k",
                        help=("SQL script containing table creation and insert "
                              "queries."), type=str, required=True)
    parser.add_argument("--initialise", "-i",
                        help=("If mentioned, it recreates the database and "
                              "tables."), action="store_true")
    parser.add_argument("--aggregate", "-a",
                        help="If mentioned, it creates aggregate image tables.",
                        action="store_true")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current"
                              " directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def prep_query_vals(doc: Dict, query: str) -> Dict:
    def _unpack_list(item_list, list_key, columns):
        if all(isinstance(item, (str, int)) for item in item_list):
            columns[list_key] = ",".join(str(item) for item in item_list)
        else:
            for item in item_list:
                for key, value in item.items():
                    if isinstance(value, str):
                        if key in columns:
                            columns[key] = value

                    if isinstance(value, list):
                        columns = _unpack_list(value, key, columns)

        return columns

    query = query.split("\n")
    columns = {}

    for line in query:
        line = line.strip().strip(",")

        if line:
            if not any(symbol in line for symbol in ["(", ")", "{"]):
                columns[line] = None

    for key, value in doc.items():
        if isinstance(value, (str, int)):
            if key in columns:
                columns[key] = value

        if isinstance(value, list):
            columns = _unpack_list(value, key, columns)

    return columns


def get_image_type(doc: Dict) -> Dict:
    types = {
        "ORIGINAL": 0,
        "DERIVED": 0,
        "PRIMARY": 0,
        "SECONDARY": 0
    }

    for img_type in types:
        if img_type in doc["ImageType"]:
            types[img_type] += int(doc["header"]["ImagesInSeries"])

    return types


def main(args: argparse.Namespace) -> None:
    '''Main function for generating synthetic data.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    src_db = args.sourcedb
    collection = args.collection
    dest_db = args.destinationdb
    schema = args.schema
    modality = args.modality
    initialise = args.initialise
    aggregate = args.aggregate
    log_path = args.log

    log = flib.setup_logging(log_path, "synthetic_table_generation", "debug")
    logging.getLogger(log)

    queries = flib.load_jinjasql(schema)

    create_queries = []
    insert_queries = []

    for query in queries.split(";"):
        if aggregate and "_ImageTable" in query:
            continue

        if not aggregate and "_Aggregate" in query:
            continue

        if "CREATE" in query:
            create_queries.append(f"{query};")

        if "REPLACE" in query or "INSERT" in query:
            insert_queries.append(f"{query};")

    if initialise:
        mysql = MySQLib(log)
        jinja = JinjaSql(param_style="qmark")
        params = {"Database": dest_db, "Modality": modality}

        for query_str in create_queries:
            query, values = jinja.prepare_query(query_str, params)
            mysql.execute_query(query)

            if "DATABASE" in query_str:
                mysql.use_db(dest_db)

        mysql.disconnect()

    logging.info("Pulling metadata from database.")
    mongo = MongoLib(log)
    mongo.switch_db(src_db)
    docs = list(mongo.search(collection, {"Modality": modality}))

    if not docs:
        logging.info("No documents could be found in %s.%s", src_db, collection)
    else:
        logging.info("Found %s documents in %s.%s", len(docs), src_db,
                     collection)
        mysql = MySQLib(log)
        mysql.use_db(dest_db)
        jinja = JinjaSql(param_style="qmark")

        for doc in docs:
            for query in insert_queries:
                if "_Aggregate" in query:
                    values = get_image_type(doc)
                    values["SeriesInstanceUID"] = doc["SeriesInstanceUID"]
                else:
                    values = prep_query_vals(doc, query)

                values["Modality"] = modality

                query_bit, values_bit = jinja.prepare_query(query, values)
                mysql.execute_query(query_bit, tuple(values_bit))

if __name__ == '__main__':
    commands = argparser()
    main(commands)
