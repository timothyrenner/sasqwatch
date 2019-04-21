import click
import folium
import pandas as pd


@click.command()
@click.argument("data_file", type=click.File("r"))
@click.option("--latitude-col", type=str, default="latitude")
@click.option("--longitude-col", type=str, default="longitude")
@click.option("--output-file", type=str, default="sasquatch_point.html")
def main(data_file, latitude, longitude, output_file):
    data = pd.read_csv(data_file).query("latitude.isnull()")
    map_center = [data["latitude"].mean(), data["longitude"].mean()]
    sasquatch_map = folium.Map(
        location=map_center, zoom_start=5, tiles="cartodbpositron"
    )

    for _, row in data.iterrows():
        folium.CircleMarker(
            [row.latitude, row.longitude],
            radius=1,
            opacity=0.75
        ).add_to(sasquatch_map)
    sasquatch_map.save(output_file)


if __name__ == "__main__":
    main()
