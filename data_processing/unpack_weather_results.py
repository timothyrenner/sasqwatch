import click
import json
import csv

from toolz import get, second, compose, get_in

listmap = compose(list, map)


WEATHER_FIELDS = [
    ("temperatureHigh", "temperature_high"),
    ("temperatureLow", "temperature_low"),
    ("dewPoint", "dew_point"),
    ("humidity", "humidity"),
    ("cloudCover", "cloud_cover"),
    ("moonPhase", "moon_phase"),
    ("precipIntensity", "precip_intensity"),
    ("precipProbability", "precip_probability"),
    ("precipType", "precip_type"),
    ("pressure", "pressure"),
    ("uvIndex", "uv_index"),
    ("visibility", "visibility"),
    ("windBearing", "wind_bearing"),
    ("windSpeed", "wind_speed"),
]


@click.command()
@click.option("--input-file", type=click.File("r"), default="-")
@click.option("--output-file", type=click.File("w"), default="-")
def main(input_file, output_file):
    reader = csv.reader(input_file)
    writer = csv.DictWriter(
        output_file,
        fieldnames=["date", "latitude", "longitude"]
        + listmap(second, WEATHER_FIELDS),
    )
    writer.writeheader()

    for row in reader:
        date, latitude, longitude, _, payload = row
        weather = get_in(["daily", "data", 0], json.loads(payload), {})
        writer.writerow(
            {
                "date": date,
                "latitude": latitude,
                "longitude": longitude,
                **{
                    field_name: get(field, weather, None)
                    for field, field_name in WEATHER_FIELDS
                },
            }
        )


if __name__ == "__main__":
    main()
