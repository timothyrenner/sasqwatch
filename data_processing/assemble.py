import click
import pandas as pd


RAW_FEATURES = [
    # These four features are transformed into new ones.
    "date",
    "latitude",
    "longitude",
    "precip_type",
    # These are passed through.
    "temperature_high",
    "temperature_low",
    "dew_point",
    "humidity",
    "cloud_cover",
    "moon_phase",
    "precip_intensity",
    "precip_probability",
    "pressure",
    "uv_index",
    "visibility",
    "wind_bearing",
    "wind_speed",
]

TARGET = "sighting"

ALL_COLUMNS = RAW_FEATURES + [TARGET]


@click.command()
@click.argument("sightings", type=click.File("r"))
@click.argument("not_sightings", type=click.File("r"))
@click.option(
    "--output-file",
    "-o",
    type=click.File("w"),
    default="data/processed/raw_training_data.csv",
)
def main(sightings, not_sightings, output_file):
    sightings_df = (
        pd.read_csv(sightings)
        .query("~latitude.isnull()")
        .assign(sighting=True)
    )
    not_sightings_df = (
        pd.read_csv(not_sightings)
        .query("~latitude.isnull()")
        .assign(sighting=False)
    )

    pd.concat(
        [sightings_df[ALL_COLUMNS], not_sightings_df[ALL_COLUMNS]]
    ).to_csv(output_file, index=False)


if __name__ == "__main__":
    main()
