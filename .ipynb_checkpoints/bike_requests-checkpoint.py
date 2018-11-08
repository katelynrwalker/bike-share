import requests
import time
import pandas as pd

def single_query(link):
    '''
    Input: internet link to request json data from (string)
    Returns:
        Pandas df with columns of data for each bike, also a column for datetime of current request
        time before next update of API
    '''
    response = requests.get(link)
    if response.status_code != 200:
        print(time.time())
        print('WARNING', response.status_code)
    else:
        contents = response.json()
        
        # convert the bikeshare data into a pandas df, include a column for the datetime of the current call
        if 'station' in link:
            bike_data = pd.DataFrame(contents['data']['stations'])
        else:
            bike_data = pd.DataFrame(contents['data']['bikes'])
        bike_data['datetime'] = contents['last_updated']
        bike_data['update_time'] = contents['ttl']
        return bike_data

    
def get_and_write_data(link, filename):
    '''
    Gets bikeshare data from link and appends it to a csv in filename.
    
    Inputs:
        link: internet link to request json data from (string)
        filename: file to append the csv data to (string)
    
    Returns: 
        None (function writes data to a csv)
    '''

    bike_data = single_query(link)
    with open(filename, mode='a') as f:
        f.write(bike_data.to_csv(header=False))

    
if __name__ == '__main__':
    links = [
        'https://sc.jumpbikes.com/opendata/free_bike_status.json',
        'https://sf.jumpbikes.com/opendata/free_bike_status.json',
        'https://sac.jumpbikes.com/opendata/free_bike_status.json',
        'https://sc.jumpbikes.com/opendata/station_status.json',
        'https://sf.jumpbikes.com/opendata/station_status.json',
        'https://sac.jumpbikes.com/opendata/station_status.json'
        ]
    
    filenames = [
        'sc-bike-data_1031.csv',
        'sf-bike-data_1031.csv',
        'sac-bike-data_1031.csv',
        'sc-bike-stations_1031.csv',
        'sf-bike-stations_1031.csv',
        'sac-bike-stations_1031.csv'
        ]
    

    # first query: get the bikeshare data from the internet and write to a blank file in csv format

    for link, filename in zip(links, filenames):
        bike_data = single_query(link)
        with open(filename, mode='w+') as f:
            f.write(bike_data.to_csv())
            
    # run an infinite loop to get continued data from API
    #Keyborad interrupt (ctrl+c to stop)

    while True:
        for link, filename in zip(links, filenames):
            get_and_write_data(link, filename)
        time.sleep(60)



