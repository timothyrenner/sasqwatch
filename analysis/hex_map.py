import click
import json
import pandas as pd
import folium
import branca

from h3 import h3
from shapely.geometry import mapping, shape


@click.command()
@click.argument("data_file", type=click.File("r"))
@click.option(
    "--polygon-file", type=click.File("r"), default="data/us.geojson"
)
@click.option("--resolution", type=int, default=4)
@click.option("--output-file", type=str, default="sasquatch_hex.html")
def main(data_file, polygon_file, resolution, output_file):
    data = pd.read_csv(data_file).query("~latitude.isnull()")
    # Index the data by h3. Not the most efficient way to do it but it's fast
    # enough IMO.
    data.loc[:, "h3_index"] = [
        h3.geo_to_h3(row.latitude, row.longitude, resolution)
        for _, row in data.iterrows()
    ]

    # Read in the US states polygons.
    us_states = shape(json.load(polygon_file))
    state_hexes = set()

    # Polyfill each state and add it to the big list of h3 indexes.
    for geometry in us_states:
        state_hexes |= h3.polyfill(
            mapping(geometry), resolution, geo_json_conformant=True
        )

    all_hexes = state_hexes | set(data.h3_index)
    # Now reindex the counted sightings by hex address and fill the empties
    # with zeros.
    grouped_sightings = (
        data.groupby("h3_index")
        .agg({"number": "count"})
        .reindex(list(all_hexes), fill_value=0)
    )

    geo_json = {"type": "FeatureCollection", "features": []}

    for h3_address, row in grouped_sightings.iterrows():
        hexagon = h3.h3_to_geo_boundary(h3_address, geo_json=True)
        geo_json["features"].append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [hexagon]},
                "properties": {
                    "hex_address": h3_address,
                    "count": int(row.number),
                },
            }
        )

    # Now it's map time.
    map_center = [data["latitude"].mean(), data["longitude"].mean()]
    colormap = branca.colormap.linear.YlOrRd_09.scale(
        grouped_sightings.number.min(), grouped_sightings.number.max()
    )
    m = folium.Map(location=map_center, zoom_start=5, tiles="cartodbpositron")

    folium.GeoJson(
        geo_json,
        tooltip=folium.GeoJsonTooltip(["hex_address", "count"]),
        style_function=lambda x: {
            "fillColor": colormap(x["properties"]["count"]),
            "color": "gray",
            "weight": 0.1,
            "fillOpacity": 0.5,
        },
    ).add_to(m)
    colormap.add_to(m)
    m.save(output_file)


if __name__ == "__main__":
    main()
