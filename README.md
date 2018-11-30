# Go get that bike! 
### Finding underused bikes in dockless bike share systems

Bike shares provide one solution to the “final mile” problem of public transit - helping people to get from their homes, workplaces, or other locations to the nearest transit stop, which may not always be in convenient walking distance. In recent years, dock-based bike shares have been quite successful in major cities, where they receive the heaviest use during commute hours.  Dockless bike shares provide a more flexible alternative to dock-based models, and may be well suited to expanding beyond city cores and transit lines. 

However, because they are dockless, these bikes can be taken anywhere, and may be left in areas with little foot traffic and few future riders. Bikes which sit idle in quiet areas are not available to riders elsewhere who might need them, and aren’t making money for the company. Identifying when a bike is likely to be left idle would allow the company to target that bike for repositioning.

The goals of this project were to predict how long a bicycle is likely to sit idle before it is re-rented, and then use that idle time prediction to identify bicycles that are worthwhile to relocate (where the lost revenue from an underused bike exceeds the cost of relocation). The probabilistic model used for this prediction can also be used to flag bikes that are likely to be broken or hidden (bikes that shouldn't be sitting for as long as they have, and should have someone go check on them).

## Data Pipeline

Data was collected in real time from the JUMP API for Santa Cruz, CA (https://sc.jumpbikes.com/opendata/gbfs.json). This API is updated once a minute with real time data on the location and battery status of each bike available for rental. Bikes currently being rented disappear from the API. I collected a couple weeks worth of data using an Amazon EC2 server, and then aggregated them using a series of pandas transformations in the featurization.py code. This aggregation resulted in a data set where each row is a single "idle event" - a bike that is parked and then sits for some period of idle time before being rented or moved.

The featurization pipeline also adds a geospatial reference to each idle event, and then uses spatial joins to add city zoning and census information to each idle event. Spatial joins allow you to add features to a point from data found in a GIS shapefile. A point which falls within a polygon defined in the shapefile is assigned the features of that polygon. These geospatial actions are accomplished using the geopandas package.

## Modeling

My first attempts at modeling attempted to predict exact departure time based on features such as time of day, day of week, city zone (residential, commercial, etc.), and population density. A gradient boosting model was able to predict departure time about 20% better than the mean alone, but this is still a long ways off from making accurate predictions.

Looking at the data more closely, I observed that time and location had slightly different mean idle times, but were not a great predictor of the longest idle times - these appeared across all locations and parking times. Bike idle times follow general trends, but are highly stochastic within those broad trends, making it very difficult to predict exact departure times. 

Bikes departures follow exponential trends.

[to be continued...]