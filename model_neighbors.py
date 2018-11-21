import featurization

import pandas as pd
import geopandas
import numpy as np
import scipy.stats as scs


def get_nearest_neighbor_bikes(one_bike, geodf, radius):
    '''
    Finds all bikes within 1000ft on same day of week and hour of day.

    Inputs: bike of interest, geopandas dataframe
    Output: list of the nearest neighbor bikes
    '''

    one_point = one_bike['geolocation']
    buff = geopandas.GeoSeries(one_point).buffer(radius)
    points_in_buff = geodf[geodf.intersects(buff.iloc[0])]
    points = points_in_buff[(points_in_buff['day_of_week'] == one_bike['day_of_week']) &
            (points_in_buff['time_of_day_start'] == one_bike['time_of_day_start'])]

    return list(points.index.values)
