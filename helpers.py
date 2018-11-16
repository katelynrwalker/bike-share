import contextily as ctx
import featurization as f
import pandas as pd
import geopandas
import matplotlib.pyplot as plt


def map_bikes(ax, geodf, label_by=None, zoom=15, **kwargs):
    '''
    Plot information from a geodataframe on a map.

    Input:
    ax: a matplotlib axis
    geodf: a geopandas dataframe, with the geometry column labeled as "geolocation"
    color_by: string, column name from geodf to use as a colorramp
    label_by: string, column name from geodf to use as labels/annotations
    zoom: int, zoom level for basemap
    '''
    w, s, e, n = geodf.total_bounds
    try:
        img, ext = ctx.bounds2img(w, s, e, n, zoom, ll=True)
        ax.imshow(img, extent=ext)
    except Exception as ex:
        print("encountered problem: {}".format(ex))

    new_crs_bike = geodf.to_crs(epsg=3857)
    new_crs_bike.plot(ax=ax, **kwargs)
    if label_by != None:
        new_crs_bike.apply(lambda x: ax.annotate(s=x[label_by], xy=x.geolocation.centroid.coords[0], ha='right', size=14, alpha=0.5),axis=1)
    ax.axis('off')

    return ax


def add_blockgroup_geometry(df):
    '''
    Add GIS shapefile geometry of each blockgroup to a dataframe.
    Intended for use with dataframes that have been grouped by blockgroup.

    Input: a pandas dataframe
    Output: a geopandas dataframe
    '''

    b = geopandas.read_file('tl_2016_06_bg')
    b.crs = {'init':'epsg:4269'}
    b.drop(['STATEFP', 'COUNTYFP', 'TRACTCE', 'BLKGRPCE', 'NAMELSAD',
       'MTFCC', 'FUNCSTAT', 'ALAND', 'AWATER', 'INTPTLAT', 'INTPTLON'], axis=1, inplace=True)
    blockgroupdf = geopandas.read_file('ACS_2016_5YR_BG_06_CALIFORNIA.gdb', driver='FileGDB', layer='ACS_2016_5YR_BG_06_CALIFORNIA')
    b = b.merge(blockgroupdf[['GEOID', 'GEOID_Data']], on="GEOID")
    geodf = b.merge(df, how='inner', on="GEOID_Data")

    return geodf
