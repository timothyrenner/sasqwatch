import dash
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import os
import json

from dotenv import load_dotenv, find_dotenv
from palettable.colorbrewer.sequential import YlOrRd_9 as colors
from math import ceil
from datetime import datetime
from dash.dependencies import Input, Output

load_dotenv(find_dotenv())


def make_layer(json_edge, color):
    return {
        "sourcetype": "geojson",
        "source": {"type": "Polygon", "coordinates": [json.loads(json_edge)]},
        "color": color,
        "below": "water",
        "opacity": 0.75,
        "type": "fill",
    }


def squatchcast_map(squatchcast_data):
    """ Builds the data structure required for a map of the squatchcast.
    """
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
            }
        ],
        "layout": {
            "mapbox": {
                "accesstoken": os.getenv("MAPBOX_KEY"),
                "layers": squatchcast_data.layer.tolist(),
                "center": {
                    "lat": squatchcast_data.latitude.mean(),
                    "lon": squatchcast_data.longitude.mean(),
                },
                "zoom": 3,
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


app = dash.Dash(
    "squatchcast",
    external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"],
)
# TODO: Heroku deployment stuff.

app.title = "SquatchCast"

data = pd.read_csv("squatchcast.csv").assign(
    color=lambda frame: frame.squatchcast.apply(
        lambda x: colors.hex_colors[(ceil(x * 10) - 1) if x > 0 else 0]
    ),
    layer=lambda frame: frame.apply(
        lambda x: make_layer(x.hex_geojson, x.color), axis=1
    ),
    text=lambda frame: frame.squatchcast.apply(
        lambda x: f"Squatchcast: {x:.3f}"
    ),
)

dates = {ii: d for ii, d in enumerate(sorted(data.date.unique()))}
date_marks = {
    ii: datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d")
    for ii, d in dates.items()
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
        ),
        dcc.Graph(
            id="squatchcast-hist",
            style={"gridRow": "11/15", "gridColumn": "1/3"},
        ),
    ],
    style={
        "display": "grid",
        "gridTemplateRows": "repeat(15, minmax(100px, 1fr))",
        "gridTemplateColumns": "repeat(5, minmax(250px, 1fr))",
    },
)

###############################################################################
# CALLBACKS
###############################################################################


@app.callback(
    Output("squatchcast-map", "figure"), [Input("day-slider", "value")]
)
def update_map(day):
    date = dates[day]  # noqa
    return squatchcast_map(data.query(f"date==@date"))


@app.callback(
    Output("squatchcast-hist", "figure"), [Input("day-slider", "value")]
)
def update_score_hist(day):
    date = dates[day]  # noqa
    return squatchcast_score_distribution(
        data.query("date==@date"), date_marks[day]
    )


if __name__ == "__main__":
    app.run_server()
