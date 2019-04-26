import click
import json
import pandas as pd
import csv

from h3 import h3
from shapely.geometry import shape, mapping
from tqdm import tqdm
from loguru import logger


@click.command()
@click.argument("polygon_file", type=click.File("r"))
@click.argument("data_file", type=click.File("r"))
@click.option("--resolution", type=int, default=5)
@click.option(
    "--output-file", type=click.File("w"), default="data/us_hexagons.csv"
)
def main(polygon_file, data_file, resolution, output_file):
    logger.info("Reading 👣 sightings.")
    data = pd.read_csv(data_file).query("~latitude.isnull()")
    data.loc[:, "h3_index"] = [
        h3.geo_to_h3(row.latitude, row.longitude, resolution)
        for _, row in data.iterrows()
    ]

    logger.info("Reading US polygon.")
    us_states = shape(json.load(polygon_file))
    us_hexes = set(data.h3_index)

    logger.info("Polyfilling the USA.")
    for geometry in tqdm(us_states, total=len(us_states)):
        us_hexes |= h3.polyfill(
            mapping(geometry), resolution, geo_json_conformant=True
        )
    logger.info(f"Writing to {output_file.name}.")
    writer = csv.DictWriter(
        output_file, fieldnames=["hex_address", "hex_geojson"]
    )
    writer.writeheader()
    for us_hex in tqdm(us_hexes, total=len(us_hexes)):
        writer.writerow(
            {
                "hex_address": us_hex,
                "hex_geojson": json.dumps(
                    h3.h3_to_geo_boundary(us_hex, geo_json=True)
                ),
            }
        )


if __name__ == "__main__":
    main()
