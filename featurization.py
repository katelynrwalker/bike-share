import pandas as pd

def import_and_clean_data(filename):
    '''
    Imports a csv file, 
    converts it to a pandas dataframe, 
    drops unneeded columns,
    converts battery level to an int, 
    creates utc time columns with datetime objects,
    rounds lat/long to nearest 0.00001 degrees (approximately 3 feet)
    
    Input: name of file, in csv format
    Output: pandas dataframe
    '''
    raw = pd.read_csv("all-sc-bike-data-1101.csv")
    
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
    then returns a df with entries each bike as it sits idle at one location.
    
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
        
    #add a column for local time
    idle_df['local_time_start'] = idle_df['utc_time_start'].dt.tz_convert('America/Los_Angeles')
    
    #sort by time
    idle_df.sort_values(['bike_id', 'utc_time_start'], axis=0, inplace=True)
    
    #adjust times and filter out additional bikes that were actually idle but "moved" due to GPS error
    missing_idle = get_missed_idle_bikes(idle_df)
    idle_df.utc_time_end[missing_idle] = idle_df.utc_time_end.shift(-1)
    drops = missing_idle.shift(1)
    drops.iloc[0] = False
    idle_df = idle_df[~drops]
    idle_df['idle_time'] = idle_df['utc_time_end'] - idle_df['utc_time_start']
    
    #flags bikes that were charged at the end of this idle period
    #uses a threshold of 5% charge increase to avoid random battery fluctuations
    charge_change = -idle_df.batt_start.diff(periods=-1)
    idle_df['gets_pickedup_charged'] = charge_change > 5
    
    #flags bikes that were moved but not charged
    #recall bikes with same charge and roughly same location have already been filtered out
    same_bike = idle_df.bike_id == idle_df.bike_id.shift(-1)
    same_charge = idle_df.batt_end == idle_df.batt_start.shift(-1)
    idle_df['gets_pickedup_not_charged'] = (same_bike & same_charge)
    
    #flags bikes that were charged during this idle period
    idle_df['in_charger'] = (idle_df.batt_end - idle_df.batt_start) > 5
    
    return idle_df
    

def get_missed_idle_bikes(idle_df):
    '''
    Takes a dataframe with entries for each idle bike, and looks for potentially missed
    idle events, where GPS errors caused biked to move without actually being rented.
    
    Input: pandas df
    Output: pandas Series (booleans)
    '''
    same_bike = idle_df.bike_id == idle_df.bike_id.shift(-1)
    same_charge = idle_df.batt_end == idle_df.batt_start.shift(-1)
    same_loc = (idle_df.lat.round(3) == idle_df.lat.shift(-1).round(3)) & (idle_df.lon.round(3) == idle_df.lon.shift(-1).round(3))
    same_time = (idle_df.utc_time_start.shift(-1) - idle_df.utc_time_end).dt.seconds < 130
    
    return (same_bike & same_charge & same_loc & same_time)