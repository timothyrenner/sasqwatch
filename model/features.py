import click
import pandas as pd
import numpy as np

from sklearn.compose import make_column_transformer
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from h3 import h3

from assemble import RAW_FEATURES, TARGET


def featurize_time(frame, date_col="date"):
    frame.loc[:, date_col] = pd.to_datetime(frame[date_col])
    return frame.assign(
        month=frame[date_col].dt.month,
        # dayofmonth=frame[date_col].dt.day,
        # dayofyear=frame[date_col].dt.dayofyear,
    ).drop(columns=[date_col])


class GeospatialDiscretizer(BaseEstimator, TransformerMixin):
    def __init__(self, resolution):
        self.resolution = resolution
        self.hex_frame = pd.DataFrame()

    def fit(self, X, y):
        # X is a Nx2 lat/lon data frame.
        # y is boolean numpy array.
        self.hex_frame = (
            pd.DataFrame(
                {
                    "latitude": X[y]["latitude"],
                    "longitude": X[y]["longitude"],
                    "h3": np.apply_along_axis(
                        lambda x: h3.geo_to_h3(x[0], x[1], self.resolution),
                        axis=1,
                        arr=X[y],
                    ),
                }
            )
            .groupby("h3")
            .agg({"h3": "count"})
        )
        return self

    def transform(self, X):
        h3_X = np.apply_along_axis(
            lambda x: h3.geo_to_h3(x[0], x[1], self.resolution), axis=1, arr=X
        )

        return self.hex_frame.reindex(h3_X, fill_value=0)


def feature_pipeline(resolution):
    column_transformer = make_column_transformer(
        # Featurize the dates and drop the date column.
        (FunctionTransformer(featurize_time, validate=False), ["date"]),
        # Featurize the geography.
        (
            GeospatialDiscretizer(resolution=resolution),
            ["latitude", "longitude"],
        ),
        # One-hot the precip_type.
        (
            make_pipeline(
                SimpleImputer(
                    strategy="constant", fill_value="no_precipitation"
                ),
                OneHotEncoder(),
            ),
            ["precip_type"],
        ),
        remainder="passthrough",
    )

    return make_pipeline(column_transformer)


def get_one_hot_precip(pipeline):
    return (
        # This is the column transformer.
        pipeline.steps[0][1]
        # This is the embedded impute + encode pipeline.
        # Last is the passthrough, second to last is the pipeline.
        .transformers_[-2][1]
        # This isolates the one-hot encoder...
        .steps[1][1]
        # ... and retrieves the categories.
        .categories_[0]
    )


def get_features(pipeline):
    return (
        ["month", "nearby_sightings"]
        + list(get_one_hot_precip(pipeline))
        + RAW_FEATURES[4:]
    )


@click.command()
@click.argument("raw_features_file", type=click.File("r"))
@click.option(
    "--output-file",
    type=click.File("w"),
    default="data/processed/training_data.csv",
)
@click.option("--resolution", "-r", type=int, default=3)
def main(raw_features_file, output_file, resolution):
    raw_features = pd.read_csv(raw_features_file).assign(
        date=lambda x: pd.to_datetime(x.date)
    )

    pipeline = feature_pipeline(resolution)

    features = pipeline.fit_transform(
        raw_features[RAW_FEATURES], raw_features[TARGET].values
    )

    # Save features to a CSV.
    feature_frame = pd.DataFrame(
        np.concatenate([features, raw_features[[TARGET]].values], axis=1),
        columns=get_features(pipeline),
    )

    feature_frame.to_csv(output_file, index=False)


if __name__ == "__main__":
    main()
