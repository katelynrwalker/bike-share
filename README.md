# Go get that bike! 
### Finding underused bikes in dockless bike share systems

Bike shares provide one solution to the “final mile” problem of public transit - helping people to get from their homes, workplaces, or other locations to the nearest transit stop, which may not always be in convenient walking distance. In recent years, dock-based bike shares have been quite successful in major cities, where they receive the heaviest use during commute hours.  Dockless bike shares provide a more flexible alternative to dock-based models, and may be well suited to expanding beyond city cores and transit lines. 

However, because they are dockless, these bikes can be taken anywhere, and may be left in areas with little foot traffic and few future riders. Bikes which sit idle in quiet areas are not available to riders elsewhere who might need them, and aren’t making money for the company. Identifying when a bike is likely to be left idle would allow the company to target that bike for repositioning.

The goals of this project were to predict how long a bicycle is likely to sit idle before it is re-rented, and then use that idle time prediction to identify bicycles that are worthwhile to relocate (where the lost revenue from an underused bike exceeds the cost of relocation). The probabilistic model used for this prediction can also be used to flag bikes that are likely to be broken or hidden (bikes that shouldn't be sitting for as long as they have been, and should have someone go check on them).

## Data Pipeline

Data was collected in real time from the JUMP API for Santa Cruz, CA (https://sc.jumpbikes.com/opendata/gbfs.json). This API is updated once a minute with real time data on the location and battery status of each bike available for rental. Bikes currently being rented disappear from the API. I collected a couple weeks worth of data using an Amazon EC2 server, and then aggregated them using a series of pandas transformations in the featurization.py code. This aggregation resulted in a data set where each row is a single "idle event" - a bike that is parked and then sits for some period of idle time before being rented or moved.

The featurization pipeline also adds a geospatial reference to each idle event, and then uses spatial joins to add city zoning and census information to each idle event. Spatial joins allowed me to add features to a point from data found in a GIS shapefile - a point which falls within a shapefile polygon is assigned the features of that polygon. These geospatial actions are accomplished using the geopandas package.

## Some General Observations

The clean_EDA.ipynb notebook takes a first pass through the data at a high level - looking at general patterns and seeing what we can learn about bike shares in Santa Cruz before we get deep into number crunching and modeling. Take a look at that file to get an intial understanding of what's going on (with lots of pretty pictures!)

## Modeling

My first attempts at modeling attempted to predict exact departure time based on features such as time of day, day of week, city zone (residential, commercial, etc.), and population density. A gradient boosting model was able to explain about 15% of the variance in the data (it predict departure time about 15% better than the mean alone), but this is still a long ways off from making accurate predictions.

Looking at the data more closely, I observed that the longest idle times appeared across all locations and parking times. Bike idle times turn out to be highly stochastic, making it very difficult to predict exact departure times. 

Idle times may be stochastic, but they still follow a distribution - an exponential distribution, to be exact. This means that we can model bike idle time as a probability function. Observing bikes in a particular location, we see that 50% of them depart in the first hour, 70% in the first two hours, and so on. So when a new bike gets parked in that location, we can immediately say that bike has a 50% chance of leaving within an hour, 70% in two hours, and so on.

[Insert exponential plots]

## Estimating Probabilities of Bike Depatures

Whenever a bike is parked, the probability of that bike leaving after x hours can be immediately generated based on an exponential probability function. The exponential function is defined by a single parameter - beta - which is equal to both the rate of "decay" of departure time and also the expected value (mean) of departure time. This is really handy! It means that beta value for a particular bike can be estimated as the mean departure time of the previously observed "neighbors" (in both time and space) of that bike. 

The model_training.py script runs a grid search cross validation on a set of bike data and finds the best number of nearest neighbors and weighting function (uniform or declining). The k-nearest neighbors (KNN) model is then trained using these best parameters and pickled for future use.

(As an aside, I also looked at a Bayesian updating technique for estimating the beta parameter. The code for that can be found in deprecated_models/model_bayesian.py. KNN outperformed this for a couple reasons. The Bayesian model also relies on neighbors to update a prior estimate of beta. But that prior estimate of beta will continue to influence the posterior estimate of beta, and I don't have any special knowledge that makes my prior beta estimate any better than looking at the neighbors alone. In addition to neighbors alone being a better predictor, it's also a simpler model that runs much faster than Bayesian updating.)


## So what can we do with probabilities of bike departures?



## How to use this code

