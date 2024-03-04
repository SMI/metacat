'''Takes in a tag labelling CSV file, groups tag values
   by their frequency and plots them.

   x axis: frequency buckets
   y axis: % of descriptions 
'''
import os
import argparse
import logging
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.transform import dodge
from bokeh.io import output_file, save
import modules.file_lib as flib


def argparser() -> argparse.Namespace:
    '''Terminal argument parser function.

    Returns:
        argparse.Namespace: Terminal arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms", "-t",
                        help="Path to terms CSV file.", type=str,
                        required=True)
    parser.add_argument("--counts", "-c",
                        help="Name of counts column.", type=str, required=True)
    parser.add_argument("--by", "-b",
                        help="Counts by series/studies. Default to 'studies'.",
                        type=str, required=False, nargs="+",
                        choices=["series", "studies"], default=["studies"])
    parser.add_argument("--output", "-o",
                        help=("Output directory path. "
                              "Default to current directory."),
                        type=str, required=False, default=".")
    parser.add_argument("--log", "-l", help=("Log directory path. "
                        "Default to current directory."),
                        type=str, required=False, default=".")

    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    '''Main function.

    Args:
        args (argparse.Namespace): Carries terminal arguments from argparse().
    '''
    term_file = args.terms
    counts_col = args.counts
    counts_by = args.by[0]
    output = args.output
    log_path = args.log

    filename = os.path.splitext(os.path.basename(term_file))[0]
    log = flib.setup_logging(log_path, f"{filename}_plot", "debug")
    logging.getLogger(log)

    terms = flib.load_csv(term_file)

    total = 0
    buckets = {
        "1": {"count": 0, "total": 0},
        "2-50": {"count": 0, "total": 0},
        "51-100": {"count": 0, "total": 0},
        "101-500": {"count": 0, "total": 0},
        "501-10000": {"count": 0, "total": 0},
        "10001-50000": {"count": 0, "total": 0},
        "50001-100000": {"count": 0, "total": 0},
        "100001-500000": {"count": 0, "total": 0},
        ">500000": {"count": 0, "total": 0}
    }

    for term in terms:
        term_freq = int(term[counts_col])
        total += term_freq

        if term_freq == 1:
            buckets["1"]["count"] += 1
            buckets["1"]["total"] += term_freq
        elif term_freq <= 50:
            buckets["2-50"]["count"] += 1
            buckets["2-50"]["total"] += term_freq
        elif term_freq <= 100:
            buckets["51-100"]["count"] += 1
            buckets["51-100"]["total"] += term_freq
        elif term_freq <= 500:
            buckets["101-500"]["count"] += 1
            buckets["101-500"]["total"] += term_freq
        elif term_freq <= 10000:
            buckets["501-10000"]["count"] += 1
            buckets["501-10000"]["total"] += term_freq
        elif term_freq <= 50000:
            buckets["10001-50000"]["count"] += 1
            buckets["10001-50000"]["total"] += term_freq
        elif term_freq <= 100000:
            buckets["50001-100000"]["count"] += 1
            buckets["50001-100000"]["total"] += term_freq
        elif term_freq <= 500000:
            buckets["100001-500000"]["count"] += 1
            buckets["100001-500000"]["total"] += term_freq
        else:
            buckets[">500000"]["count"] += 1
            buckets[">500000"]["total"] += term_freq

    x_axis = list(buckets.keys())
    y_axis1 = []
    y_axis2 = []

    for counts in buckets.values():
        y_axis1.append("{:.2f}".format((counts["count"] * 100) / len(terms)))
        y_axis2.append("{:.2f}".format((counts["total"] * 100) / total))

    data = {
        "buckets": x_axis,
        "unique_counts": y_axis1,
        "total_counts": y_axis2
    }

    logging.info("Unique counts: %s", len(terms))
    logging.info("Total counts: %s", total)

    source = ColumnDataSource(data=data)
    split_filename = filename.split('_')
    title = f"{split_filename[1].capitalize()} {split_filename[0]} unique value frequency"

    chart = figure(x_range=x_axis, height=500, title=title,
                   toolbar_location=None, tools="")
    chart.vbar(x=dodge("buckets", -0.25, range=chart.x_range),
               top="unique_counts", source=source, width=0.2, color="#72CFB3",
               legend_label="% of unique values")
    chart.vbar(x=dodge("buckets", 0.0, range=chart.x_range), top="total_counts",
               source=source, width=0.2, color="#E59866",
               legend_label=f"% of total {counts_by}")

    chart.width = 800
    chart.x_range.range_padding = 0.1
    chart.xgrid.grid_line_color = None
    chart.xaxis.axis_label = f"Number of {counts_by} per unique value"
    chart.legend.location = "top_center"
    chart.legend.orientation = "horizontal"

    output_file(os.path.join(output, f"{filename}.html"), mode="inline")
    save(chart)


if __name__ == '__main__':
    commands = argparser()
    main(commands)
