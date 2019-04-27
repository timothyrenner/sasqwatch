import click
import pandas as pd
import mlflow


from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.externals import joblib
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost.sklearn import XGBClassifier
from time import time
from loguru import logger
from yaspin import yaspin
from toolz import get

from assemble import RAW_FEATURES, TARGET
from features import feature_pipeline, get_one_hot_precip


def log_params(max_depth, learning_rate, n_estimators):
    logger.info(f"Max depth: {max_depth}.")
    logger.info(f"Learning rate: {learning_rate}.")
    logger.info(f"Num estimators: {n_estimators}.")
    mlflow.log_params(
        {
            "max_depth": str(max_depth),
            "learning_rate": str(learning_rate),
            "n_estimators": str(n_estimators),
        }
    )


def log_performance(model, test_x, test_y):
    test_pred = model.predict(test_x)
    test_pred_proba = model.predict_proba(test_x)

    acc = accuracy_score(test_y, test_pred)
    f1 = f1_score(test_y, test_pred)
    prec = precision_score(test_y, test_pred)
    rec = recall_score(test_y, test_pred)
    auc = roc_auc_score(test_y, test_pred_proba[:, 1])

    logger.info(f"Accuracy: {acc}.")
    logger.info(f"F1: {f1}.")
    logger.info(f"Precision: {prec}.")
    logger.info(f"Recall: {rec}.")
    logger.info(f"AUC: {auc}.")
    mlflow.log_metrics(
        {
            "accuracy": acc,
            "f1": f1,
            "precision": prec,
            "recall": rec,
            "auc": auc,
        }
    )


def log_feature_importances(model, importance_plot_file):
    final_features = (
        ["year", "month", "dayofmonth", "dayofyear"]
        + list(get_one_hot_precip(model.steps[0][1]))
        + RAW_FEATURES[4:]
    )
    features = {f"f{ii}": feature for ii, feature in enumerate(final_features)}
    importances = (
        model.steps[-1][1].get_booster().get_score(importance_type="gain")
    )

    feature_importances = pd.DataFrame(
        [
            {
                "feature": feature,
                "importance": get(coded_feature, importances, 0.0),
            }
            for coded_feature, feature in features.items()
        ]
    ).sort_values("importance", ascending=True).reset_index(drop=True)

    ax = feature_importances.plot(y="importance", x="feature", kind="barh")
    ax.get_figure().subplots_adjust(left=0.25)
    ax.get_figure().savefig(importance_plot_file)
    mlflow.log_artifact(importance_plot_file)


@click.command()
@click.argument("raw_training_data", type=click.File("r"))
@click.option("--model-file", "-m", type=str, default="model/model.pkl")
@click.option(
    "--prediction-file",
    "-p",
    type=click.File("w"),
    default="data/processed/predictions.csv",
)
@click.option(
    "--importance-plot-file",
    type=str,
    default="data/visualizations/feature_importances.png",
)
@click.option("--max-depth", type=int, default=3)
@click.option("--learning-rate", type=float, default=0.15)
@click.option("--n-estimators", type=int, default=500)
def main(
    raw_training_data,
    model_file,
    prediction_file,
    importance_plot_file,
    max_depth,
    learning_rate,
    n_estimators,
):
    training_data = pd.read_csv(raw_training_data)

    # Split the training and test set.
    train_x, test_x, train_y, test_y = train_test_split(
        training_data[RAW_FEATURES], training_data[TARGET], test_size=0.25
    )

    logger.info(f"Training set size: {train_x.shape[0]}.")
    logger.info(f"Test set size: {test_x.shape[0]}.")
    log_params(max_depth, learning_rate, n_estimators)

    # Make the pipeline.
    pipeline = make_pipeline(
        feature_pipeline(),
        XGBClassifier(
            max_depth=max_depth,
            learning_rate=learning_rate,
            n_estimators=n_estimators,
        ),
    )

    logger.info("Fitting the pipeline.")
    start = time()
    with yaspin(text="👣 Training model 👣", color="cyan"):
        pipeline.fit(train_x, train_y)

    logger.info(f"Model trained in {time() - start:.3f}s.")
    log_performance(pipeline, test_x, test_y)

    logger.info(f"Training model with full dataset.")
    start = time()
    with yaspin(text="👣 Training model (full dataset) 👣", color="cyan"):
        pipeline.fit(training_data[RAW_FEATURES], training_data[TARGET])

    # Make the final predictions.
    logger.info("Making final predictions.")
    predictions = pipeline.predict(training_data[RAW_FEATURES])
    prediction_probas = pipeline.predict_proba(training_data[RAW_FEATURES])
    training_data.loc[:, "sighting_predicted"] = predictions
    training_data.loc[:, "sighting_pred_proba"] = prediction_probas[:, 1]

    # Log the feature importances.
    logger.info(f"Saving feature importances to {importance_plot_file}.")
    log_feature_importances(pipeline, importance_plot_file)

    # Save the model pickle file.
    logger.info(f"Saving pickled pipeline to {model_file}.")
    joblib.dump(pipeline, model_file)

    # Save the predictions to a csv.
    logger.info(f"Saving final predictions to {prediction_file.name}.")
    training_data.to_csv(prediction_file, index=False)


if __name__ == "__main__":
    main()
