import geopandas as gpd
import click
import json

from shapely.geometry import mapping


NON_CONUS = {"VI", "AK", "HI", "PR", "GU", "MP", "AS"}


@click.command()
@click.argument("shapefile", type=str)
@click.option("--output-file", type=click.File("w"), default="data/us.geojson")
def main(shapefile, output_file):
    us_states = gpd.read_file(shapefile).query("STUSPS not in @NON_CONUS")

    polygon = us_states.geometry.cascaded_union

    json.dump(mapping(polygon), output_file)


if __name__ == "__main__":
    main()
