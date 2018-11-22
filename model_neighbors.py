import featurization

import pandas as pd
import geopandas
import numpy as np
import scipy.stats as scs


def get_nearest_neighbor_bikes(location, datetime, geodf, radius):
    '''
    Finds all bikes within a given radius on same day of week within a 3 hour window.

    Inputs: location of interest(shapely Point),
            datetime of interest,
            geopandas dataframe of historic bike info,
            radius to search in (feet)
    Output: list of the nearest neighbor bikes (indices of the dataframe)
    '''

    buff = geopandas.GeoSeries(location).buffer(radius)
    points_in_buff = geodf[geodf.intersects(buff.iloc[0])]
    neighbor_bikes = points_in_buff[(points_in_buff['day_of_week'] == datetime.weekday()) &
            (points_in_buff['time_of_day_start'] <= datetime.hour+1) &
            (points_in_buff['time_of_day_start'] >= datetime.hour-1)]

    return neighbor_bikes


def get_mean_interarrival_time(location, datetime, geodf, radius):
    '''
    Finds the average time between bike arrivals within a given area (radius in feet)
    (based on same day of week within a 3 hour window).

    Inputs: location of interest(shapely Point),
            datetime of interest,
            geopandas dataframe of historic bike info,
            radius to search in (feet)
    Output: average time between bike arrivals, in hours
    '''

    larger_search = False
    neighbor_df = get_nearest_neighbor_bikes(location, datetime, geodf, radius)
    if len(neighbor_df) < 6:
        #if this search area doesn't return enough comparison bikes, enlarge it
        larger_search = True
        neighbor_df = get_nearest_neighbor_bikes(location, datetime, geodf, radius*2)
    if len(neighbor_df) < 6:
        #if the enlarged search area still doesn't return enough comparison bikes, then this
        #is a low traffic area/time. Just return a high value for the interarrival time
        #so that the model won't predict any bikes arriving
        return 1.5
    interarrival_times = []
    for date in neighbor_df['local_time_start'].dt.date.unique():
        df = neighbor_df[neighbor_df['local_time_start'].dt.date == date]
        if len(df) < 2:
            interarrival_times.append(1.5)
        hours = df['local_time_start'].dt.hour + df['local_time_start'].dt.minute/60
        arrival_times = sorted(hours)
        for x in range(len(arrival_times)-1):
            interarrival_times.append(arrival_times[x+1]-arrival_times[x])
    mean_interarrival_time = np.array(interarrival_times).mean()
    if larger_search:
        mean_interarrival_time 
    return mean_interarrival_time
