import pandas as pd

def import_and_clean_data(filename):
    '''
    Imports a csv file, 
    converts it to a pandas dataframe, 
    drops unneeded columns,
    converts battery level to an int, 
    and creates utc and local time columns with datetime objects
    
    Input: name of file, in csv format
    Output: pandas dataframe
    '''
    raw = pd.read_csv("all-sc-bike-data-1101.csv")
    
    raw.drop(['is_disabled', 'is_reserved', 'update_time'], axis = 1, inplace = True)
    raw['jump_ebike_battery_level'] = raw['jump_ebike_battery_level'].str.strip('%').astype(int)
    
    raw['utc_time'] = pd.to_datetime(raw['datetime'], unit='s')
    raw['utc_time'] = raw['utc_time'].dt.tz_localize('UTC')
    raw['local_time'] = raw['utc_time'].dt.tz_convert('America/Los_Angeles')
    
    return raw

