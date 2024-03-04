'''Tag quality metadata.
   Modality-level attributes:
   {
       "tags": [
           {"tag": "<TAG_NAME>",
            "completenessRaw": "<PERCENT>",
            "tagQualityDateRaw": "<TIMESTAMP>"
           }
       ]
   }
'''
import argparse
import logging
import multiprocessing
from typing import List
from datetime import datetime
import modules.file_lib as flib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", "-d",
                        help="Database where data lives. Default to analytics.",
                        type=str, required=False,
                        choices=["analytics", "dicom", "data_load2", "smi"],
                        nargs="+", default=["analytics"])
    parser.add_argument("--priority", "-p",
                        help=("Prioritise tags by whether they are available "
                              "or public. Default to all tags."),
                        type=str, required=False, nargs="+",
                        choices=["available", "public"], default=["all"])
    parser.add_argument("--cataloguedb", "-c",
                        help=("Database where catalogue lives. Default to "
                              "analytics."), type=str, required=False,
                        default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current"
                              " directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def custom_error_callback(error):
    logging.error("Process failed: %s", error)


def tag_quality_wrapper(database: str, cataloguedb: str, log: str,
                        tag: str, modalities: List) -> None:
    '''Wrapper for Mongo multiprocessing pool.
       Creates and runs a query for a tag.
       Saves facet output to catalogue.

    Args:
        database (str): Database where data lives.
        cataloguedb (str): Database where catalogue lives.
        log (str): Log path start a new database connection.
        tag (str): Tag name.
        modalities (List): Dictionary of modalities.
    '''
    logging.info("Processing tag %s", tag)
    mongo = MongoLib(log)
    mongo.switch_db(database)
    quality_meta = mongo.get_tag_quality("series", tag)

    logging.info("Received tag %s quality metadata. Preparing...", tag)

    mongo.switch_db(cataloguedb)

    for modality in modalities:
        total = int(modality["totalNoImagesRaw"])

        for mod_count in quality_meta:
            if mod_count["_id"] == modality["modality"]:
                for mod_tag in modality["tags"]:
                    if tag == mod_tag["tag"]:
                        tag_meta = {"tag": tag}
                        exists = int(mod_count["exists"])
                        empty_str = int(mod_count["emptyStr"])
                        completeness = 100 * ((exists - empty_str) / total)

                        tag_meta["completenessRaw"] = float("{:.2f}".format(completeness))
                        tag_meta["tagQualityDateRaw"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

                        mongo.update_mod_tag_quality(
                            modality["modality"], tag_meta, "modalities"
                        )

    mongo.disconnect()


def main(args: argparse.Namespace) -> None:
    '''Main function for updating modality-level tag quality stats.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    database = args.database[0]
    priority = args.priority[0]
    cataloguedb = args.cataloguedb
    log_path = args.log

    log = flib.setup_logging(log_path, f"tag_quality_facet_{database}", "debug")
    logging.getLogger(log)

    logging.info("Analysing %s tags.", priority)

    mongo = MongoLib(log)
    mongo.switch_db(cataloguedb)
    mod_meta = list(mongo.search(
        "modalities", {"promotionStatus": {"$ne": "blocked"}},
        {"_id": 0, "modality": 1, "tags": 1, f"totalNoImagesRaw": 1}
    ))

    mongo.switch_db(cataloguedb)

    tags_meta = []

    if priority == "available":
        tags_meta = list(mongo.search(
            "tags", {"promotionStatus": "available"},
            {"tag": 1, "_id": 0}
        ))
    elif priority == "public":
        tags_meta = list(mongo.search(
            "tags", {"public": "true"},
            {"tag": 1, "_id": 0}
        ))

    logging.info("Extracted %s tags of priority %s from catalogue", len(tags_meta), priority)

    starmap = [(database, cataloguedb, log, tag["tag"], mod_meta) for tag in tags_meta]

    with multiprocessing.Pool(50) as pool:
        pool.starmap_async(tag_quality_wrapper, starmap, chunksize=50, error_callback=custom_error_callback)

        pool.close()
        pool.join()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
