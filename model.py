import featurization

import geopandas
import numpy as np
import scipy.stats as scs


def get_beta_for_blockgroups(geodf):
    '''
    Divides all idle bike observations by blockgroup (proxy for regions of the city), then fits an exponential distribution to each grouping.

    Input: Dataframe (geopandas or pandas)
    Output: Dictionary
            keys: blockgroup name (from GEOID_Data column of dataframe),
            values: estimated beta value for an exponential distribution of idle_times in that blockgroup
    '''

    blockgroups = geodf.GEOID_Data.unique()
    beta_all = scs.expon.fit(geodf['idle_hours'])[1]

    beta_by_bg = {}
    for bg in blockgroups:
        bikes_in_bg = geodf[geodf.GEOID_Data == bg]
        if len(bikes_in_bg) > 10:
            beta_bg = scs.expon.fit(bikes_in_bg['idle_hours'])[1]
            beta_by_bg[bg] = beta_bg
        else:
            beta_by_bg[bg] = beta_all

    return beta_by_bg


def get_nearest_neighbor_bikes(one_bike, geodf):
    '''
    Finds all bikes within 1000ft on same day of week and hour of day.

    Inputs: bike of interest, geopandas dataframe
    Output: geopandas dataframe
    '''

    one_point = one_bike['geolocation']
    buff = geopandas.GeoSeries(one_point).buffer(1000)
    points_in_buff = geodf[geodf.intersects(buff.iloc[0])]
    points = points_in_buff[(points_in_buff['day_of_week'] == one_bike['day_of_week']) &
            (points_in_buff['time_of_day_start'] == one_bike['time_of_day_start'])]

    return list(points.bike_id.values)


def bayesian_update(prior_beta_dist, hyp_betas, datapoints):
    '''
    Updates a prior distribution of eponential beta values based on more
    specific bike idle time observations.

    Inputs: prior_beta_dist(array-like), hyp_betas(array-like), datapoints(dataframe)
    Output: posterior_beta_dist(numpy array)
    '''

    if len(datapoints) == 0:
        #in the case where there are no similar datapoints to update the
        #distribution with, just return the prior distribution in array format
        #(aka the distribution that's been fit to the entire blockgroup)
        return prior_beta_dist.pdf(hyp_betas)

    posterior_beta_dist = []
    for beta0 in hyp_betas:
        likelihood = np.prod(scs.expon(scale=beta0).pdf(datapoints['idle_hours']))
        posterior_beta_dist.append(likelihood*prior_beta_dist.pdf(beta0))
    posterior_beta_dist = np.array(posterior_beta_dist)
    posterior_beta_dist /= posterior_beta_dist.sum()
    return posterior_beta_dist
