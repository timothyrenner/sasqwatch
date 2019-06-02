import click
import os
import pandas as pd
import numpy as np
import requests
import sys

from dotenv import load_dotenv, find_dotenv
from loguru import logger
from h3 import h3
from tqdm import tqdm
from toolz import get, get_in, curry
from datetime import datetime
from sklearn.externals.joblib import load
from yaspin import yaspin


load_dotenv(find_dotenv())
sys.path.append("./model")

from assemble import RAW_FEATURES  # noqa


DARK_SKY_KEY = os.getenv("DARK_SKY_KEY")

if not DARK_SKY_KEY:
    logger.error("No Dark Sky key was found. Double check .env file.")
    sys.exit(1)


def create_weather_request(lat, lon, key):
    return (
        "https://api.darksky.net/forecast/"
        f"{key}/{lat},{lon}?exclude=hourly,minutely"
    )


@click.command()
@click.option(
    "--us-hexagons", type=click.File("r"), default="data/raw/us_hexagons.csv"
)
@click.option(
    "--historical-sightings",
    type=click.File("r"),
    default="data/raw/bigfoot_sightings.csv",
)
@click.option("--model-file", type=str, default="model/model.pkl")
@click.option("--debug", is_flag=True, default=False)
@click.option("--output-file", type=click.File("w"), default="squatchcast.csv")
def main(us_hexagons, historical_sightings, model_file, debug, output_file):

    logger.info(f"Reading hexagons from {us_hexagons.name}.")
    squatchcast_locations = pd.read_csv(us_hexagons)
    logger.info(f"Read {squatchcast_locations.shape[0]} hexagons.")

    logger.info(
        f"Reading historical sightings from {historical_sightings.name}."
    )
    historical_sightings_frame = pd.read_csv(historical_sightings).query(
        "~latitude.isnull()"
    )
    logger.info(
        f"Read {historical_sightings_frame.shape[0]} historical_sightings."
    )

    if debug:
        logger.warning("Debug selected, pulling top five records.")
        squatchcast_locations = squatchcast_locations.head()

    num_locations = squatchcast_locations.shape[0]
    lats = []
    lons = []
    logger.info("Extracting hexagon lat / lon values.")
    for _, row in tqdm(squatchcast_locations.iterrows(), total=num_locations):
        lat, lon = h3.h3_to_geo(row.hex_address)
        lats.append(lat)
        lons.append(lon)

    squatchcast_locations.loc[:, "latitude"] = lats
    squatchcast_locations.loc[:, "longitude"] = lons

    session = requests.Session()
    logger.info(f"Retrieving the weather for {num_locations} " "locations.")
    weather_conditions = []
    failed = 0
    for _, row in tqdm(squatchcast_locations.iterrows(), total=num_locations):
        request = create_weather_request(
            row.latitude, row.longitude, DARK_SKY_KEY
        )
        try:
            weather_response = session.get(request)
            # Make sure the response worked.
            weather_response.raise_for_status()
            # Now parse the json.
            weather_conditions.append(weather_response.json())
        except requests.HTTPError:
            failed += 1
    logger.info(f"{failed} requests to Dark Sky failed.")

    # Extract the features a list of dicts. Plan is to turn that into a
    # data frame and concatenate them to the squatchcast_locations.
    logger.info("Unpacking weather results.")
    squatchcast_features = []
    for weather in tqdm(weather_conditions, total=num_locations):
        # Append the current features.
        daily = get_in(["daily", "data"], weather, [])
        latitude = get("latitude", weather, np.nan)
        longitude = get("longitude", weather, np.nan)
        for conditions in daily:
            get_condition = curry(get)(seq=conditions, default=np.nan)
            squatchcast_features.append(
                {
                    "date": datetime.utcfromtimestamp(
                        get_condition("time")
                    ).strftime("%Y-%m-%d"),
                    "latitude": latitude,
                    "longitude": longitude,
                    "precip_type": get(
                        "precipType", conditions, "no_precipitation"
                    ),
                    "temperature_high": get_condition("temperatureHigh"),
                    "temperature_low": get_condition("temperatureLow"),
                    "dew_point": get_condition("dewPoint"),
                    "humidity": get_condition("humidity"),
                    "cloud_cover": get_condition("cloudCover"),
                    "moon_phase": get_condition("moonPhase"),
                    "precip_intensity": get_condition("precipIntensity"),
                    "precip_probability": get_condition("precipProbability"),
                    "pressure": get_condition("pressure"),
                    "uv_index": get_condition("uvIndex"),
                    "visibility": get_condition("visibility"),
                    "wind_bearing": get_condition("windBearing"),
                    "wind_speed": get_condition("windSpeed"),
                }
            )

    squatchcast_frame = pd.DataFrame.from_records(squatchcast_features)
    logger.info(f"Loading model from {model_file}.")
    model = load(model_file)
    logger.info(
        f"Getting predictions for {squatchcast_frame.shape[0]} locations."
    )
    with yaspin(text="👣 Calculating squatchcast. 👣", color="cyan"):
        squatchcast_frame.loc[:, "squatchcast"] = model.predict_proba(
            squatchcast_frame[RAW_FEATURES]
        )[:, 1]
    # Get the resoluton the US hexagon file is at and index the squatchcast
    # results by that resolution.
    us_resolution = h3.h3_get_resolution(
        squatchcast_locations.head(1).hex_address[0]
    )

    squatchcast_frame.loc[:, "hex_address"] = np.apply_along_axis(
        lambda x: h3.geo_to_h3(x[0], x[1], us_resolution),
        axis=1,
        arr=squatchcast_frame[["latitude", "longitude"]].values,
    )

    historical_sightings_frame.loc[:, "hex_address"] = np.apply_along_axis(
        lambda x: h3.geo_to_h3(x[0], x[1], us_resolution),
        axis=1,
        arr=historical_sightings_frame[["latitude", "longitude"]].values,
    )

    historical_sightings_agg = (
        historical_sightings_frame.groupby("hex_address")
        .agg({"number": "count"})
        .reset_index()
    )

    # Now we need, for each day, a complete hexagonification of the US. We'll
    # do this in a groupby and concatenate.
    visualization_frames = []
    for date, frame in squatchcast_frame.groupby("date"):
        # Merge weather and US hexagons.
        weather_location_merge = pd.merge(
            squatchcast_locations.drop(columns=["latitude", "longitude"]),
            frame,
            on="hex_address",
            how="left",
        )
        # Merge historical sightings.
        visualization_frames.append(
            pd.merge(
                weather_location_merge,
                historical_sightings_agg,
                on="hex_address",
                how="left",
            )
            .fillna(0)
            .astype({"number": "int"})
            .rename(columns={"number": "historical_sightings"})
        )

    pd.concat(visualization_frames).to_csv(output_file, index=False)


if __name__ == "__main__":
    main()
