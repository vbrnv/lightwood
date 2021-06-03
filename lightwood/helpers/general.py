from sklearn.metrics import r2_score, f1_score, balanced_accuracy_score, accuracy_score
import numpy as np
import pandas as pd

from lightwood.api.dtype import dtype
from lightwood.api import Output


def evaluate_accuracy(predictions: pd.DataFrame,
                      data_frame: pd.DataFrame,
                      target_info: Output,
                      backend=None,
                      **kwargs) -> float:

    col_type = target_info.data_dtype
    column = target_info.name
    if col_type in [dtype.integer, dtype.float]:
        evaluator = evaluate_regression_accuracy
    elif col_type == dtype.categorical:
        evaluator = evaluate_classification_accuracy
    elif col_type == dtype.tags:
        evaluator = evaluate_multilabel_accuracy
    elif col_type == dtype.array:
        evaluator = evaluate_array_accuracy
        # @TODO: add typing info to target_info
        kwargs['categorical'] = True if dtype.categorical in target_info.typing.get('data_type_dist', []) else False
    else:
        evaluator = evaluate_generic_accuracy

    score = evaluator(
        column,
        predictions,
        data_frame[column],
        backend=backend,
        **kwargs
    )

    return 0.00000001 if score == 0 else score


def evaluate_regression_accuracy(
        column,
        predictions,
        true_values,
        backend,
        **kwargs
    ):
    if f'{column}_confidence_range' in predictions:
        Y = np.array(true_values)
        ranges = predictions[f'{column}_confidence_range']
        within = ((Y >= ranges[:, 0]) & (Y <= ranges[:, 1]))
        return sum(within)/len(within)
    else:
        r2 = r2_score(true_values, predictions['predictions'])
        return max(r2, 0)


def evaluate_classification_accuracy(column, predictions, true_values, **kwargs):
    pred_values = predictions['predictions']
    return balanced_accuracy_score(true_values, pred_values)


def evaluate_multilabel_accuracy(column, predictions, true_values, backend, **kwargs):
    # @TODO: use new API
    encoder = backend.predictor._mixer.encoders[column]
    pred_values = encoder.encode(predictions['predictions'])
    true_values = encoder.encode(true_values)
    return f1_score(true_values, pred_values, average='weighted')


def evaluate_generic_accuracy(column, predictions, true_values, **kwargs):
    pred_values = predictions['predictions']
    return accuracy_score(true_values, pred_values)


def evaluate_array_accuracy(column, predictions, true_values, **kwargs):
    accuracy = 0
    predictions = predictions['predictions']
    true_values = list(true_values)
    acc_f = balanced_accuracy_score if kwargs['categorical'] else r2_score
    for i in range(len(predictions)):
        if isinstance(true_values[i], list):
            accuracy += max(0, acc_f(predictions[i], true_values[i]))
        else:
            # For the T+1 usecase
            return max(0, acc_f([x[0] for x in predictions], true_values))
    return accuracy / len(predictions)
