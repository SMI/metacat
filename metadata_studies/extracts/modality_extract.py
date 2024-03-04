'''Metadata extraction by modality to JSON.
'''
import argparse
import modules.file_lib as flib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--modality", "-m",
                        help="Modality name.", type=str, required=True)
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
    modality = args.modality
    modality_meta_filename = f"{modality}_modality_metadata.json"
    tags_meta_filename = f"{modality}_tags_metadata.json"
    log_path = args.log
    log_name = f"{modality}_metadata_extraction"

    log = flib.setup_logging(log_path, log_name, "debug")

    database = MongoLib(log)
    database.switch_db("analytics")

    modality_metadata = database.get_modality_meta(modality)
    tag_metadata = database.get_tag_meta(modality)

    database.disconnect()

    tags = [[tag["tag"]] for tag in tag_metadata]

    flib.json_dump(modality_metadata, modality_meta_filename)
    flib.json_dump(tag_metadata, tags_meta_filename)
    flib.csv_dump(tags, tags_meta_filename)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
