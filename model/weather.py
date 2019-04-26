import click
import os
import pandas as pd
import csv

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DARK_SKY_KEY = os.getenv("DARK_SKY_KEY")


def create_weather_request(lat, lon, time, key=None):
    return "https://api.darksky.net/forecast/{}/{},{},{}?exclude={}".format(
        key, lat, lon, time, "currently,hourly,minutely"
    )


@click.command()
@click.argument("data_file", type=click.File("r"))
@click.option("--output-file", "-o", type=click.File("w"), default="-")
def main(data_file, output_file):

    data = pd.read_csv(data_file).query("~latitude.isnull()")
    writer = csv.writer(output_file)
    for _, r in data[["date", "latitude", "longitude"]].iterrows():

        writer.writerow(
            [
                r.date,
                r.latitude,
                r.longitude,
                create_weather_request(
                    r.latitude,
                    r.longitude,
                    str(r.date) + "T00:00:00",
                    key=DARK_SKY_KEY,
                ),
            ]
        )


if __name__ == "__main__":
    main()
