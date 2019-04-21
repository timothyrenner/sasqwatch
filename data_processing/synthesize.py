import click
import random
import pandas as pd
import csv

from datetime import datetime, timedelta
from h3 import h3
from tqdm import tqdm


def random_date(min_date, max_date):
    total_days = (max_date - min_date).days
    days_forward = random.randint(0, total_days)

    return (min_date + timedelta(days=days_forward)).date()


def random_location(candidate_hex_addresses, resolution):
    root_hex = random.choice(candidate_hex_addresses)
    root_resolution = h3.h3_get_resolution(root_hex)

    current_resolution = root_resolution
    current_cell = root_hex

    while current_resolution < resolution:
        # Step up one resolution.
        current_resolution += 1
        # Get all the children of the current cell.
        children = h3.h3_to_children(current_cell, current_resolution)
        # Draw a random child and set it to the current cell.
        current_cell = random.choice(list(children))

    return h3.h3_to_geo(current_cell)


@click.command()
@click.option("--num-samples", type=int, default=5000)
@click.option("--min-date", type=str, default="1990-01-01")
@click.option(
    "--max-date",
    type=str,
    default=datetime.today().date().strftime("%Y-%m-%d"),
)
@click.option(
    "--hexagon-file", type=click.File("r"), default="data/us_hexagons.csv"
)
@click.option("--location-resolution", type=int, default=11)
@click.option(
    "--output-file",
    "-o",
    type=click.File("w"),
    default="data/synthesized_sightings.csv",
)
def main(
    num_samples,
    min_date,
    max_date,
    hexagon_file,
    location_resolution,
    output_file,
):
    min_date_obj = datetime.strptime(min_date, "%Y-%m-%d")
    max_date_obj = datetime.strptime(max_date, "%Y-%m-%d")
    hexagons = pd.read_csv(hexagon_file)
    writer = csv.DictWriter(
        output_file, fieldnames=["date", "latitude", "longitude"]
    )
    writer.writeheader()
    for ii in tqdm(range(num_samples), total=num_samples):
        latitude, longitude = random_location(
            hexagons.hex_address, location_resolution
        )
        sample_date = random_date(min_date_obj, max_date_obj)
        writer.writerow(
            {
                "date": sample_date.strftime("%Y-%m-%d"),
                "latitude": latitude,
                "longitude": longitude,
            }
        )


if __name__ == "__main__":
    main()
