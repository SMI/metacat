'''Extraction of following metadata:
   - Total number of available MRI scans (series) and of CT scans (series)
   - .csv file listing all available PUBLIC tags for MRI and CT modalities,
     with columns showing:
      - For each tag, the percentage of available scans containing values in
        that field
      - Of that, the percentage of usable values i.e. not null values or empty
        strings
      - Whether the tag has been promoted to eDRIS yet
      - Any percentages of less than 5% to be replaced with 5%.
'''
import os
import argparse
import modules.file_lib as flib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", "-d",
                        help=("Name of catalogue database. "
                              "Default to analytics."), type=str,
                        required=False, default="analytics")
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


def main(args: argparse.Namespace) -> None:
    '''Main function for updating modality-level counts.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    database = args.db
    modality = args.modality
    output = args.output
    log_path = args.log

    log = flib.setup_logging(log_path, f"{modality}_tag_meta_extract",
                             "debug")

    mongo = MongoLib(log)
    mongo.switch_db(database)
    mod_meta = mongo.get_modality_meta(modality)
    tags_meta = list(mongo.search(
        "tags", {},
        {"tag": 1, "promotionStatus": 1, "informationEntity": 1, "_id": 0}
    ))
    mongo.disconnect()

    tags = []

    for mod_tag_meta in mod_meta["tags"]:
        for tag_meta in tags_meta:
            if tag_meta["tag"] == mod_tag_meta["tag"] and tag_meta["public"] == "true" and tag_meta["promotionStatus"] != "blocked":
                tag = {
                    "Tag": tag_meta["tag"],
                }

                if tag_meta["promotionStatus"] == "available":
                    tag["Promoted"] = 1
                else:
                    tag["Promoted"] = 0

                tag["Level"] = tag_meta.get("informationEntity", "")

                comp = int(float(mod_tag_meta["completenessRaw"]))

                tag["Completeness"] = comp if comp > 5 else 5

                tags.append(tag)

    meta_header = [
        "Tag",
        "Level",
        "Completeness",
        "Promoted"
    ]

    meta_file = os.path.join(output, f"{modality}_tag_metadata.csv")
    flib.csv_dump(tags, meta_file, meta_header)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
