'''Custom medical imaging metadata catalogue.
   Client-side processing decision based on: https://datatables.net/faqs/index#speed
'''
import logging
import argparse
import _modules.functionality as funct
import modules.file_lib as flib
from waitress import serve
from flask import Flask, render_template
from werkzeug.exceptions import abort
from flask_caching import Cache


app = Flask(__name__)
app.config.from_mapping({"CACHE_TYPE": "SimpleCache"})
cache = Cache(app)
log = flib.setup_logging("logs", "catalogue_ui", "debug")
logging.getLogger(log)


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", "-e",
                        help="Environment type: prod/dev",
                        required=False, choices=["prod", "dev"],
                        nargs="+", default="dev")
    parser.add_argument("--address", "-a",
                        help="Host address or name. Default to 0.0.0.0.",
                        type=str, required=False, default="0.0.0.0")
    parser.add_argument("--port", "-p",
                        help="Port number. Default to 5002",
                        type=int, required=False, default=5002)

    return parser.parse_args()


@app.route('/')
def index() -> str:
    '''Main page showing modalities summary.'''
    data = get_mods()

    return render_template("index.html",
                           modalities=data,
                           calculate_percentage=funct.calculate_percentage)


@cache.cached(timeout=500)
def get_mods():
    conn = funct.get_db_connection(log)
    modalities = list(conn.search("modalities", {}, {
        "modality": 1, "promotionStatus": 1, "promotionStatusDate": 1,
        "totalNoImagesRaw": 1, "totalNoImagesStaging": 1, "totalNoImagesLive": 1
    }))
    blocked_mods = list(conn.search("modality_blocklist"))
    conn.disconnect()

    modalities = funct.merge_lists(modalities, blocked_mods, "modality")

    return modalities


@app.route('/api/<modality>')
def modality(modality: str) -> str:
    '''Modality page showing modality details and graphs.

    Args:
        modality (str): Modality name.
    '''
    conn = funct.get_db_connection(log)
    mod_meta = conn.get_modality_meta(modality)
    tag_meta = conn.get_tag_meta(modality)

    if modality is None:
        abort(404)

    tag_meta = funct.merge_lists(mod_meta.pop("tags"), tag_meta, "tag")
    tag_stats = funct.tag_stats(tag_meta, modality=True)
    counts = funct.format_counts(mod_meta)
    conn.disconnect()

    return render_template("modality.html", modality=mod_meta,
                           tags=tag_stats, counts=counts)


@app.route('/api/<modality>/tags')
def modality_tags(modality: str) -> str:
    '''Modality-specific tags page.

    Args:
        modality (str): Modality name.
    '''
    data = get_tags(modality)

    return render_template("tags.html", modality=modality, tags=data)


@app.route('/api/all_tags')
def all_tags() -> str:
    '''Page showing all tags.'''
    data = get_tags("all")

    return render_template("tags.html", modality="All Tags", tags=data)


@cache.cached(timeout=500)
def get_tags(modality):
    conn = funct.get_db_connection(log)

    if modality != "all":
        mod_meta = list(conn.search("modalities",
                                    {"modality": modality},
                                    {"tags": 1}
        ))[0]["tags"]
        tag_meta = list(conn.search("tags",
                                    {"modalities": {"$in": [modality]},
                                    "promotionStatus": {"$ne": "blocked"}}
        ))

        tag_meta = funct.merge_lists(tag_meta, mod_meta, "tag")
    else:
        tag_meta = list(conn.search("tags", {"promotionStatus": {"$ne": "blocked"}}))

    conn.disconnect()

    tag_meta = funct.format_mods(tag_meta)
    data = sorted(tag_meta, key=lambda tag: tag["tag"])

    return data


@app.route('/api/labels')
def labels() -> str:
    '''Body part labelling page showing body part statistics.'''
    conn = funct.get_db_connection(log)
    label_meta = list(conn.search("bodyparts"))
    conn.disconnect()

    labels, data = funct.format_label_stats(label_meta[0]["stats"])

    return render_template("body.html", labels=labels, data=data, logs=label_meta)


@app.route('/api/report')
def report() -> str:
    '''Report page.'''
    tag_stats, monthly_counts = get_report()

    return render_template("report.html", tag_stats=tag_stats,
                           monthly_counts=monthly_counts)


@cache.cached(timeout=500)
def get_report():
    conn = funct.get_db_connection(log)
    modalities = list(conn.search("modalities", {}, {
        "modality": 1, "countsPerMonthRaw": 1, "countsPerMonthStaging": 1,
        "countsPerMonthLive": 1, "promotionStatus": 1
    }))
    tags = conn.get_tag_meta("all")

    tag_stats = funct.tag_stats(tags)
    monthly_counts = funct.monthly_counts(modalities, "Live")

    return tag_stats, monthly_counts


def main(args: argparse.Namespace) -> None:
    '''Main function for running app.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    env = args.env
    host = args.address
    port = args.port

    if env == "dev":
        app.run(host=host, port=port, debug=True)
    else:
        serve(app, listen=f"{host}:{port}")


if __name__ == '__main__':
    commands = argparser()
    main(commands)
