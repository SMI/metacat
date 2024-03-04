'''Tag public status:
   Tag-level attributes:
   {
       "public": "<True/False>"
   }
'''
import re
import logging
import argparse
import modules.file_lib as flib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", "-d",
                        help="Name of database. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current "
                              "directory."), type=str, required=False,
                        default=".")

    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    '''Main function for extracting a modality's metadata to JSON file.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    database = args.database
    log_path = args.log

    log = flib.setup_logging(log_path, "public_status", "debug")
    logging.getLogger(log)

    mongo = MongoLib(log)
    mongo.switch_db(database)

    # Extract tags
    tags = list(mongo.search("tags", {}, {"tag": 1}))

    # Apply regex looking for tag code
    regex = "^\([a-zA-Z0-9]{4},[a-zA-Z0-9]{4}"

    for tag in tags:
        if re.search(regex, tag["tag"]):
            tag["public"] = "false"
        else:
            tag["public"] = "true"

    # Update tags in database
    mongo.upsert_tags(tags, "tags")

    mongo.disconnect()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
