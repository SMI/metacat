'''Create label tables and populate them from CSV.
'''
import csv
import argparse
import logging
import modules.file_lib as flib
from modules.mysql_lib import MySQLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", "-d",
                        help="Name of relational database. Default to labels.",
                        type=str, required=False, default="labels")
    parser.add_argument("--modality", "-mo",
                        help="Modality name. Default to CT.", type=str,
                        required=True)
    parser.add_argument("--input", "-i",
                        help=("Location of data file to be loaded "
                              "in the new table."), type=str, required=True)
    parser.add_argument("--log", "-l", help=("Log directory path. "
                        "Default to current directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    '''Main function.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    rdb = args.db
    modality = args.modality
    input_file = args.input
    log_path = args.log
    table_name = f"{modality}_BodyPart_Mapping"

    log = flib.setup_logging(log_path, f"{modality}_populate_table", "debug")
    logging.getLogger(log)

    # List tables
    mysql = MySQLib(log)

    mysql.execute_query(f"CREATE DATABASE IF NOT EXISTS {rdb};")

    mysql.use_db(rdb)

    mysql.execute_query(f"DROP TABLE IF EXISTS {table_name};")

    tables = mysql.list_tables()
    tables = [table[0] for table in tables]

    if not tables or table_name not in tables:
        query = (f"CREATE TABLE IF NOT EXISTS {table_name} ("
                 "StudyDescription VARCHAR(255) BINARY, "
                 "SeriesDescription VARCHAR(255) BINARY, "
                 "BodyPartExamined VARCHAR(255) BINARY, "
                 "head FLOAT, "
                 "neck FLOAT, "
                 "chest FLOAT, "
                 "abdomen FLOAT, "
                 "pelvis FLOAT, "
                 "upper_limb FLOAT, "
                 "lower_limb FLOAT, "
                 "spine FLOAT, "
                 "whole_body FLOAT, "
                 "CombinationCount INT, "
                 "PRIMARY KEY (StudyDescription, SeriesDescription, BodyPartExamined)"
                 ");")

    mysql.execute_query(query)

    query = (f"CREATE INDEX {table_name}_StudyDescription_indx ON {table_name} (StudyDescription);")
    mysql.execute_query(query)

    query = (f"CREATE INDEX {table_name}_SeriesDescription_indx ON {table_name} (SeriesDescription);")
    mysql.execute_query(query)

    query = (f"CREATE INDEX {table_name}_BodyPartExamined_indx ON {table_name} (BodyPartExamined);")
    mysql.execute_query(query)

    with open(input_file, encoding="utf-8") as data:
        reader = csv.DictReader(data)
        header = reader.fieldnames

        table_cols = str(tuple(header)).replace("'", "`")
        markers = str(tuple(['%s' for val in header]))
        markers = f"{markers}".replace("'", "")

        query = (f"INSERT INTO {table_name} {table_cols} VALUES {markers};")

        pks = ["StudyDescription", "SeriesDescription", "BodyPartExamined"]

        for row in reader:
            row_vals = [None if row[col] == "" and col not in pks else row[col].replace("\"", "'") for col in header]
            mysql.execute_query(query, tuple(row_vals))


if __name__ == '__main__':
    commands = argparser()
    main(commands)
