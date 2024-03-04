'''Populates catalogue with initial metadata.
   Has an initialisation flag that sets up the catalogue,
   if this is not set, it updates an already existing catalogue.
'''
import argparse
import logging
import multiprocessing
from typing import Tuple, List, Dict
import modules.file_lib as flib
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
                        help=("What collection to extract the modalities and "
                              "tags from. Default to series."), type=str,
                        required=False, choices=["series", "modality"],
                        nargs="+", default="series")
    parser.add_argument("--cataloguedb", "-c",
                        help=("Name of catalogue database. "
                              "Default to analytics."), type=str,
                        required=False, default="analytics")
    parser.add_argument("--init", "-i",
                        help=("Catalogue initialise or update. "
                              "Default to False, update."), action="store_true")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current"
                              " directory."), type=str, required=False,
                        default=".")

    return parser.parse_args()


def list_fields_wrapper(db_name: str, log: str, collection: str) -> List[Dict]:
    '''Wrapper for multiprocessing pool.

    Args:
       db_name (str): Database name.
       log (str): Log location.
       collection (str): Collection name.

    Returns:
       List[Dict]: [{"modality": <MODALITY>, "tags": [<TAG>]}]
    '''
    mongo = MongoLib(log)
    mongo.switch_db(db_name)

    fields = mongo.list_fields(collection)

    mongo.disconnect()

    return fields


def format_metadata(modalities_list: List[Dict]) -> Tuple:
    '''Prepares metadata for catalogue. Merges lists of modalities
       and tags from all collections into one. Splits this list into
       modalities and tag metadata.

    Args:
       modalities_list (List[Dict]): List of modalities and tags from
                                     all collections.

    Returns:
       Tuple: (
                [{"modality": <MODALITY>, "tags": [{"tag": <TAG>}]}],
                [{"tag": <TAG>, "modalities": [<MODALITY>]}]
                )
    '''
    mod_metadata: Dict = {}

    # Merge tag lists by modality
    for mod in modalities_list:
        mod_name = mod["modality"]

        if mod_name in mod_metadata:
            mod_metadata[mod_name] += mod["tags"]
        else:
            mod_metadata[mod_name] = mod["tags"]

    mod_collection = []

    # Prepare modalities metadata structure
    for mod, tags in mod_metadata.items():
        tags = list(set(tags))
        formatted_tags = []

        for tag in tags:
            tag_mod = {
                "tag": tag
            }

            formatted_tags.append(tag_mod)

        mod_meta = {
            "modality": mod,
            "tags": formatted_tags
        }

        mod_collection.append(mod_meta)

    tag_metadata: Dict = {}

    # Make a list of modalities for each tag
    for mod in mod_collection:
        mod_name = mod["modality"]

        for tag in mod["tags"]:
            tag_name = tag["tag"]

            if tag_name in tag_metadata:
                tag_metadata[tag_name].append(mod_name)
            else:
                tag_metadata[tag_name] = [mod["modality"]]

    tag_collection = []

    # Prepare tags metadata structure
    for tag, mods in tag_metadata.items():
        tag_meta = {
            "tag": tag,
            "modalities": list(set(mods))
        }

        tag_collection.append(tag_meta)

    return mod_collection, tag_collection


def merge_mods(old_mods: List[Dict], new_mods: List[Dict]) -> List[Dict]:
    '''Updates old modalities metadata with new modalities metadata.

    Args:
       old_mods (List[Dict]): Modalities metadata currently in catalogue.
       new_mods (List[Dict]): New modalities metadata to be added to
                              the catalogue.

    Returns:
       List[Dict]
    '''
    modalities = {}
    updated_mods = []

    for omod in old_mods:
        if omod["modality"] not in modalities:
            modalities[omod["modality"]] = [tag["tag"] for tag in omod["tags"]]

    for nmod in new_mods:
        if nmod["modality"] not in modalities:
            modalities[nmod["modality"]] = [tag["tag"] for tag in nmod["tags"]]
            old_mods.append(nmod)
        else:
            otags = set(modalities[nmod["modality"]])
            ntags = {tag["tag"] for tag in nmod["tags"]}
            modalities[nmod["modality"]] = list(set(ntags.difference(otags)))
            updated_mods.append(nmod["modality"])

    for omod in old_mods:
        if omod["modality"] in updated_mods:
            for tag in modalities[omod["modality"]]:
                tag_meta = {"tag": tag}
                omod["tags"].append(tag_meta)

    return old_mods


def merge_tags(old_tags: List[Dict], new_tags: List[Dict]) -> List[Dict]:
    '''Updates old tags metadata with new tags metadata.

    Args:
       old_tags (List[Dict]): tags metadata currently in catalogue.
       new_tags (List[Dict]): New tags metadata to be added to
                              the catalogue.

    Returns:
       List[Dict]
    '''
    otags = {tag["tag"] for tag in old_tags}
    ntags = {tag["tag"] for tag in new_tags}
    diff = list(set(ntags.difference(otags)))

    for ntag in new_tags:
        if ntag["tag"] in diff:
            old_tags.append(ntag)

    return old_tags


def main(args: argparse.Namespace) -> None:
    '''Main function for initialising catalogue collection.
        Creates tag and modality collections and indexes.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    pacs_db = args.pacsdb
    extract_on = args.on
    catalogue_db = args.cataloguedb
    init = args.init
    log_path = args.log

    log = flib.setup_logging(log_path, "initialise_catalogue", "debug")
    logging.getLogger(log)

    mongo = MongoLib(log)
    mongo.switch_db(pacs_db)

    if extract_on == "series":
        col_mods_and_tags = mongo.list_fields("series")
    else:
        collections = [col for col in mongo.list_collections()
                       if "image_" in col or col == "series"]
        col_mods_and_tags = []

        with multiprocessing.Pool(processes=len(collections)) as pool:
            async_results = [
                pool.apply_async(list_fields_wrapper, [pacs_db, log, collection])
                for collection in collections
            ]

            for result in async_results:
                try:
                    col_mods_and_tags += result.get()
                except Exception as error:
                    print(error)

            pool.close()
            pool.join()

    mod_collection, tag_collection = format_metadata(col_mods_and_tags)

    mongo.switch_db(catalogue_db)

    if init:
        # Initialise tag collection
        mongo.create_collection("tags")
        mongo.create_index("tags", "tag", uniq=True)

        # Initialise modality collection
        mongo.create_collection("modalities")
        mongo.create_index("modalities", "modality", uniq=True)

        mongo.upsert_modalities(mod_collection, "modalities")
        mongo.upsert_tags(tag_collection, "tags")
    else:
        current_mods = list(mongo.search("modalities"))
        updated_mods = merge_mods(current_mods, mod_collection)

        current_tags = list(mongo.search("tags"))
        updated_tags = merge_tags(current_tags, tag_collection)

        mongo.upsert_modalities(updated_mods, "modalities")
        mongo.upsert_tags(updated_tags, "tags")

    mongo.disconnect()


if __name__ == '__main__':
    commands = argparser()
    main(commands)
