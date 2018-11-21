import featurization

import pandas as pd
import geopandas
import numpy as np
import scipy.stats as scs


def get_nearest_neighbor_bikes(location, datetime, geodf, radius):
    '''
    Finds all bikes within 1000ft on same day of week within a 3 hour window.

    Inputs: location of interest(shapely Point),
            datetime of interest,
            geopandas dataframe of historic bike info,
            radius to search in (feet)
    Output: list of the nearest neighbor bikes (indices of the dataframe)
    '''

    buff = geopandas.GeoSeries(location).buffer(radius)
    points_in_buff = geodf[geodf.intersects(buff.iloc[0])]
    neighbor_bikes = points_in_buff[(points_in_buff['day_of_week'] == datetime.dayofweek) &
            (points_in_buff['time_of_day_start'] <= datetime.hour+1) &
            (points_in_buff['time_of_day_start'] >= datetime.hour-1)]

    return neighbor_bikes


def get_mean_interarrival_time(location, datetime, geodf, radius):
    neighbor_df = model_neighbors.get_nearest_neighbor_bikes(one_bike, geodf, radius)
    if len(neighbor_df) < 2:
        return 90
    interarrival_times = []
    for date in neighbor_df['local_time_start'].dt.date.unique():
        df = neighbor_df[neighbor_df['local_time_start'].dt.date == date]
        if len(df) < 2:
            interarrival_times.append(90)
        arrival_times = sorted(df['local_time_start'].dt.minute)
        for x in range(len(arrival_times)-1):
            interarrival_times.append(arrival_times[x+1]-arrival_times[x])
    mean_interarrival_time = np.array(interarrival_times).mean()
    return mean_interarrival_time
