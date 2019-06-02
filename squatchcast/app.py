import dash
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import numpy as np
import os
import json

from dotenv import load_dotenv, find_dotenv
from palettable.colorbrewer.sequential import YlOrRd_9 as colors
from math import floor
from datetime import datetime
from dash.dependencies import Input, Output
from toolz import get_in

load_dotenv(find_dotenv())


def make_layers(data):
    layers = []
    # We want one layer per color group.
    for color, group in data.groupby("color"):
        # Each layer is a multipolygon of all hexagons with the same color.
        geojson = {"type": "MultiPolygon", "coordinates": []}
        for _, row in group.iterrows():
            geojson["coordinates"].append([json.loads(row.hex_geojson)])
        layers.append(
            {
                "sourcetype": "geojson",
                "source": geojson,
                "color": color,
                "below": "water",
                "opacity": 0.5,
                "type": "fill",
            }
        )
    return layers


def squatchcast_map(squatchcast_data, layers):
    """ Builds the data structure required for a map of the squatchcast.
    """
    # TODO: This resets the zoom level and center of the map.
    # TODO: Let's not do that.
    return {
        "data": [
            {
                "type": "scattermapbox",
                "lat": squatchcast_data.latitude.tolist(),
                "lon": squatchcast_data.longitude.tolist(),
                "text": squatchcast_data.text.tolist(),
                "mode": "markers",
                "marker": {
                    "size": 1,
                    "color": squatchcast_data.color.tolist(),
                },
                "hoverinfo": "text",
                "customdata": squatchcast_data[
                    [
                        "temperature_high",
                        "squatchcast",
                        "precip_type",
                        "historical_sightings",
                    ]
                ].to_dict(orient="records"),
            }
        ],
        "layout": {
            "mapbox": {
                "accesstoken": os.getenv("MAPBOX_KEY"),
                "layers": layers,
                "center": {
                    "lat": squatchcast_data.latitude.mean(),
                    "lon": squatchcast_data.longitude.mean(),
                },
                "zoom": 3,
                "style": "mapbox://styles/mapbox/light-v9",
            }
        },
    }


def squatchcast_score_distribution(squatchcast_data, date):
    """ Builds the histogram for the squatchast scores.
    """
    return {
        "data": [
            {"type": "histogram", "x": squatchcast_data.squatchcast.tolist()}
        ],
        "layout": {
            "title": f"Squatchcast Scores: {date}",
            "xaxis": {"title": "Squatchcast Score"},
            "bargap": 0.05,
        },
    }


def squatchcast_temp_distribution(squatchcast_data, date):
    """ Builds the histogram for the squatchcast temperatures.
    """
    return {
        "data": [
            {
                "type": "histogram",
                "x": squatchcast_data.temperature_high.tolist(),
            }
        ],
        "layout": {
            "title": f"High Temperatures: {date}",
            "xaxis": {"title": "High Temperature"},
            "bargap": 0.05,
        },
    }


def squatchcast_precip(squatchcast_data, date):
    """ Builds the bar chart for the squatchcast precipitation types.
    """
    grouped_data = squatchcast_data.groupby("precip_type").agg(
        {"precip_type": "count"}
    )
    return {
        "data": [
            {
                "type": "bar",
                "x": grouped_data.index.tolist(),
                "y": grouped_data.precip_type.tolist(),
            }
        ],
        "layout": {
            "title": f"Precip Type: {date}",
            "xaxis": {"title": "Precipitation Type"},
            "yaxis": {"title": "Number of Locations"},
        },
    }


app = dash.Dash(
    "squatchcast",
    external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"],
)
# TODO: Heroku deployment stuff.

app.title = "SquatchCast"

data = pd.read_csv("squatchcast.csv").assign(
    color=lambda frame: frame.squatchcast.apply(
        lambda x: colors.hex_colors[
            (floor(x * 10) - 1) if floor(x * 10) > 0 else 0
        ]
    ),
    text=lambda frame: frame.squatchcast.apply(
        lambda x: f"Squatchcast: {x:.3f}"
    ),
    precip_type=lambda frame: np.where(
        frame.precip_probability < 0.4, "no_precipitation", frame.precip_type
    ),
)

dates = {ii: d for ii, d in enumerate(sorted(data.date.unique()))}
date_marks = {
    ii: datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d")
    for ii, d in dates.items()
}
layers = {
    ii: make_layers(data.query(f"date=='{dates[ii]}'")) for ii in dates.keys()
}

###############################################################################
# LAYOUT
###############################################################################

app.layout = html.Div(
    children=[
        html.H1(
            "SquatchCast",
            style={
                "textAlign": "center",
                "gridColumn": "3/4",
                "gridRow": "1/2",
            },
        ),
        html.Div(
            children=[
                dcc.Slider(
                    id="day-slider",
                    min=0,
                    max=len(date_marks) - 1,
                    value=0,
                    marks=date_marks,
                    included=False,
                )
            ],
            style={
                "gridRow": "2/3",
                "gridColumn": "1/6",
                "padding-left": "25px",
                "padding-right": "25px",
            },
        ),
        dcc.Graph(
            id="squatchcast-map",
            style={"gridRow": "3/11", "gridColumn": "1/5"},
            config={"displayModeBar": False},
        ),
        dcc.Graph(
            id="squatchcast-hist",
            style={"gridRow": "11/15", "gridColumn": "1/3"},
            config={"displayModeBar": False},
        ),
        dcc.Graph(
            id="temperature-hist",
            style={"gridRow": "11/15", "gridColumn": "3/5"},
            config={"displayModeBar": False},
        ),
        dcc.Graph(
            id="precip-bar",
            style={"gridRow": "11/15", "gridColumn": "5/6"},
            config={"displayModeBar": False},
        ),
        html.Div(
            children=[
                html.H2("", id="weather", style={"textAlign": "center"}),
                html.H3("Weather", style={"textAlign": "center"}),
            ],
            style={"gridRow": "4/6", "gridColumn": "5/6"},
        ),
        html.Div(
            children=[
                html.H2(
                    "",
                    id="historical-sightings",
                    style={"textAlign": "center"},
                ),
                html.H3("Historical Sightings", style={"textAlign": "center"}),
            ],
            style={"gridRow": "6/8", "gridColumn": "5/6"},
        ),
        html.Div(
            children=[
                html.H2(
                    "", id="squatchcast-score", style={"textAlign": "center"}
                ),
                html.H3("Squatchcast Score", style={"textAlign": "center"}),
            ],
            style={"gridRow": "8/10", "gridColumn": "5/6"},
        ),
    ],
    style={
        "display": "grid",
        "gridTemplateRows": "repeat(15, minmax(100px, 1fr))",
        "gridTemplateColumns": "repeat(5, minmax(250px, 1fr))",
    },
)

# TODO: Footer, including dark sky attribution.

###############################################################################
# CALLBACKS
###############################################################################


@app.callback(
    Output("squatchcast-map", "figure"), [Input("day-slider", "value")]
)
def update_map(day):
    date = dates[day]  # noqa
    return squatchcast_map(data.query(f"date==@date"), layers[day])


@app.callback(
    Output("squatchcast-hist", "figure"), [Input("day-slider", "value")]
)
def update_score_hist(day):
    date = dates[day]  # noqa
    return squatchcast_score_distribution(
        data.query("date==@date"), date_marks[day]
    )


@app.callback(
    Output("temperature-hist", "figure"), [Input("day-slider", "value")]
)
def update_temperature_hist(day):
    date = dates[day]  # noqa
    return squatchcast_temp_distribution(
        data.query("date==@date"), date_marks[day]
    )


@app.callback(Output("precip-bar", "figure"), [Input("day-slider", "value")])
def update_precip_bar(day):
    date = dates[day]  # noqa
    return squatchcast_precip(data.query("date==@date"), date_marks[day])


@app.callback(
    Output("weather", "children"), [Input("squatchcast-map", "hoverData")]
)
def update_high_temperature(map_hover_data):
    if map_hover_data:
        high_temp = get_in(
            ["points", 0, "customdata", "temperature_high"], map_hover_data, ""
        )
        precipitation = get_in(
            ["points", 0, "customdata", "precip_type"], map_hover_data, ""
        )
        if (not precipitation) or (precipitation == "no_precipitation"):
            precipitation = "clear"
        return f"{int(high_temp)}\xb0F, {precipitation}"
    else:
        return "\n"


@app.callback(
    Output("historical-sightings", "children"),
    [Input("squatchcast-map", "hoverData")],
)
def update_historical_sightings(map_hover_data):
    if map_hover_data:
        historical_sightings = get_in(
            ["points", 0, "customdata", "historical_sightings"],
            map_hover_data,
            "",
        )
        return historical_sightings
    else:
        return "\n"


@app.callback(
    Output("squatchcast-score", "children"),
    [Input("squatchcast-map", "hoverData")],
)
def update_squatchcast_score(map_hover_data):
    if map_hover_data:
        score = get_in(
            ["points", 0, "customdata", "squatchcast"], map_hover_data
        )
        return f"{score:.3f}"
    else:
        return "\n"


if __name__ == "__main__":
    app.run_server()
