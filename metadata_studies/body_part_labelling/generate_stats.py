'''Extract unique, cleaned (lowercased, no symbols or additional spacing) values
   of a specified column from across a list of specified modalities.
'''
import os
import argparse
import logging
import modules.file_lib as flib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", "-d",
                        help="Name of catalogue database. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--outputs", "-o",
                        help="Path to directory containing outputs.", type=str,
                        required=True)
    parser.add_argument("--version", "-v", help="Tag dictionary version.",
                        type=str, required=True)
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
    db = args.db
    outputs = args.outputs
    version = args.version
    log_path = args.log

    log = flib.setup_logging(log_path, "bodypart_labelling_stats", "debug")
    logging.getLogger(log)

    stats = {
        "dictionaryVersion": version,
        "totalNoLabelledSeries": 0,
        "totalNoSeriesLive": 0,
        "totalNoValidatedSeries": 0,
        "stats": []
    }

    mongo = MongoLib(log)
    mongo.switch_db(db)
    mods_meta = list(mongo.search(
        "modalities", {}, 
        {"_id": 0, "modality": 1, "totalNoSeriesLive": 1, "countsDateLive": 1}
    ))

    mongo.disconnect()

    _, _, files = next(os.walk(outputs))
    files = [filename for filename in files if ".csv" in filename]
    non_labels = ["StudyDescription", "SeriesDescription", "BodyPartExamined", "CombinationCount"]

    for filename in files:
        if "StudyDescription" in filename:
            data = flib.load_csv(os.path.join(outputs, filename))

            if "_labelled" in filename:
                if "_validate" in filename:
                    for row in data:
                        if row["ManualValidation"] == "1":
                            stats["totalNoValidatedSeries"] += int(row["SeriesCount"])

        if "mod_labelled" in filename:
            mod = filename.split("_")[0]

            for mod_meta in mods_meta:
                if mod == mod_meta["modality"]:
                    stats["labellingDate"] = filename.split("_")[3].split(".")[0]
                    mod_meta["totalNoLabelledSeries"] = 0
                    data = flib.load_csv(os.path.join(outputs, filename))

                    stats["totalNoSeriesLive"] += int(mod_meta["totalNoSeriesLive"])
                    mod_meta["totalNoLabelledSeries"] = sum(int(row["CombinationCount"]) for row in data)
                    stats["totalNoLabelledSeries"] += int(mod_meta["totalNoLabelledSeries"])
                    mod_meta["percentLabelledSeries"] = "{:.2f}".format(100 * (mod_meta["totalNoLabelledSeries"]/mod_meta["totalNoSeriesLive"]))

                    labels = {}

                    for key in data[0].keys():
                        if key not in non_labels:
                            labels[key] = {
                                "labelledNoSeries": 0,
                                "avgConfidence": []
                            }

                    rows_stats = []

                    for row in data:
                        row_stats = {"label": [], "conf": [], "count": 0}

                        for label in labels:
                            if row[label]:
                                row_stats["count"] = row["CombinationCount"]

                                for row_label in labels:
                                    if row[row_label]:
                                        if row_label not in row_stats["label"]:
                                            row_stats["label"].append(row_label)
                                            row_stats["conf"].append(row[row_label])

                        if len(row_stats["label"]) > 1:
                            row_stats["label"] = " & ".join(row_stats["label"])
                            row_stats["conf"] = "{:.2f}".format(sum(float(avg) for avg in row_stats["conf"]) / len(row_stats["conf"]))
                        else:
                            row_stats["label"] = row_stats["label"][0]
                            row_stats["conf"] = row_stats["conf"][0]

                        rows_stats.append(row_stats)

                    for row_stat in rows_stats:
                        if row_stat["label"] not in labels.keys():
                            labels[row_stat["label"]] = {
                                "labelledNoSeries": 0,
                                "avgConfidence": []
                            }

                    redundant_labels = []

                    for label in labels:
                        label_count = 0

                        for row_stat in rows_stats:
                            if row_stat["label"] == label:
                                label_count += 1
                                labels[label]["labelledNoSeries"] += int(row_stat["count"])
                                labels[label]["avgConfidence"].append(float(row_stat["conf"]))

                        labels[label]["percentLabelledSeries"] = "{:.2f}".format(100 * (labels[label]["labelledNoSeries"]/mod_meta["totalNoSeriesLive"]))

                        if float(labels[label]["percentLabelledSeries"]) < 1:
                            redundant_labels.append(label)
                        else:
                            if labels[label]["avgConfidence"]:
                                labels[label]["avgConfidence"] = "{:.2f}".format(sum(labels[label]["avgConfidence"]) / label_count)
                            else:
                                labels[label]["avgConfidence"] = 0

                    for label in redundant_labels:
                        del labels[label]

                    mod_meta["labels"] = labels
                    stats["stats"].append(mod_meta)

    if stats["totalNoLabelledSeries"]:
        stats["percentLabelledSeries"] = "{:.2f}".format(100 * (stats["totalNoLabelledSeries"]/stats["totalNoSeriesLive"]))

    if stats["totalNoValidatedSeries"]:
        stats["percentValidatedSeries"] = "{:.2f}".format(100 * (stats["totalNoValidatedSeries"]/stats["totalNoSeriesLive"]))

    mongo = MongoLib(log)
    mongo.switch_db(db)
    mongo.upsert_obj(
        stats, "bodyparts", 
        {"dictionaryVersion": stats["dictionaryVersion"]},
        {"$set": stats}
    )

    mongo.disconnect()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
