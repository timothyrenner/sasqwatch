import click
import pandas as pd


RAW_FEATURES = [
    "date",
    "latitude",
    "longitude",
    "temperature_high",
    "temperature_low",
    "dew_point",
    "humidity",
    "cloud_cover",
    "moon_phase",
    "precip_intensity",
    "precip_probability",
    "precip_type",
    "pressure",
    "uv_index",
    "visibility",
    "wind_bearing",
    "wind_speed",
]


@click.command()
@click.argument("sightings", type=click.File("r"))
@click.argument("not_sightings", type=click.File("r"))
@click.option(
    "--output-file", "-o", type=click.File("w"), default="raw_training_set.csv"
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
        [sightings_df[RAW_FEATURES], not_sightings_df[RAW_FEATURES]]
    ).to_csv(output_file, index=False)


if __name__ == "__main__":
    main()
