'''Library class that holds general functionality such as file
   manipulation, terminal commands etc.
'''
import os
import sys
import glob
import csv
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from bson import json_util
from typing import List, Union, Dict, Tuple


def setup_logging(log_path: str, log_name: str, level: str) -> str:
    '''Sets up logger.

    Args:
        log_path (str): Path for logging directory as specified in the
                        configuration file.
        log_name (str): Identifier name for log. This would be of format
                        `<RUNTYPE>_import`.
        level (str): INFO|DEBUG

    Returns:
        str: Current run log path and name.
    '''
    now = datetime.now()
    filename = os.path.join(log_path, (f"{now.year}-{now.month:02}-"
                                       f"{now.day:02}_{now.hour:02}-"
                                       f"{now.minute:02}-{now.second:02}"
                                       f"_{os.getpid()}_{log_name}.log"))

    Path(log_path).mkdir(parents=True, exist_ok=True)

    log_handlers: List[logging.Handler] = [
        logging.FileHandler(filename, mode='w')
    ]

    if sys.stdout.isatty():
        log_handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, level.upper()),
        handlers=log_handlers,
    )

    return filename


def json_dump(data: Union[Dict, List], filename: str) -> None:
    '''Dumps dictionary to JSON file.

    Args:
        data (Dict): Data dictionary.
        filename (str): Path and name of output JSON file.
    '''
    with open(filename, 'w', encoding="utf-8") as out:
        json.dump(data, out, indent=4, default=json_util.default)


def csv_dump(data: List[Dict], filename: str, header: List[str] = None) -> None:
    '''Dumps list to CSV file.

    Args:
        data (Dict): Data dictionary.
        filename (str): Path and name of output CSV file.
    '''
    try:
        with open(filename, 'w', encoding="utf-8", newline='') as output:
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()
            writer.writerows(data)

        logging.debug("Successfully saved data to %s", filename)
    except Exception as error:
        logging.exception("Failed saving data to %s: %s", filename, error)
        raise error


def load_json(json_path: str) -> dict:
    '''Loads JSON and returns dictionary.

    Args:
        json_path (str): Path and name of input JSON file.

    Returns:
        dict: Dictionary containing the JSON file data.
    '''
    with open(json_path, encoding="utf-8") as json_file:
        data = json.load(json_file)

    return data


def load_csv(csv_path) -> List:
    '''Loads CSV and returns a list.

    Args:
        csv_path (str): Path and name of input CSV file.

    Returns:
        list: List containing the CSV file data.
    '''
    data_list = []

    with open(csv_path, 'r', encoding="utf-8") as input_file:
        data = csv.DictReader(input_file)

        for row in data:
            data_list.append(dict(row))

    return data_list


def load_jinjasql(jinja_path) -> str:
    '''Loads JinjaSQL file and returns a string.

    Args:
        jinja_path (str): Path and name of input Jinja file.

    Returns:
        string: String containing the JinjaSQL file data.
    '''
    template: str

    with open(jinja_path, 'r', encoding="utf-8") as input_file:
        template = input_file.read()

    return template


def ls_dir(path: str, extension: str = "csv") -> List:
    '''Returns a list of files of given extension in a given directory.

    Args:
        path (str): Directory path.
        extension (str, optional): File extension. Defaults to "csv".

    Raises:
        err: If glog.glob failes.

    Returns:
        List: glob.glob list of files in the directory matching extension.
    '''
    try:
        return glob.glob(os.path.join(path, f"*.{extension}"))
    except Exception as err:
        raise err


def split_path(file_path: str) -> Tuple[str, str]:
    '''Splits a path into the base and filename.

    Args:
        file_path (str): Full file path to be split.

    Returns:
        Tuple[str, str]: Base path and filename.
    '''
    path = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    return path, filename


def fill_blanks(counts: List[Dict], min_date: str = None, max_date: str = None) -> List[Dict]:
    '''Takes a list of counts per month and fills in
       missing months with counts of 0 for plotting.

    Args:
        counts (List[Dict]): List of count dicts.

    Returns:
        List[Dict]: [{"date": <DATE>,
                      "imageCount": <COUNT>,
                      "seriesCount": <COUNT>,
                      "studyCount": <COUNT>
                    }]
    '''
    counts = [count for count in counts if count["date"] and count["date"] != "1/1"]
    count_dates = [datetime.strptime(count["date"], "%Y/%m") for count in counts]

    if min_date is None:
        min_date = min(count_dates)
    else:
        min_date = datetime.strptime(min_date, "%Y/%m")

    if max_date is None:
        max_date = max(count_dates)
    else:
        max_date = datetime.strptime(max_date, "%Y/%m")

    all_dates = []

    for date in range(int((max_date - min_date).days) + 1):
        all_dates.append((min_date + timedelta(date)).strftime("%Y/%m"))

    all_dates = sorted(list(set(all_dates)))
    count_date_str = sorted(list(set([date.strftime("%Y/%m") for date in count_dates])))
    missing_dates = [date for date in all_dates if date not in count_date_str]

    missing_metadata = []

    for date in missing_dates:
        metadata = {
            "date": date,
            "imageCount": 0,
            "seriesCount": 0,
            "studyCount": 0
        }

        missing_metadata.append(metadata)

    counts += missing_metadata
    counts = sorted(counts, key=lambda count: datetime.strptime(count["date"], "%Y/%m"))

    return counts
