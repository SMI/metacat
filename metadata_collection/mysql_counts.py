'''MySQL counts - works for Maria as well.
   Modality-level attributes:
   {
        "modality": <MODALITY>
        "totalNoImages<Staging|Live>": <COUNT>,
        "totalNoSeries<Staging|Live>": <COUNT>,
        "totalNoStudies<Staging|Live>": <COUNT>,
        "countsPerMonth<Staging|Live>": [
            {"date": <TIMESTAMP>,
             "imageCount": <COUNT>,
             "seriesCount": <COUNT>,
             "studyCount": <COUNT>
            }
        ]
    }
'''
import argparse
import logging
import multiprocessing
from typing import Dict
from datetime import datetime
import modules.file_lib as flib
from modules.mysql_lib import MySQLib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--rdb", "-d",
                        help=("Name of relational database. "
                              "Default to data_load2."), type=str,
                        required=False, choices=["data_load2", "smi", "metacat_test"],
                        nargs="+", default=["data_load2"])
    parser.add_argument("--status", "-s",
                        help=("Status associated with database. "
                              "Default to 'Staging'."), type=str,
                        required=False, choices=["Live", "Staging"],
                        nargs="+", default=["Staging"])
    parser.add_argument("--cataloguedb", "-c",
                        help="Name of catalogue database. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. "
                              "Default to current directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def get_modalities(database: MySQLib) -> Dict:
    '''Returns a list of main tables by modality in the current database.
       Main tables are considered to be:
       - <MODALITY>_StudyTable
       - <MODALITY>_SeriesTable
       - <MODALITY>_ImageTable

    Args:
        database (MySQLib): MySQLib instance

    Returns:
        Dict: {<MODALITY>: {
                   "modality": <MODALITY>,
                   "tables": [<TABLE_NAME>]
              }}
    '''
    tables = database.list_tables()
    modalities: dict = {}

    for table in tables:
        table_name = table[0]

        if table_name.endswith(("ImageTable", "Aggregate_ImageType", "SeriesTable", "StudyTable")):
            table_split = table_name.split("_", 1)
            modality = table_split[0]

            if len(table_split) > 1:
                if modality in modalities:
                    main_table = f"{table_split[0]}_{table_split[1]}"
                    modalities[modality]["tables"].append(main_table)
                    sorted_list = list(set(modalities[modality]["tables"]))
                    modalities[modality]["tables"] = sorted_list
                else:
                    modalities[modality] = {
                        "modality": modality,
                        "tables": [table_name]
                    }

    return modalities


def total_counts(log: str, database: str, modality: Dict, status: str) -> Dict:
    mysql = MySQLib(log)
    mysql.use_db(database)

    if modality["modality"] == "SR":
        modality[f"totalNoStudies{status}"] = int(mysql.count_sr_table("StudyInstanceUID"))
        modality[f"totalNoSeries{status}"] = int(mysql.count_sr_table("SeriesInstanceUID"))
        modality[f"totalNoImages{status}"] = int(mysql.count_sr_table("SOPInstanceUID"))
    else:
        for table in modality["tables"]:
            if "Aggregate" in table:
                count = int(mysql.count_aggregate_table(table))
            else:
                count = int(mysql.count_table(table))

            if "Image" in table:
                modality[f"totalNoImages{status}"] = count
            elif "Series" in table:
                modality[f"totalNoSeries{status}"] = count
            elif "Study" in table:
                modality[f"totalNoStudies{status}"] = count

    mysql.disconnect()

    return modality


def month_counts(log: str, database: str, modality: Dict, status: str) -> Dict:
    modality[f"countsPerMonth{status}"] = []

    mysql = MySQLib(log)
    mysql.use_db(database)

    if modality["modality"] == "SR":
        study_counts = mysql.count_sr_per_month("StudyInstanceUID")
        series_counts = mysql.count_sr_per_month("SeriesInstanceUID")
        image_counts = mysql.count_sr_per_month("SOPInstanceUID")
    else:
        study_counts = mysql.count_studies_per_month(modality["modality"])
        series_counts = mysql.count_series_per_month(modality["modality"])

        if f"{modality['modality']}_Aggregate_ImageType" in modality["tables"]:
            image_counts = mysql.count_aggregate_images_per_month(modality["modality"])
        else:
            image_counts = mysql.count_images_per_month(modality["modality"])

    for study_count in study_counts:
        month_count = {
            "date": study_count[0]
        }

        for image_count in image_counts:
            if image_count[0] == month_count["date"]:
                month_count["imageCount"] = int(image_count[1])

        for series_count in series_counts:
            if series_count[0] == month_count["date"]:
                month_count["seriesCount"] = int(series_count[1])

        month_count["studyCount"] = int(study_count[1])

        modality[f"countsPerMonth{status}"].append(month_count)

    mysql.disconnect()

    # Fill missing months
    modality.pop("tables", None)

    if modality[f"countsPerMonth{status}"]:
        modality[f"countsPerMonth{status}"] = flib.fill_blanks(modality[f"countsPerMonth{status}"])

    modality[f"countsDate{status}"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    return modality


def get_counts_wrapper(log: str, rdb: str, cataloguedb: str, status: str,
                       modality: Dict) -> None:
    '''Wrapper for multiprocessing pool.

    Args:
       log (str): Log location.
       rdb (str): Name of relational DB to connect to.
       cataloguedb (str): Name of MongoDB catalogue database.
       status (str): Status associated with rdb (Staging|Live).
       modality (Dict): Modality dictionary containing modality name
                        and list of tables.
    '''
    modality = total_counts(log, rdb, modality, status)
    modality = month_counts(log, rdb, modality, status)

    mongo = MongoLib(log)
    mongo.switch_db(cataloguedb)
    mongo.upsert_modalities([modality], "modalities")
    mongo.disconnect()


def main(args: argparse.Namespace) -> None:
    '''Main function for updating modality-level counts.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    rdb = args.rdb[0]
    status = args.status[0]
    cataloguedb = args.cataloguedb
    log_path = args.log

    log = flib.setup_logging(log_path, f"mysql_counts_{rdb}", "debug")
    logging.getLogger(log)

    mysql = MySQLib(log)
    mysql.use_db(rdb)

    modalities = get_modalities(mysql)

    mysql.disconnect()

    with multiprocessing.Pool(processes=len(modalities)) as pool:
        for _, modality in modalities.items():
            try:
                pool.apply_async(
                    get_counts_wrapper,
                    [log, rdb, cataloguedb, status, modality]
                )
            except Exception as error:
                logging.info("Process for modality %s failed: %s",
                             modality['modality'], error)

        pool.close()
        pool.join()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
