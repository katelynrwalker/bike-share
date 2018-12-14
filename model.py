import featurization

from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

import numpy as np
import geopandas
import pandas
import pickle


class knn_prob_model(KNeighborsRegressor):

    def fit(self, X, y, cost_idle, cost_relocate):
        self.X = X
        self.y = y
        self.cost_idle = cost_idle
        self.cost_relocate = cost_relocate

        self.relocate_time = cost_relocate/cost_idle
        avg_hours_idle = self.X[self.X['idle_hours']>relocate_time]['idle_hours'].mean()

        self.cost_matrix = np.array([[avg_hours_idle*self.cost_idle,  -self.cost_relocate],
                                     [ 0,  0]])


    def fit_prob_threshold(self, X2, y2):
        '''
        X2 and y2 are a test set used to find the best probability threshold
        (distinct from the training set)
        '''
        thresholds = np.linspace(0.05, 1)

        y_pred = predict(X2)
        prob_bike_is_there = [1-scs.expon(scale=y_pred[i]).cdf(self.relocate_time) for i in range(len(y_pred))]

        profit = profit_curve(self.cost_matrix, thresholds, prob_bike_is_there, y2)
        self.prob_threshold = profit[profit[:,1].argmax(),0]


if __name__ == '__main__':
    #read in training data
    train_geodf = featurization.featurization_for_knn("bike-data/all-sc-bike-data-1101.csv")

    train_raw = train_geodf.sort_values('utc_time_start', axis=0)
    X_raw = train_raw[["lon", "lat", "time_of_day_start", "day_of_week"]]
    y = train_raw["idle_hours"]

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
