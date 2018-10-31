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
        bike_data = pd.DataFrame(contents['data']['bikes'])
        bike_data['datetime'] = contents['last_updated']
        bike_data['update_time'] = contents['ttl']
        return bike_data, contents['ttl']

    
def get_and_write_data(link, filename)
    '''
    Gets bikeshare data from link and appends it to a csv in filename.
    
    Inputs:
        link: internet link to request json data from (string)
        filename: file to append the csv data to (string)
    
    Returns: 
        sleep_time: time to wait between requests (int)
        Also writes data to a csv
    '''

        bike_data, sleep_time = single_query(link)
        with open(filename, mode='a') as f:
            f.write(bike_data.to_csv(header=False))
        return sleep_time

    
if __name__ == '__main__':
    link = 'https://sc.jumpbikes.com/opendata/free_bike_status.json'
    filename = 'sac-bike-data.csv'

    # first query: get the bikeshare data from the internet and write to a blank file in csv format

    bike_data = single_query(link)
    with open(filename, mode='w+') as f:
        f.write(bike_data.to_csv())

    # run an infinite loop to get continued data from API

    while True:
            sleep_time = get_and_write_data
            time.sleep(sleep_time)



