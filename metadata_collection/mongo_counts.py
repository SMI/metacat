'''Mongo counts.
   Modality-level attributes:
   {
       "totalNoImagesRaw": "<COUNT>",
       "totalNoSeriesRaw": "<COUNT>",
       "totalNoStudiesRaw": "<COUNT>",
       "avgNoImagesPerSeries": "<COUNT>",
       "avgNoSeriesPerStudy": "<COUNT>",
       "countsPerMonthRaw": [
           {"date": "<TIMESTAMP>",
            "imageCount": "<COUNT>",
            "seriesCount": "<COUNT>",
            "studyCount": "<COUNT>"
           }
       ]
   }
'''
import argparse
import logging
from typing import Dict, List
import multiprocessing
import modules.file_lib as flib
from datetime import datetime
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--pacsdb", "-d",
                        help="Name of PACS database. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--on", "-o",
                        help=("What collection to base counts on. "
                              "Default to series."), type=str,
                        required=False, choices=["series", "modality"],
                        nargs="+", default="series")
    parser.add_argument("--modality", "-m",
                        help="Modality to count. Default to all.",
                        type=str, required=False, default="all")
    parser.add_argument("--cataloguedb", "-c",
                        help="Name of catalogue database. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current"
                              " directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def prepare_facet(collection: str) -> Dict:
    '''Prepares facet with the following faces:
       - imageCount
       - seriesCount
       - studiesCount
       - monthCount

    Args:
        collection (str): Collection name.

    Returns:
        Dict: Facet dictionary.
    '''
    if collection == "series":
        image_count = "$header.ImagesInSeries"
    else:
        image_count = 1

    facet = {
        "imageCount": [
            {"$group": {
                "_id": {
                    "modality": "$Modality",
                },
                "imageCount": {"$sum": image_count},
            }}
        ],
        "seriesCount": [
            {"$group": {
                "_id": {
                    "modality": "$Modality",
                    "seriesID": "$SeriesInstanceUID"
                },
                "imageCountPerSeries": {"$sum": image_count}
            }},
            {"$group": {
                "_id": {
                    "modality": "$_id.modality"
                },
                "avgNoImagesPerSeries": {"$avg": "$imageCountPerSeries"},
                "minNoImagesPerSeries": {"$min": "$imageCountPerSeries"},
                "maxNoImagesPerSeries": {"$max": "$imageCountPerSeries"},
                "stdDevImagesPerSeries": {"$stdDevPop": "$imageCountPerSeries"},
                "seriesCount": {"$sum": 1}
            }}
        ],
        "studiesCount": [
            {"$group": {
                "_id": {
                    "modality": "$Modality",
                    "studyID": "$StudyInstanceUID",
                    "seriesID": "$SeriesInstanceUID"
                },
            }},
            {"$group": {
                "_id": {
                    "modality": "$_id.modality",
                    "studyID": "$_id.studyID"
                },
                "seriesCountPerStudy": {"$sum": 1}
            }},
            {"$group": {
                "_id": {
                    "modality": "$_id.modality"
                },
                "avgNoSeriesPerStudy": {"$avg": "$seriesCountPerStudy"},
                "minNoSeriesPerStudy": {"$min": "$seriesCountPerStudy"},
                "maxNoSeriesPerStudy": {"$max": "$seriesCountPerStudy"},
                "stdDevSeriesPerStudy": {"$stdDevPop": "$seriesCountPerStudy"},
                "studyCount": {"$sum": 1}
            }}
        ],
        "monthCount": [
            {"$group": {
                "_id": {
                    "modality": "$Modality",
                    "studyID": "$StudyInstanceUID",
                    "seriesID": "$SeriesInstanceUID",
                    "studyYear": {
                        "$toString": {
                            "$year": {"$toDate": "$StudyDate"}
                        }
                    },
                    "studyMonth": {
                        "$toString": {
                            "$month": {"$toDate": "$StudyDate"}
                        }
                    }
                },
                "imageCount": {"$sum": image_count}
            }},
            {"$group": {
                "_id": {
                    "modality": "$_id.modality",
                    "studyID": "$_id.studyID",
                    "studyYear": "$_id.studyYear",
                    "studyMonth": "$_id.studyMonth"
                },
                "imageCount": {"$sum": "$imageCount"},
                "seriesCount": {"$sum": 1}
            }},
            {"$group": {
                "_id": {
                    "modality": "$_id.modality",
                    "studyYear": "$_id.studyYear",
                    "studyMonth": "$_id.studyMonth"
                },
                "imageCount": {"$sum": "$imageCount"},
                "seriesCount": {"$sum": "$seriesCount"},
                "studyCount": {"$sum": 1}
            }},
            {"$group": {
                "_id": {"modality": "$_id.modality"},
                "countsPerMonth": {
                    "$push": {
                        "date": {
                            "$concat": [
                                "$_id.studyYear",
                                "/",
                                "$_id.studyMonth"
                            ]
                        },
                        "imageCount": "$imageCount",
                        "seriesCount": "$seriesCount",
                        "studyCount": "$studyCount"
                    }
                }
            }},
            {"$project": {
                "_id": 0,
                "modality": "$_id.modality",
                "countsPerMonthRaw": "$countsPerMonth"
            }}
        ]
    }

    return facet


def format_counts(counts: List[Dict]) -> List[Dict]:
    '''Formats facet counts.

    Args:
       counts (List[Dict]): [{"imageCount": [{
                                "_id": {"modality": <MODALITY>},
                                "imageCount": <NUMBER>
                              }],
                              "seriesCount": [{
                                "_id": {"modality": <MODALITY>},
                                "avgNoImagesPerSeries": <NUMBER>,
                                "minNoImagesPerSeries": <NUMBER>,
                                "maxNoImagesPerSeries": <NUMBER>,
                                "stdDevImagesPerSeries": <NUMBER>,
                                "seriesCount": <NUMBER>
                              }],
                              "studiesCount": [{
                                "_id": {"modality": <MODALITY>},
                                "avgNoSeriesPerStudy": <NUMBER>,
                                "minNoSeriesPerStudy": <NUMBER>,
                                "maxNoSeriesPerStudy": <NUMBER>,
                                "stdDevSeriesPerStudy": <NUMBER>,
                                "studyCount": <NUMBER>


    Returns:
       List[Dict]: [{"modality": <MODALITY>,
                     "totalNoImagesRaw": <imageCount>,
                     "avgNoImagesPerSeriesRaw": <avgNoImagesPerSeries>,
                     "minNoImagesPerSeriesRaw": <minNoImagesPerSeries>,
                     "maxNoImagesPerSeriesRaw": <maxNoImagesPerSeries>,
                     "stdDevImagesPerSeriesRaw": <stdDevImagesPerSeries>,
                     "totalNoSeriesRaw": <seriesCount>,
                     "avgNoSeriesPerStudyRaw": <avgNoSeriesPerStudy>,
                     "minNoSeriesPerStudyRaw": <minNoSeriesPerStudy>,
                     "maxNoSeriesPerStudyRaw": <maxNoSeriesPerStudy>,
                     "stdDevSeriesPerStudyRaw": <stdDevSeriesPerStudy>,
                     "totalNoStudiesRaw": <studyCount>}]
    '''
    def _float(number):
        return "{:.2f}".format(number)

    formatted = []

    image_counts = counts[0]["imageCount"]
    series_counts = counts[0]["seriesCount"]
    study_counts = counts[0]["studiesCount"]
    monthly_counts = counts[0]["monthCount"]

    for count in image_counts:
        modality = {
            "modality": count["_id"]["modality"],
            "totalNoImagesRaw": count["imageCount"],
        }

        formatted.append(modality)

    for count in series_counts:
        for modality in formatted:
            if count["_id"]["modality"] == modality["modality"]:
                modality["avgNoImagesPerSeriesRaw"] = _float(count["avgNoImagesPerSeries"])
                modality["minNoImagesPerSeriesRaw"] = _float(count["minNoImagesPerSeries"])
                modality["maxNoImagesPerSeriesRaw"] = _float(count["maxNoImagesPerSeries"])
                modality["stdDevImagesPerSeriesRaw"] = _float(count["stdDevImagesPerSeries"])
                modality["totalNoSeriesRaw"] = count["seriesCount"]

    for count in study_counts:
        for modality in formatted:
            if count["_id"]["modality"] == modality["modality"]:
                modality["avgNoSeriesPerStudyRaw"] = _float(count["avgNoSeriesPerStudy"])
                modality["minNoSeriesPerStudyRaw"] = _float(count["minNoSeriesPerStudy"])
                modality["maxNoSeriesPerStudyRaw"] = _float(count["maxNoSeriesPerStudy"])
                modality["stdDevSeriesPerStudyRaw"] = _float(count["stdDevSeriesPerStudy"])
                modality["totalNoStudiesRaw"] = count["studyCount"]

    for count in monthly_counts:
        for modality in formatted:
            if count["modality"] == modality["modality"]:
                modality["countsPerMonthRaw"] = flib.fill_blanks(count["countsPerMonthRaw"])
                modality["countsDateRaw"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    return formatted


def get_counts_wrapper(pacsdb: str, cataloguedb: str, log: str, collection: str) -> None:
    '''Wrapper for multiprocessing pool.

    Args:
       pacsdb (str): Target database name.
       cataloguedb (str): Catalogue database name.
       log (str): Log location.
       collection (str): Collection name.
    '''
    mongo = MongoLib(log)
    mongo.switch_db(pacsdb)
    counts = mongo.run_facet(collection, prepare_facet(collection))
    counts = format_counts(counts)

    mongo.switch_db(cataloguedb)
    mongo.upsert_modalities(counts, "modalities")
    mongo.disconnect()


def main(args: argparse.Namespace) -> None:
    '''Main function for updating modality-level counts.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    pacsdb = args.pacsdb
    extract_on = args.on
    modality = args.modality
    cataloguedb = args.cataloguedb
    log_path = args.log

    log = flib.setup_logging(log_path, "mongo_counts", "debug")
    logging.getLogger(log)

    if extract_on == "series":
        get_counts_wrapper(pacsdb, cataloguedb, log, "series")
    else:
        mongo = MongoLib(log)
        mongo.switch_db(pacsdb)
        collections = [col for col in mongo.list_collections() if "image_" in col]
        mongo.disconnect()

        if modality == "all":
            with multiprocessing.Pool(processes=len(collections)) as pool:
                for collection in collections:
                    try:
                        pool.apply_async(
                            get_counts_wrapper,
                            [pacsdb, cataloguedb, log, collection]
                        )
                    except Exception as error:
                        logging.info("Process for collection %s failed: %s",
                                     collection, error)

                pool.close()
                pool.join()
        else:
            for collection in collections:
                if modality in collection:
                    get_counts_wrapper(pacsdb, cataloguedb, log, collection)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
