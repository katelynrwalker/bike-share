import featurization

import pandas as pd
import geopandas
import numpy as np
import scipy.stats as scs
import pickle


def get_prediction(model_pickle_path, scaler_pickle_path, X):

    knn_model = pickle.load(open(model_pickle_path, "rb"))
    scaler = pickle.load(open(scaler_pickle_path, "rb"))
    X_scaled = scaler.transform(X.astype(float))
    return knn_model.predict(X_scaled)



def standard_confusion_matrix(y_t, y_p):
    y_true = np.array(y_t)
    y_predict = np.array(y_p)
    tp = np.sum((y_true == y_predict) & (y_true == 1))
    fp = np.sum((y_true != y_predict) & (y_true == 0))
    fn = np.sum((y_true != y_predict) & (y_true == 1))
    tn = np.sum((y_true == y_predict) & (y_true == 0))
    return np.array([[tp, fp], [fn, tn]])


def create_simple_cost_matrix(avg_hours_idle, cost_idle, cost_relocate):

    relocate_time = cost_relocate/cost_idle
    cost_matrix = np.array([[ avg_hours_idle*cost_idle,  -cost_relocate],
                            [ 0,  0]])

def profit_curve(cost_matrix, thresholds, probs, true_labels):

    profits = []
    for t in thresholds:
        cf = standard_confusion_matrix(true_labels, prob_bike_is_there > t)
        profits.append(np.sum(cf * cost_matrix)/np.sum(cf))
    return np.array([thresholds,profits]).T


def find_prob_threshold_for_moving():
    cost_matrix = create_simple_cost_matrix(avg_hours_idle, cost_idle, cost_relocate)

    thresholds = np.linspace(0.05, 1)

    y_pred = get_prediction(model_pickle_path, scaler_pickle_path, X_test)
    prob_bike_is_there = [1-scs.expon(scale=y_pred[i]).cdf(relocate_time) for i in range(len(y_pred))]

    profit = profit_curve(cost_matrix, thresholds, prob_bike_is_there, true_labels)
    return profit[profit[:,1].argmax(),0]


#Need to convert this all into a class! variables become object attributes.

#the previous function returns the prob_threshold for this training set.
#This is consistent and doesn't need to be recalculated every time. Need to figure out
#if there is a way to save this value to feed in to the function below
def should_it_move(one_bike,
                   model_pickle_path = 'pickles/knn_pickle.p',
                   scaler_pickle_path = 'pickles/scaler.p',
                   prob_threshold = 0.16):
    '''
    one_bike (1 row geodf or 2D numpy array, a bike you want to make a prediction about.
                        Required fields: lat(float),
                                         lon(float),
                                         time_of_dat_start (int),
                                         day_of_week (int))
    '''

    y_pred = get_prediction(model_pickle_path, scaler_pickle_path, one_bike)
    prob_bike_is_there = 1-scs.expon(scale=y_pred).cdf(relocate_time)
    if prob_bike_is_there > prob_threshold:
        return True


def detect_broken():
    pass
