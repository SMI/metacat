'''Tag promotion status by modality:
   Modality-level attributes:
   {
        "promotionStatus": "<blocked|unavailable|processing|available>",
        "promotionStatusDate": "<TIMESTAMP>"
   }

   Tag-level attributes:
   {
        "promotionStatus": "<blocked|unavailable|processing|available>",
        "promotionStatusDate": "<TIMESTAMP>"
   }
'''
import argparse
import logging
import modules.file_lib as flib
from datetime import datetime
from modules.mysql_lib import MySQLib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", "-d",
                        help="Name of database. Default to analytics.",
                        type=str, required=False,
                        choices=["analytics", "metacat_test", "data_load2", "smi"],
                        nargs="+", default=["analytics"])
    parser.add_argument("--status", "-s",
                        help="Status associated with database. Default to 'blocked'.",
                        type=str, required=False,
                        choices=["blocked", "processing", "available"],
                        nargs="+", default=["blocked"])
    parser.add_argument("--cataloguedb", "-c",
                        help="Metadata database name. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current "
                              "directory."), type=str, required=False,
                        default=".")

    return parser.parse_args()


def add_timestamp(objects):
    for obj in objects:
        obj["promotionStatusDate"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    return objects


def check_data(modality, status):
    '''Checking if there is any data promoted to the given stage.'''
    data = False

    if status == "processing":
        if modality.get("totalNoImagesStaging", None):
            if int(modality["totalNoImagesStaging"]) > 0:
                data = True
    else:
        if modality.get("totalNoImagesLive", None):
            if int(modality["totalNoImagesLive"]) > 0:
                data = True

    return data


def main(args: argparse.Namespace) -> None:
    '''Main function for extracting a modality's metadata to JSON file.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    database = args.database[0]
    status = args.status[0]
    cataloguedb = args.cataloguedb
    log_path = args.log

    log = flib.setup_logging(log_path, f"promotion_status_{database}", "debug")
    logging.getLogger(log)

    mongo = MongoLib(log)
    mongo.switch_db(cataloguedb)

    mod_meta = list(mongo.search("modalities"))
    tag_meta = list(mongo.search("tags"))

    mod_upsert = []
    tag_upsert = []

    if status == "blocked":
        mod_blocklist = [mod["modality"] for mod in mongo.search("modality_blocklist")]
        tag_blocklist = [tag["tag"] for tag in mongo.search("tag_blocklist")]

        for mod in mod_meta:
            if mod["modality"] in mod_blocklist:
                mod["promotionStatus"] = status
            else:
                if "promotionStatus" not in mod:
                    mod["promotionStatus"] = "unavailable"

            mod_upsert.append(mod)

        for tag in tag_meta:
            if tag["tag"] in tag_blocklist:
                tag["promotionStatus"] = status
            else:
                if "promotionStatus" not in tag:
                    tag["promotionStatus"] = "unavailable"

            tag_upsert.append(tag)
    elif status in ["processing", "available"]:
        mysql = MySQLib(log)
        mysql.use_db(database)

        tables = mysql.list_tables()
        table_prefixes = (
            "ImageTable", "Aggregate_ImageType", "SeriesTable", "StudyTable"
        )

        modalities = []
        columns = []

        for table in tables:
            if table[0].endswith(table_prefixes):
                modalities.append(table[0].split("_", 1)[0])

            for col in mysql.list_table_columns(table[0]):
                columns.append(col[0])

        mysql.disconnect()

        for mod in mod_meta:
            if mod["modality"] in set(modalities):
                data = check_data(mod, status)

                if data:
                    if "promotionStatus" in mod:
                        if mod["promotionStatus"] not in ["blocked", "available"]:
                            mod["promotionStatus"] = status
                            mod_upsert.append(mod)
                    else:
                        mod["promotionStatus"] = status
                        mod_upsert.append(mod)

        for tag in tag_meta:
            if tag["tag"] in set(columns):
                if "promotionStatus" in tag:
                    if tag["promotionStatus"] not in ["blocked", "available"]:
                        tag["promotionStatus"] = status
                        tag_upsert.append(tag)
                else:
                    tag["promotionStatus"] = status
                    tag_upsert.append(tag)

    if mod_upsert:
        mod_upsert = add_timestamp(mod_upsert)
        mongo.upsert_modalities(mod_upsert, "modalities")

    if tag_upsert:
        tag_upsert = add_timestamp(tag_upsert)
        mongo.upsert_tags(tag_upsert, "tags")

    mongo.disconnect()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
