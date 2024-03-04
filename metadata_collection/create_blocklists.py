'''Creates blocklists of modalities and tags from JSON files.'''
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
    parser.add_argument("--tagblocklist", "-t",
                        help="Path to tag blocklist JSON file.",
                        type=str, required=False)
    parser.add_argument("--modalityblocklist", "-m",
                        help="Path to modality blocklist JSON file.",
                        type=str, required=False)
    parser.add_argument("--blockname", "-b",
                        help="Block those that contain specified string.",
                        type=str, required=False)
    parser.add_argument("--database", "-d",
                        help=("Location of blocklist collection. "
                              "Default to analytics."),
                        type=str, required=False, default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current"
                              " directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    '''Main function for initialising blocklist collections.
       Creates tag and modality collections and indexes.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    tag_blocklist = args.tagblocklist
    mod_block = args.modalityblocklist
    blockname = args.blockname
    database = args.database
    log_path = args.log

    log = flib.setup_logging(log_path, "create_blocklist", "debug")
    logging.getLogger(log)

    tags = list(flib.load_json(tag_blocklist)) if tag_blocklist else []
    modalities = list(flib.load_json(mod_block)) if mod_block else []

    mongo = MongoLib(log)
    mongo.switch_db(database)

    if blockname:
        tag_condition = {"tag": {"$regex": blockname}}
        blocked_tags = list(mongo.search("tags", tag_condition))

        logging.info("BLOCKED TAGS: %s", blocked_tags)

        for b_tag in blocked_tags:
            tag = {
                "tag": b_tag["tag"],
                "blockReason": f"Contains '{blockname}' and is considered unusable.",
                "modality": "all"
            }

            tags.append(tag)

        modality_condition = {"modality": {"$regex": blockname}}
        blocked_modalities = mongo.search("modalities", modality_condition)

        for b_mod in blocked_modalities:
            modality = {
                "modality": b_mod["modality"],
                "blockReason": f"Contains '{blockname}' and is considered unusable."
            }

            modalities.append(modality)

    # Initialise tag blocklist collection
    if tags:
        mongo.create_collection("tag_blocklist")
        mongo.create_index("tag_blocklist", "tag", uniq=True)
        mongo.upsert_tags(tags, "tag_blocklist")

    # Initialise modality blocklist collection
    if modalities:
        mongo.create_collection("modality_blocklist")
        mongo.create_index("modality_blocklist", "modality", uniq=True)
        mongo.upsert_modalities(modalities, "modality_blocklist")

    mongo.disconnect()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
