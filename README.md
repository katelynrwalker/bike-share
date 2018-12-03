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

Idle times may be stochastic, but they still follow a distribution - an exponential distribution, to be exact. This means that we can model bike idle time as a probability function. Observing bikes in a particular location, we might see that 50% of them depart in the first hour, 70% in the first two hours, and so on. So when a new bike gets parked in that location, we can immediately say that bike has a 50% chance of leaving within an hour, 70% in two hours, and so on.

[Insert exponential plots]

## Estimating Probabilities of Bike Depatures

Whenever a bike is parked, the probability of that bike leaving after x hours can be immediately generated based on an exponential probability function. The exponential function is defined by a single parameter - beta - which is equal to both the rate of "decay" of departure time and also the expected value (mean) of departure time. This is really handy! It means that beta value for a particular bike can be estimated as the mean departure time of the previously observed "neighbors" (in both time and space) of that bike. 

[insert probability curve here]

The model_training.py script runs a grid search cross validation on a set of bike data and finds the best number of nearest neighbors and weighting function (uniform or declining). The k-nearest neighbors (KNN) model is then trained using these best parameters and pickled for future use.

(As an aside, I also looked at a Bayesian updating technique for estimating the beta parameter. The code for that can be found in deprecated_models/model_bayesian.py. KNN outperformed this for a couple reasons. The Bayesian model also relies on neighbors to update a prior estimate of beta. But that prior estimate of beta will continue to influence the posterior estimate of beta, and I don't have any special knowledge that makes my prior beta estimate any better than looking at the neighbors alone. In addition to neighbors alone being a better predictor, it's also a simpler model that runs much faster than Bayesian updating.)

## So what can we do with probabilities of bike departures?

Now every bike gets a probability model of its departure time as soon as it parks. But this still doesn't tell us what bikes are going to sit around for excessively long periods of time. We do know that some bikes are likely to sit for longer than others, but the model doesn't predict extremes, because those are due to random chance within a probabilistic model.

A bike should be moved when we predict that the potential profit to be made by moving that bike to a better area exceeds the cost of moving that bike. For the purposes of this model, I'm making an assumption that a bike can make, on average, \$0.50 an hour. And that it costs \$5.00 to move it. This means that a bike should be moved if we expect it to sit for over 10 hours.

The expected values from the probability models almost never reach ten hours. But we can look at the probability models and decide on some threshold probability at which we pull the trigger on moving a bike. Which probability should we choose? Working with probabilities, we're going to be wrong about moving the bike sometimes, and correct othertimes. At which threshold are we correct the most without being incorrect too many times? Let's try them all and see what makes us the most profit: 

[insert profit curve here]

Looks like if we have a 16% probability that a bike is going to sit for ten hours, we should move it to maximize profit.

[insert confusion matrix here]

## Another, even better, use case

An even more interesting thing we can do with this probability model is detect bikes which have sat around for an unusually long amount of time. Once a bike exceeds the time at which it was 95% likely to depart, that means there is only a 1 in 20 chance that bike would still be there acorrding to the randomness of the universe - making it fairly likely at this point that there might be something wrong with it (broken, hidden in the bushes, etc.) and someone should be sent to go check on it!

Looking at the numbers, a bike sits on average for 2.8 hours after being parked, and 50% of bikes leave in just 0.8 hours. Once a bike has exceeded it's 95% probability of departure, it sits on average for another 5.8 hours (in addition to the time it's already sat to get to this point!), or it takes another 4.7 hours for 50% of these bikes to leave. So it certainly seems like something is going on with these bikes making them less likely to be ridden!

## Future expansions

This probability model could also be used to help riders find the likelihood that a bike will be available to them some time period from now (say 30-60 minutes). The probability of departure of existing bikes could be combined with a rate of arrival of new bikes to create a probability that a bike will be available to you at some near point in the future.

The profit model for finding probability threshholds could be improved in two ways. First, including an adjustment for demand would be more realistic - a bike has greater potential profit if it's moved to an area with current high demand as compared to if it's moved at a low demand time of day. Second, the availability of other nearby bikes should be taken into account. A low traffic area with three available bikes is a higher priority to relocate a bike than the same area with one available bike. In addition, a minimum service level should be set so that an area is not end up completely cleared of bikes.

## How to use this code

If you'd like to collect your own bikeshare data from JUMP, perhaps for a different city and/or time period, run bike_requests.py for a week or more to get yourself a training set (I recommend doing this on an AWS EC2 server so you can turn your computer off!). Adjust the API web address in there for your city of interest. Once you've collected that data you can run it through model_training.py to train a knn model on it and save that model as a pickle. You will need to go into the beginning of that model_training code and change the filepath to your data. 

If you just want to play with this and haven't collected your own data, no worries, the pickled model I used is saved in pickles/knn_pickle.p (and the scaler to bring all the data into a constant set of units is pickles/scaler.p).

If you've collected your own data, feel free to change the file paths referenced in clean_EDA.ipynb to get some visuals on your data.

[the code for this next part is still in the cost_model.ipynb notebook - need to clean it up for generalized use; the script/methods referenced below don't actually exist yet.]
Once you have a trained model to play with, you'll also need some current data to try it out on. Run bike_requests.py again. After a minute, you can run the data through the cost_model.py/should_it_move method to see if any of your bikes get flagged as one that should be moved based on a probability of sitting for too long. If you've collected at least a few hours worth of new data, you can run it through cost_model.py/detect_broken method to see if any bikes get flagged as having sat for too long and should be checked out as being potentially broken or hidden.