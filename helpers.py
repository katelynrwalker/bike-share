import contextily as ctx
import featurization as f
import pandas as pd
import matplotlib.pyplot as plt


def map_bikes(ax, geodf, color_by, label_by=None, zoom=15):
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
    img, ext = ctx.bounds2img(w, s, e, n, zoom, ll=True)
    ax.imshow(img, extent=ext)
    new_crs_bike = geodf.to_crs(epsg=3857)
    new_crs_bike.plot(ax=ax, column=color_by, cmap='coolwarm')
    if label_by != None:
        new_crs_bike.apply(lambda x: ax.annotate(s=x[label_by], xy=x.geolocation.centroid.coords[0], ha='right', size=14),axis=1)
    ax.axis('off')
    
    return ax