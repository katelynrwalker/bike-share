import featurization

from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

import numpy as np
import geopandas
import pandas
import pickle

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
