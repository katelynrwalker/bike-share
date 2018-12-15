import featurization

from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

import numpy as np
import geopandas
import pandas
import pickle


class knn_prob_model(KNeighborsRegressor):


    def _standard_confusion_matrix(y_t, y_p):
        y_true = np.array(y_t)
        y_predict = np.array(y_p)
        tp = np.sum((y_true == y_predict) & (y_true == 1))
        fp = np.sum((y_true != y_predict) & (y_true == 0))
        fn = np.sum((y_true != y_predict) & (y_true == 1))
        tn = np.sum((y_true == y_predict) & (y_true == 0))
        return np.array([[tp, fp], [fn, tn]])


    def _profit_curve(cost_matrix, thresholds, probs, true_labels):
        profits = []
        for t in thresholds:
            cf = _standard_confusion_matrix(true_labels, prob_bike_is_there > t)
            profits.append(np.sum(cf * cost_matrix)/np.sum(cf))
        return np.array([thresholds,profits]).T


    def fit_prob_threshold(self, X2, y2, cost_idle, cost_relocate):
        '''
        X2 and y2 are a test set used to find the best probability threshold
        (distinct from the training set)

        Must run fit first.

        '''
        self.relocate_time = cost_relocate/cost_idle
        avg_hours_idle = self.X[self.X['idle_hours']>relocate_time]['idle_hours'].mean()

        self.cost_matrix = np.array([[avg_hours_idle*cost_idle,  -cost_relocate],
                                     [ 0,  0]])

        thresholds = np.linspace(0.05, 1)

        y_pred = predict(X2)
        prob_bike_is_there = [1-scs.expon(scale=y_pred[i]).cdf(self.relocate_time) for i in range(len(y_pred))]

        profit = _profit_curve(self.cost_matrix, thresholds, prob_bike_is_there, y2)
        self.prob_threshold = profit[profit[:,1].argmax(),0]


    def should_it_move(self, one_bike):
        '''
        one_bike (1 row geodf or 2D numpy array, a bike you want to make a prediction about.
                            Required fields: lat(float),
                                             lon(float),
                                             time_of_day_start (int),
                                             day_of_week (int))

        Must run fit_prob_threshold first.
        '''

        y_pred = predict(one_bike)
        prob_bike_is_there = 1-scs.expon(scale=y_pred).cdf(self.relocate_time)
        if prob_bike_is_there > self.prob_threshold:
            return True


    def detect_broken(self, one_bike):
        '''
        one_bike (1 row geodf or 2D numpy array, a bike you want to make a prediction about.
                            Required fields: lat(float),
                                             lon(float),
                                             time_of_day_start (int),
                                             day_of_week (int),
                                             idle_hours (float) - hours bike has sat so far)

        Must run fit_prob_threshold first.
        '''
        y_pred = predict(one_bike)
        likely_departure = scs.expon(scale=y_pred).ppf(.95))
        if one_bike.idle_hours > likely_departure:
            return True



if __name__ == '__main__':
    #read in training data
    train_geodf = featurization.featurization_for_knn("bike-data/all-sc-bike-data-1101.csv")

    train_raw = train_geodf.sort_values('utc_time_start', axis=0)

    #split the training data. The first part is used to cross validate and train
    #the knn model. The second part is used to
    #train_split = TimeSeriesSplit(n_splits=2)
    #train_raw1 =
    #train_raw2 = 

    X_raw = train_raw1[["lon", "lat", "time_of_day_start", "day_of_week"]]
    y = train_raw1["idle_hours"]

    #scale features data
    scaler = StandardScaler()
    scaler.fit(X_raw.astype(float))
    X = scaler.transform(X_raw.astype(float))

    #run a grid search to find best params for knn model
    tscv = TimeSeriesSplit(n_splits=3)
    model = KNeighborsRegressor()
    gcv = GridSearchCV(model, param_grid={"n_neighbors":range(10,60),
                                            "weights":["uniform","distance"]},
                       verbose=1,
                       cv=tscv.split(X),
                       error_score=np.nan)
    gcv.fit(X, y)

    print ('best params: {}'.format(gcv.best_params_))
    print ('score: {}'.format(gcv.best_score_))

    #fit knn model using best params from grid search
    knn_model=KNeighborsRegressor(**gcv.best_params_)
    knn_model.fit(X, y)

    #save fitted model and scaler
    pickle.dump(knn_model, open('knn_pickle.p', 'wb'))
    pickle.dump(scaler, open('scaler.p', 'wb'))
