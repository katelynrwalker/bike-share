import pandas as pd
import geopandas
from shapely.geometry import Point
import datetime

def import_and_clean_data(filename):
    '''
    Imports a csv file,
    converts it to a pandas dataframe,
    drops duplicates (when api didn't update between requests),
    drops unneeded columns,
    converts battery level to an int,
    creates utc time columns with datetime objects,
    rounds lat/long to nearest 0.00001 degrees (approximately 3 feet)

    Input: name of file, in csv format
    Output: pandas dataframe
    '''
    raw = pd.read_csv(filename)

    raw.drop_duplicates(inplace = True)

    raw.drop(['is_disabled', 'is_reserved', 'update_time', 'name'], axis = 1, inplace = True)
    raw['jump_ebike_battery_level'] = raw['jump_ebike_battery_level'].str.strip('%').astype(int)

    raw['utc_time'] = pd.to_datetime(raw['datetime'], unit='s')
    raw['utc_time'] = raw['utc_time'].dt.tz_localize('UTC')

    # one way of keeping bikes that "move" without being ridden in the same group - rounding to smooth out GPS error.
    raw = raw.round({'lat':5, 'lon':5})

    return raw

def group_and_create_target(raw_df):
    '''
    Takes a cleaned dataframe with unique entries for every available bike at every minute.
    Groups those entries by bike and location,
    then returns a df with entries for each bike as it sits idle at one location.
    Output includes the target: idle_time

    Input: pandas dataframe
    Output: pandas dataframe, with consolidated information for each idle event
    '''

    idle_bikes =raw_df.groupby(by=['bike_id', 'lat', 'lon'])

    #get the information of interest for each idle event
    idle_time = idle_bikes.utc_time.max() - idle_bikes.utc_time.min()
    idle_batt_start = idle_bikes.jump_ebike_battery_level.first()
    idle_batt_end = idle_bikes.jump_ebike_battery_level.last()
    idle_utc_time_start = idle_bikes.utc_time.first()
    idle_utc_time_end = idle_bikes.utc_time.last()

    #convert the pandas group object into a dataframe
    idle_df = idle_time.reset_index(name='idle_time')

    #merge all other group objects into the idle_dataframe
    to_merge = [idle_batt_start, idle_batt_end, idle_utc_time_start, idle_utc_time_end]
    merge_names = ['batt_start', 'batt_end', 'utc_time_start', 'utc_time_end']
    for m, name in zip(to_merge, merge_names):
        m_df = m.reset_index(name = name)
        idle_df = pd.merge(idle_df, m_df)

    #sort by time - some of the functions below use .shift to compare rows and
    #depend on the bikes being grouped by id and in sequential order.
    idle_df.sort_values(['bike_id', 'utc_time_start'], axis=0, inplace=True)

    return idle_df

def drop_recharges(idle_df):
    '''
    Throws out all datapoints where battery level is below 40%. These bikes get
    flagged for recharging, so their idle behavior is going to be totally different.

    Input: pandas df
    Output: pandas df
    '''
    idle_df = idle_df[idle_df.batt_start > 39]
    return idle_df


def consolidate_missed_idle_bikes(idle_df):
    '''
    Takes a dataframe with entries for each idle bike, and looks for potentially
    missed idle events, where GPS errors or minor relocation caused bikes to move
    without actually being rented. Detects sequential idle events where charge
    level didn't change, new location was within ~300 ft, and time between idle
    events was less than 2:10 minutes. Consolidates these multiple idle events into
    a single idle event.

    Input: pandas df
    Output: pandas df
    '''

    same_bike = idle_df.bike_id == idle_df.bike_id.shift(-1)
    same_charge = idle_df.batt_end == idle_df.batt_start.shift(-1)
    same_loc = (idle_df.lat.round(3) == idle_df.lat.shift(-1).round(3)) & (idle_df.lon.round(3) == idle_df.lon.shift(-1).round(3))
    same_time = (idle_df.utc_time_start.shift(-1) - idle_df.utc_time_end).dt.seconds < 130
    missing_idle = (same_bike & same_charge & same_loc & same_time)

    #adjust times and filter out additional bikes that were actually idle but "moved" due
    #to GPS error or minor relocation
    idle_df.loc[missing_idle, 'utc_time_end'] = idle_df.utc_time_end.shift(-1)
    drops = missing_idle.shift(1)
    drops.iloc[0] = False
    idle_df = idle_df[~drops].copy()
    idle_df['idle_time'] = idle_df['utc_time_end'] - idle_df['utc_time_start']

    #sometimes a mixup in the first/last times causes an idle_time to be negative.
    #Drop these, but print how many are dropped in case it's a lot.
    print("Dropping {} entries where end time was before start time".format(
                sum(idle_df.idle_time < datetime.timedelta())
                ))
    idle_df = idle_df[idle_df.idle_time > datetime.timedelta()]

    return idle_df


def add_more_time_and_date_info(idle_df):
    '''
    Takes a dataframe consolidated by bike and location (idle events)
    then returns a df with additional information based on datetime info.

    Input: pandas dataframe (consolidated into idle events)
    Output: pandas dataframe, with additional feature columns
    '''

    #create a numerical column for idle time as well, because timedelta objects
    #don't work in some pandas functions, like groupby
    idle_df['idle_hours'] = idle_df['idle_time'].dt.total_seconds()/3600

    #add columns for local time
    idle_df['local_time_start'] = idle_df['utc_time_start'].dt.tz_convert('America/Los_Angeles')
    idle_df['local_time_end'] = idle_df['utc_time_end'].dt.tz_convert('America/Los_Angeles')

    #add columns for day of week and time of day
    idle_df['day_of_week'] = idle_df['local_time_start'].dt.dayofweek
    idle_df['time_of_day_start'] = idle_df['local_time_start'].dt.hour
    idle_df['time_of_day_end'] = idle_df['local_time_end'].dt.hour

    return idle_df


def create_flags_from_bike_info(idle_df):
    '''
    Takes a dataframe consolidated by bike and location (idle events)
    then returns a df with additional information based on charge levels and location

    Input: pandas dataframe (consolidated into idle events)
    Output: pandas dataframe, with additional feature columns
    '''

    same_bike_next = idle_df.bike_id == idle_df.bike_id.shift(-1)
    same_bike_prev = idle_df.bike_id == idle_df.bike_id.shift(1)

    #flags bikes that were charged at the end of this idle period
    #uses a threshold of 5% charge increase to avoid random battery fluctuations
    charge_change = -idle_df.batt_start.diff(periods=-1)
    gets_charged = charge_change > 5
    idle_df['gets_pickedup_charged'] = (same_bike_next & gets_charged)

    #flags bikes that were charged at the end of this idle period
    #uses a threshold of 5% charge increase to avoid random battery fluctuations
    charge_change = idle_df.batt_start.diff(periods=1)
    got_charged = charge_change > 5
    idle_df['just_got_charged'] = (same_bike_prev & got_charged)

    #flags bikes that were moved but not charged
    #recall bikes with same charge and roughly same location have already been filtered out
    same_charge = idle_df.batt_end == idle_df.batt_start.shift(-1)
    idle_df['gets_pickedup_not_charged'] = (same_bike_next & same_charge)

    #flags bikes that were charged during this idle period
    idle_df['in_charger'] = (idle_df.batt_end - idle_df.batt_start) > 5

    #creates labels for what happens to the bike after this idle period
    #(equivilent to 'gets_pickedup_charged' and 'gets_pickedup_not_charged',
    #but these labels are useful for mapping)
    idle_df['next_action'] = 'rented'
    idle_df.loc[idle_df['gets_pickedup_charged'], 'next_action'] = 'gets_pickedup_charged'
    idle_df.loc[idle_df['gets_pickedup_not_charged'], 'next_action'] = 'gets_relocated'

    return idle_df


def add_geolocation(idle_df):
    '''
    Takes a dataframe consolidated by bike and location (idle events)
    then returns a geopandas dataframe with geometry for each point.

    Input: pandas dataframe (consolidated into idle events)
    Output: geopandas dataframe, with geometry column called 'geolocation'
    '''

    idle_df['geolocation'] = idle_df.apply(lambda z: Point(z.lon, z.lat), axis=1)
    geodf = geopandas.GeoDataFrame(idle_df, geometry='geolocation')
    geodf.crs = {'init': 'epsg:4326'}

    return geodf


def add_zoning(geodf, zoning_file):
    '''
    Takes a geodataframe of bike idle events, and a shapefile with zoning information.
    Spatial joins zoning to bike idle events so that each event now has a zone
    associated with it. Returns a geopandas dataframe.

    Inner join clips the bike data to the city limits, which is approximately the
    extent of the JUMP service area.

    Note right now this is built to work with Santa Cruz zoning shapefile. Other
    cities likely have different fields/columns and function will need adjustment.

    Input: geopandas dataframe (bike idle events, with geometry column)
    Output: geopandas dataframe, with zone for each idle event
    '''

    zoningdf = geopandas.read_file(zoning_file)
    geodf = geodf.to_crs(crs={'proj': 'lcc',
                            'lat_1': 37.06666666666667,
                            'lat_2': 38.43333333333333,
                            'lat_0': 36.5,
                            'lon_0': -120.5,
                            'x_0': 2000000,
                            'y_0': 500000.0000000002,
                            'datum': 'NAD83',
                            'units': 'us-ft',
                            'no_defs': True})
    zoningdf.drop(['OBJECTID', 'SHAPE_LENG', 'SHAPEarea', 'SHAPElen'], axis = 1, inplace=True)
    geodf_plus = geopandas.sjoin(geodf, zoningdf, how="inner", op='intersects')
    geodf_plus.fillna(value = 'out', inplace=True)
    geodf_plus.drop('index_right', axis=1, inplace=True)

    return geodf_plus


def load_census_blockgroups():
    '''
    Creates a geodataframe of census blockgroups.

    For now the census files are hardcoded because they're statewide data, but
    they could be generalized if ever needed.

    Input: none
    Output: geopandas dataframe, with census blockgroups and some key features from the census data
    '''
    # load census data into dataframes.
    blockgroupdf = geopandas.read_file('geospatial_data/ACS_2016_5YR_BG_06_CALIFORNIA.gdb',
                                        driver='FileGDB',
                                        layer='ACS_2016_5YR_BG_06_CALIFORNIA')
    blockgroup_pop = geopandas.read_file('geospatial_data/ACS_2016_5YR_BG_06_CALIFORNIA.gdb',
                                        driver='FileGDB',
                                        layer='X00_COUNTS')
    blockgroup_pop.rename({'GEOID':'GEOID_Data'}, axis=1, inplace=True)

    #geopandas is not reading the crs from census files, and census metadata
    #does not include information on the crs. This is a workaround using a file
    #with a known crs.
    blockgroup_shape = geopandas.read_file('geospatial_data/tl_2016_06_bg')
    blockgroup_shape.crs = {'init':'epsg:4269'}
    bg = blockgroup_shape.merge(blockgroupdf[['GEOID', 'Shape_Area', 'GEOID_Data']], on="GEOID")

    bg = bg.merge(blockgroup_pop, on='GEOID_Data')

    # calculate features of each blockgroup
    bg['pop_density'] = bg['B00001e1']/bg['Shape_Area']
    bg['people_per_house'] = bg['B00001e1']/bg['B00002e1']

    #just pull out columns with features of interest and convert to the State Plane California crs
    bg_features = bg[['GEOID_Data', 'geometry_x', 'pop_density', 'people_per_house']]
    bg_features = geopandas.GeoDataFrame(bg_features, geometry = 'geometry_x', crs={'init': 'epsg:4269'})
    bg_features = bg_features.to_crs(crs={'proj': 'lcc',
                            'lat_1': 37.06666666666667,
                            'lat_2': 38.43333333333333,
                            'lat_0': 36.5,
                            'lon_0': -120.5,
                            'x_0': 2000000,
                            'y_0': 500000.0000000002,
                            'datum': 'NAD83',
                            'units': 'us-ft',
                            'no_defs': True})
    
    return bg_features


def add_census_blockgroups(geodf):
    '''
    Takes a geodataframe of bike idle events, and spatial joins that to census
    blockgroup shapefiles so that each event has census population associated
    with it. Returns a geopandas dataframe.

    For now the census files are hardcoded because they're statewide data, but
    they could be generalized if ever needed.

    Input: geopandas dataframe (bike idle events, with geometry column)
    Output: geopandas dataframe, with census (population) information for each idle event
    '''

    blockgroups = load_census_blockgroups()

    # spatial join blockgroup data to bike data (so each bike point gets the attributes
    # of the blockgroup it's in)
    geodf = geopandas.sjoin(geodf, blockgroups, how="left")
    geodf.drop('index_right', axis=1, inplace=True)

    return geodf


def all_featurization(filename):
    '''
    Master function to run all of the above in one command
    '''
    raw_df = import_and_clean_data(filename)
    idle_df = group_and_create_target(raw_df)
    idle_df = drop_recharges(idle_df)
    idle_df = consolidate_missed_idle_bikes(idle_df)
    idle_df = add_more_time_and_date_info(idle_df)
    idle_df = create_flags_from_bike_info(idle_df)
    geodf = add_geolocation(idle_df)
    geodf = add_zoning(geodf, 'geospatial_data/Zoning')
    geodf = add_census_blockgroups(geodf)

    return geodf


def all_featurization_keep_recharges(filename):
    '''
    Master function to run all of the above in one command, without dropping
    bikes with low battery that are likely to be picked up for recharge (needed
    for finding the rate of bike arrivals)
    '''
    raw_df = import_and_clean_data(filename)
    idle_df = group_and_create_target(raw_df)
    idle_df = consolidate_missed_idle_bikes(idle_df)
    idle_df = add_more_time_and_date_info(idle_df)
    idle_df = create_flags_from_bike_info(idle_df)
    geodf = add_geolocation(idle_df)
    geodf = add_zoning(geodf, 'geospatial_data/Zoning')
    geodf = add_census_blockgroups(geodf)

    return geodf


def featurization_for_knn(filename):
    '''
    Master function to run all of the dataframe processing in one command,
    without the geospatial parts (faster processing for models that don't use
    those features). Note this does not drop bikes that are outside the service area.
    '''
    raw_df = import_and_clean_data(filename)
    idle_df = group_and_create_target(raw_df)
    idle_df = drop_recharges(idle_df)
    idle_df = consolidate_missed_idle_bikes(idle_df)
    idle_df = add_more_time_and_date_info(idle_df)
    idle_df = create_flags_from_bike_info(idle_df)

    return idle_df
