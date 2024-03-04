'''Import DICOM standard metadata from
   https://github.com/innolitics/dicom-standard.
'''
import re
import argparse
import logging
from datetime import datetime
from typing import Dict
import modules.file_lib as flib
from modules.mongo_lib import MongoLib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", "-f",
                        help=("Path to directory containing standard metadata"
                              " files."), type=str, required=True)
    parser.add_argument("--cataloguedb", "-c",
                        help="Name of catalogue database. Default to analytics.",
                        type=str, required=False, default="analytics")
    parser.add_argument("--log", "-l",
                        help=("Log directory path. Default to current "
                              "directory."), type=str, required=False,
                        default=".")

    return parser.parse_args()


def remove_tags(text: str) -> str:
    '''Removes HTML tags from given string.

    Args:
        text (str): Text containing HTML tags.

    Returns:
        str: Text with no HTML tags.
    '''
    text_re = re.compile(r'<[^>]+>')
    return text_re.sub('', text)


def import_modality_meta(database: str, log: str, filepath: str) -> None:
    '''Get modality description, link to standard, and ciodID.

    Args:
        filepath (str): Path to modalities DICOM standard metadata file.
        mods (List[Dict]): Modalities metadata from catalogue.

    Returns:
        List[Dict]: Modalities metadata + description and ID.
    '''
    mongo = MongoLib(log)
    mongo.switch_db(database)
    mods = list(mongo.search("modalities", {}, {"modality": 1}))
    mods_std = flib.load_json(filepath)

    for mod in mods:
        for mod_std in mods_std:
            if f"{mod['modality']} Image" == mod_std["name"]:
                logging.info("Extracting modality %s details...",
                             mod['modality'])

                mod["dicomID"] = mod_std["id"]
                mod["description"] = remove_tags(mod_std["description"])
                mod["linkToStandard"] = mod_std["linkToStandard"]
                mod["standardDate"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    mongo.upsert_modalities(mods, "modalities")
    mongo.disconnect()


def get_tags_conf(tags_file: str, conf_file: str) -> Dict:
    '''Merges tag and tag confidentiality metadata.

    Args:
        tags_file (str): Tag metadata filename.
        conf_file (str): Tag confidentiality filename.

    Returns:
        Dict: Tag metadata.
    '''
    logging.info("Getting tags confidentiality information...")
    tags = flib.load_json(tags_file)
    tags_conf = flib.load_json(conf_file)

    for tag in tags:
        for tag_conf in tags_conf:
            if tag["tag"] == tag_conf["tag"]:
                tag.update(tag_conf)

    return tags


def get_modules(mod_levels_file: str) -> Dict:
    '''Extracts modules and associated information entity from given file.

    Args:
        mod_levels_file (str): Modules metadata filename.

    Returns:
        Dict: Modules and associated information entity.
    '''
    logging.info("Getting modules and their information entity...")
    mod_levels = flib.load_json(mod_levels_file)
    modules: Dict = {}

    for module in mod_levels:
        if module["moduleId"] in modules:
            modules[module["moduleId"]].append(module["informationEntity"])
        else:
            modules[module["moduleId"]] = [module["informationEntity"]]

    return modules


def get_tags_descr(tags: Dict, modules: Dict, mod_tags_file: str) -> Dict:
    '''Adds tag descriptions to a given tag dictionary.

    Args:
        tags (Dict): Dictionary of tags.
        modules (Dict): Dictionary of modules.
        mod_tags_file (str): Modules and tags filename.

    Returns:
        Dict: Tag metadata.
    '''
    logging.info("Getting tags description...")
    mod_tags = flib.load_json(mod_tags_file)

    for tag in tags:
        levels = []

        for mod_tag in mod_tags:
            if tag["tag"] == mod_tag["tag"]:
                if mod_tag["type"] != "None":
                    tag["type"] = mod_tag["type"]

                tag["description"] = remove_tags(mod_tag["description"])
                tag["linkToStandard"] = mod_tag["linkToStandard"]

                if mod_tag["moduleId"] in modules:
                    levels += modules[mod_tag["moduleId"]]

        levels = list(set(levels))

        if levels:
            if "Study" in levels:
                tag["informationEntity"] = "Study"
            elif "Series" in levels:
                tag["informationEntity"] = "Series"
            elif "Image" in levels:
                tag["informationEntity"] = "Image"
            else:
                tag["informationEntity"] = ', '.join(levels)

    return tags


def import_tags_meta(database: str, log: str, tags_meta: Dict) -> None:
    '''Upserts tag metadata.

    Args:
        database (str): Name of database to upsert tag metadata to.
        log (str): Log name.
        tags_meta (Dict): Tag metadata.
    '''
    mongo = MongoLib(log)
    mongo.switch_db(database)
    tags = list(mongo.search("tags", {}, {"tag": 1, "promotionStatus": 1}))

    for tag in tags:
        if tag["promotionStatus"] != "blocked":
            for tag_meta in tags_meta:
                if tag["tag"] == tag_meta["keyword"]:
                    tag["dicomID"] = tag_meta.pop("tag")
                    tag.update(tag_meta)
                    del tag["keyword"]
                    del tag["id"]
                    tag["standardDate"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

    mongo.upsert_tags(tags, "tags")
    mongo.disconnect()


def main(args: argparse.Namespace) -> None:
    '''Main function for extracting a modality's metadata to JSON file.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    file_path = args.files
    cataloguedb = args.cataloguedb
    log_path = args.log

    log = flib.setup_logging(log_path, "standard_import", "debug")
    logging.getLogger(log)

    filepaths = flib.ls_dir(file_path, "json")
    filenames = {
        flib.split_path(filepath)[1]: filepath for filepath in filepaths
    }

    import_modality_meta(cataloguedb, log, filenames.get("modalities.json", None))
    tags = get_tags_conf(
        filenames.get("tags.json", None),
        filenames.get("tag_confidentiality.json", None)
    )
    modules = get_modules(filenames.get("modality_levels.json", None))
    tags = get_tags_descr(
        tags, modules,
        filenames.get("modality_tags.json", None)
    )

    import_tags_meta(cataloguedb, log, tags)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
