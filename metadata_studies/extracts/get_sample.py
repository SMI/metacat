'''Save a given number of sample images to file.
'''
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
    parser.add_argument("--database", "-d",
                        help="Name of database to pull sample from.",
                        type=str, required=False, default="dicom")
    parser.add_argument("--collection", "-c",
                        help="Name of collection to pull sample from.",
                        type=str, required=False, default="series")
    parser.add_argument("--number", "-n",
                        help="Number of sample images.", type=int,
                        required=False, default=1)
    parser.add_argument("--output", "-o",
                        help="Path and name of output JSON file.",
                        type=str, required=False,
                        default="series_samples.json")
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
    collection = args.collection
    number = args.number
    output = args.output
    log_path = args.log

    log = flib.setup_logging(log_path, f"{collection}_sample", "debug")
    logging.getLogger(log)

    mongo = MongoLib(log)
    mongo.switch_db(database)

    samples = mongo.sample(collection, number)

    mongo.disconnect()

    flib.json_dump(samples, output)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
