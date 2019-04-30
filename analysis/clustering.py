import click
import pandas as pd
import numpy as np
import hdbscan
import folium
import webbrowser
import os

from loguru import logger
from yaspin import yaspin
from tqdm import tqdm
from time import time
from shapely.geometry import MultiPoint, mapping

CURRENT_DIR = os.getcwd()


@click.command()
@click.argument("sightings_file", type=click.File("r"))
@click.option("--min-cluster-size", type=int, default=5)
@click.option("--min-samples", type=int, default=None)
@click.option("--alpha", type=float, default=1.0)
@click.option(
    "--output-file",
    type=str,
    default="data/visualizations/sighting_cluster_map.html",
)
def main(sightings_file, min_cluster_size, min_samples, alpha, output_file):
    sightings = pd.read_csv(sightings_file).query("~latitude.isnull()")
    clusterer = hdbscan.HDBSCAN(metric="haversine")
    logger.info("Performing clustering.")
    start = time()
    with yaspin(text="👣 Building clusters 👣", color="cyan"):
        clusterer.fit(
            sightings[["latitude", "longitude"]].values * (np.pi / 180)
        )
    logger.info(
        f"Found {clusterer.labels_.max()} clusters in {time() - start:.3f}s."
    )
    sightings.loc[:, "cluster_label"] = clusterer.labels_

    logger.info("Drawing cluster polygons.")
    start = time()
    cluster_polygons = []
    for label, cluster_frame in tqdm(
        sightings.query("cluster_label != -1").groupby("cluster_label"),
        total=clusterer.labels_.max(),
    ):
        cluster_points = MultiPoint(
            cluster_frame[["longitude", "latitude"]].values
        )
        cluster_polygons.append(cluster_points.convex_hull)
    logger.info(f"Cluster polygons drawn in {time() - start:.3f}s.")

    # Now draw the map.
    logger.info("Drawing the map.")
    map_center = [sightings["latitude"].mean(), sightings["longitude"].mean()]
    sighting_cluster_map = folium.Map(
        location=map_center, zoom_start=5, tiles="cartodbpositron"
    )

    for _, row in sightings.iterrows():
        folium.CircleMarker(
            [row.latitude, row.longitude], radius=1, opacity=0.75
        ).add_to(sighting_cluster_map)

    cluster_polygon_geojson = {"type": "FeatureCollection", "features": []}
    for polygon in cluster_polygons:
        cluster_polygon_geojson["features"].append(
            {"type": "Feature", "properties": {}, "geometry": mapping(polygon)}
        )

    folium.GeoJson(cluster_polygon_geojson).add_to(sighting_cluster_map)
    sighting_cluster_map.save(output_file)
    webbrowser.open(f"file://{CURRENT_DIR}/{output_file}")


if __name__ == "__main__":
    main()
