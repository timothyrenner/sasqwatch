import click
import pandas as pd
import numpy as np
from sklearn.compose import make_column_transformer
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from assemble import RAW_FEATURES, TARGET


def featurize_time(frame, date_col="date"):
    frame.loc[:, date_col] = pd.to_datetime(frame[date_col])
    return frame.assign(
        month=frame[date_col].dt.month,
        dayofmonth=frame[date_col].dt.day,
        dayofyear=frame[date_col].dt.dayofyear,
    ).drop(columns=[date_col])


def featurize_geography(
    frame, latitude_col="latitude", longitude_col="longitude"
):
    # Obviously we'll do a little more with this later.
    return frame.drop(columns=[latitude_col, longitude_col])


def feature_pipeline():
    column_transformer = make_column_transformer(
        # Featurize the dates and drop the date column.
        (FunctionTransformer(featurize_time, validate=False), ["date"]),
        # Featurize the geography and drop the latitude / longitude columns.
        (
            FunctionTransformer(featurize_geography, validate=False),
            ["latitude", "longitude"],
        ),
        # One-hot the precip_type.
        (
            make_pipeline(
                SimpleImputer(strategy="constant", fill_value="unknown"),
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


@click.command()
@click.argument("raw_features_file", type=click.File("r"))
@click.option(
    "--output-file",
    type=click.File("w"),
    default="data/processed/training_data.csv",
)
def main(raw_features_file, output_file):
    raw_features = pd.read_csv(raw_features_file).assign(
        date=lambda x: pd.to_datetime(x.date)
    )

    pipeline = feature_pipeline()

    features = pipeline.fit_transform(raw_features[RAW_FEATURES])

    # Save features to a CSV.
    feature_cols = (
        ["month", "dayofmonth", "dayofyear"]
        + list(get_one_hot_precip(pipeline))
        # Remove the first four columns because they're transformed.
        + RAW_FEATURES[4:]
        + [TARGET]
    )

    feature_frame = pd.DataFrame(
        np.concatenate([features, raw_features[[TARGET]].values], axis=1),
        columns=feature_cols,
    )

    feature_frame.to_csv(output_file, index=False)


if __name__ == "__main__":
    main()
