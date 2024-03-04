'''Module for data preparation for display.'''
import math
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from modules.mongo_lib import MongoLib
from typing import List, Dict, Union

def get_db_connection(log: str) -> MongoLib:
    '''Creates and returns a connection to MongoDB.

    Args:
        log (str): Name of log to use.

    Returns:
        MongoLib: MongoLib object.
    '''
    logging.getLogger(log)
    conn = MongoLib(log)
    conn.switch_db("analytics")

    return conn


def merge_lists(list1: List[Dict], list2: List[Dict], type: str) -> List[Dict]:
    '''Merges two metadata lists by modality or tag, as specified by the type.
       The first list is to be the main, largest list. The second list is to be
       the smallest list to be absorbed by the first list.

    Args:
        list1 (List[Dict]): Metadata list 1 which is updated and returned.
        list2 (List[Dict]): Metadata list 2 absorbed by list 1.
        type (str): "modality" or "tag" to indicate what to merge the lists by.

    Returns:
        List[Dict]: Merged metadata.
    '''
    if type == "modality":
        for mod2 in list2:
            for mod1 in list1:
                if mod2["modality"] == mod1["modality"]:
                    mod1.update(mod2)
    elif type == "tag":
        for tag1 in list1:
            for tag2 in list2:
                if tag2["tag"] == tag1["tag"]:
                    tag1.update(tag2)

    return list1


def format_mods(tags: List) -> List:
    '''For each tag in a list of tags, transforms the list of modalities a tag
       is found in into a comma separated string.

    Args:
        tags (List): List of tags with lists of modalities.

    Returns:
        List: List of tags with comma separated string of modalities.
    '''
    for tag in tags:
        if tag.get("modalities", None):
            tag["modalities"] = [str(mod) for mod in tag["modalities"]]
            tag["modalities"] = ", ".join(tag["modalities"])

    return tags


def format_counts(modality: Dict) -> Dict:
    '''Formats a modality's count metadata for plotting.

    Args:
        modality (Dict): Modality metadata.

    Returns:
        Dict: Dictionary of lists for plotting.
    '''
    plot_format = {
        "dates": [],
        "images_raw": [],
        "series_raw": [],
        "study_raw": [],
        "images_staging": [],
        "series_staging": [],
        "study_staging": [],
        "images_live": [],
        "series_live": [],
        "study_live": [],
    }

    for attr in modality:
        if "countsPerMonth" in attr:
            modality[attr] = fix_month_counts(modality[attr])

            if "Raw" in attr:
                for count in modality[attr]:
                    plot_format["dates"].append(count["date"])
                    plot_format["images_raw"].append(count["imageCount"])
                    plot_format["series_raw"].append(count["seriesCount"])
                    plot_format["study_raw"].append(count["studyCount"])

            if "Staging" in attr:
                for count in modality[attr]:
                    plot_format["images_staging"].append(count["imageCount"])
                    plot_format["series_staging"].append(count["seriesCount"])
                    plot_format["study_staging"].append(count["studyCount"])

            if "Live" in attr:
                for count in modality[attr]:
                    plot_format["images_live"].append(count["imageCount"])
                    plot_format["series_live"].append(count["seriesCount"])
                    plot_format["study_live"].append(count["studyCount"])
        elif any(term in attr for term in ["No", "std"]):
            modality[attr] = "{:,}".format(float(modality[attr]))

    return plot_format


def tag_stats(tags: List[Dict], modality: bool=False) -> Dict:
    stats = {
        "public": {
          "Public": 0,
          "Private": 0
        },
        "confidentiality": {},
        "promotion": {}
    }

    if modality:
        stats["sparseness"] = {
            "Unknown": 0,
            "<50%": 0,
            "50-60%": 0,
            "60-70%": 0,
            "70-80%": 0,
            "80-90%": 0,
            ">=90%": 0
        }

    for tag in tags:
        # Group tags by public status
        if tag["public"] == "true":
            stats["public"]["Public"] += 1
        else:
            stats["public"]["Private"] += 1

        # Group tags by promotion status
        if tag["promotionStatus"] in stats["promotion"].keys():
            stats["promotion"][tag["promotionStatus"]] += 1
        else:
            stats["promotion"][tag["promotionStatus"]] = 0 

        # Group tags by confidentiality profile
        if tag.get("basicProfile", None):
            if tag["basicProfile"] in stats["confidentiality"].keys():
                stats["confidentiality"][tag["basicProfile"]] += 1
            else:
                stats["confidentiality"][tag["basicProfile"]] = 0
        else:
            if "Unknown" in stats["confidentiality"].keys():
                stats["confidentiality"]["Unknown"] += 1
            else:
                stats["confidentiality"]["Unknown"] = 0

        if modality:
            # Group tags by completeness
            if tag.get("completenessRaw", None):
                frequency = float(tag["completenessRaw"])

                if frequency > 0 and frequency < 50:
                    stats["sparseness"]["<50%"] += 1
                elif frequency >= 50 and frequency < 60:
                    stats["sparseness"]["50-60%"] += 1
                elif frequency >= 60 and frequency < 70:
                    stats["sparseness"]["60-70%"] += 1
                elif frequency >= 70 and frequency < 80:
                    stats["sparseness"]["70-80%"] += 1
                elif frequency >= 80 and frequency < 90:
                    stats["sparseness"]["80-90%"] += 1
                elif frequency >= 90:
                    stats["sparseness"][">=90%"] += 1
            else:
                stats["sparseness"]["Unknown"] += 1

    return stats


def monthly_counts(modalities, stage):
    min_date = datetime.now()
    max_date = datetime.strptime("2010/01", "%Y/%m")

    for mod in modalities:
        for attr in mod:
            if "countsPerMonth" in attr:
                mod[attr] = fix_month_counts(mod[attr])

        if mod["promotionStatus"] == "available":
            mod_min_date = min(datetime.strptime(count["date"], "%Y/%m") for count in mod["countsPerMonthRaw"])
            mod_max_date = max(datetime.strptime(count["date"], "%Y/%m") for count in mod["countsPerMonthRaw"])

            if mod_min_date < min_date:
                min_date = mod_min_date

            if mod_max_date > max_date:
                max_date = mod_max_date

    dates = {
        "dates": list(OrderedDict(((min_date + timedelta(_)).strftime("%Y/%m"), None) for _ in range((max_date - min_date).days)).keys()),
        "image_counts": {},
        "series_counts": {},
        "study_counts": {}
    }

    for mod in modalities:
        if mod["promotionStatus"] == "available":
            image_counts = {}
            series_counts = {}
            study_counts = {}

            for vdate in dates["dates"]:
                for count in mod[f"countsPerMonth{stage}"]:
                    if datetime.strptime(vdate, "%Y/%m") == datetime.strptime(count["date"], "%Y/%m"):
                        image_counts[vdate] = count["imageCount"]
                        series_counts[vdate] = count["seriesCount"]
                        study_counts[vdate] = count["studyCount"]

            dates["image_counts"][mod["modality"]] = list(image_counts.values())
            dates["series_counts"][mod["modality"]] = list(series_counts.values())
            dates["study_counts"][mod["modality"]] = list(study_counts.values())

    return dates


def format_label_stats(labels):
    modalities = []
    chartLabels = []
    chartData = []

    vertical = [
        {"label": "% labelled series",
         "data": [],
         "stack": "Stack 0"
        },
        {"label": "% unlabelled series",
         "data": [],
         "stack": "Stack 0"
        },
    ]

    for mod in labels:
        modalities.append(mod["modality"])
        chartLabels += list(mod["labels"].keys())

    chartLabels = set(chartLabels)

    for label in chartLabels:
        chartData.append({
            "label": label,
            "data": [],
            "stack": "Stack 0"
        })

    for mod in labels:
        for chart_label in chartData:
            if chart_label["label"] in mod["labels"].keys():
                chart_label["data"].append(mod["labels"][chart_label["label"]]["percentLabelledSeries"])
            else:
                chart_label["data"].append("0")

    return modalities, chartData


def calculate_percentage(no1: Union[int, str], no2: Union[int, str]) -> str:
    '''Calculates percentage.

    Args:
        no1 (int): Number.
        no2 (int): Number.

    Returns:
        float: (no1*100)/no2
    '''
    perc = (int(no1) * 100) / int(no2)

    return "{:.2f}".format(perc)


def fix_month_counts(counts: List[Dict]) -> List[Dict]:
    '''Monthly count cleaning required for live datasets.
       Edge cases such as dates below the expected minimum date and
       dates such as "1/1" can cause the counts at different stages to be
       misaligned.

    Args:
        counts (List): List of counts by monthly date.

    Returns:
        List[Dict]: Cleaned counts in the same format.
    '''
    fixed_counts = []
    mincount = datetime.strptime("2010/01", "%Y/%m")

    for count in counts:
        if count.get("date", None):
            fcount = datetime.strptime(count["date"], "%Y/%m")

            if count["date"] != "1/1" and fcount >= mincount:
                fixed_counts.append(count)

    return fixed_counts
