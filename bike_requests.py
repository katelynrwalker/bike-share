import requests
import time
import pandas as pd

def single_query(link):
    '''
    Input: internet link to request json data from (string)
    Output: Pandas df with columns of data for each bike, also a column for datetime of current request
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
        return bike_data
    
link = 'https://sc.jumpbikes.com/opendata/free_bike_status.json'  ## enter bikeshare data link here

# get the bikeshare data from the internet and write to a blank file in csv format

bike_data = single_query(link)
with open('sac-bike-data.csv', mode='w+') as f:
    f.write(bike_data.to_csv())

# once a minute, get the bikeshare data from the internet and continue appending in csv format to same file as above

#while True:
for k in [1,2,3,4]:
    time.sleep(60)

    bike_data = single_query(link)
    with open('sac-bike-data.csv', mode='a') as f:
        f.write(bike_data.to_csv(header=False))
