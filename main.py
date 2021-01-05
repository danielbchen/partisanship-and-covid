from bs4 import BeautifulSoup
import datetime
import geopandas as gpd
from geopandas import GeoDataFrame
import io
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import numpy as np
import operator
import os
import pandas as pd
import requests
import statsmodels.formula.api as smf
import us
import zipfile


def main():
    '''
    Saves following files:

    1) Total votes by state for Clinton and Trump in 2016.
        (WEBSCRAPED VIA WIKIPEDIA.COM)
    2) Total votes by county for Clinton and Trump in 2016.
        (WEBSCRAPED VIA TOWNHALL.COM)
    3) County names and their corresponding FIPS codes.
        (WEBSCRAPED VIA USDA.COM)
    4) Reported daily number of Coronavirus cases by county.
        (ACCESSED VIA NYT GITHUB)
    5) Population estimates in 2019 by county.
        (ACCESSED VIA USDA)
    6) Population density based on 2014-2018 American Community Survey.
        (ACCESSED VIA CENSUS BUREAU)
    7) Final dataframe that merges all of the files mentioned above.
    8) Two subplots saved in a single .png showing:
        a) Daily change in Coronavirus cases grouped by states who voted for
           Clinton in 2016 and states who voted for Trump in 2016.
        b) Daily change in Coronavirus cases grouped by regions in the
           continential United States.
    9) A choropleth showing the Coronavirus infection rate by county.
    10) A choropleth showing how each county voted in 2016.
    11) A choropleth showing the population density of each county.
    12) A .txt file containing regression results where:
        Total Cases ~ Party Identification + Population Density
    13) A .txt file containing regression results where:
        Infection Rate ~ Party Identification
    '''

    print('Running script, please wait about two minutes!')

    votes = wiki_extractor()
    votes = wiki_cleaner(votes)
    votes = party_calculator(votes)

    county_votes = county_vote_extractor()
    fips = usda_extractor()
    cases = cases_loader()
    population = population_loader()
    density = density_loader()

    county_fips_combined = county_fips_merger(county_votes, fips)
    county_fips_combined = vote_margin_calculator(county_fips_combined)

    geo = geo_data_loader()
    geo = geo_data_cleaner(geo)

    df = data_merger(cases, votes, population, density,
                     county_fips_combined, geo)

    df = bin_creator(df)
    df = region_grouper(df)

    votes.to_csv('Votes by State in 2016.csv')
    county_votes.to_csv('Votes by County in 2016.csv')
    fips.to_csv('FIPS codes.csv')
    cases.to_csv('Reported Daily Coronavirus Cases.csv')
    population.to_csv('Poplation Estimates 2019.csv')
    density.to_csv('Population Density Estimates.csv')

    drop_cols = [
        'COUNTYNS',
        'AFFGEOID',
        'GEOID',
        'NAME',
        'LSAD',
        'ALAND',
        'AWATER',
        'GEOMETRY',
        'INFECTION_BINS',
        'DENSITY_BINS',
        'VOTE_BINS',
        'REGION'
    ]
    df.drop(drop_cols, 1).to_csv('Final Dataframe.csv', index=False)

    plotter(df)
    choropleth_infection(df)
    choropleth_vote(df)
    choropleth_density(df)

    run_ols(df)

    print('The files have been saved!')
    

def wiki_extractor():
    """Scrapes wikipedia table to return a dataframe with the Clinton versus
    Trump vote counts from 2016.
    """

    url = 'https://en.wikipedia.org/wiki/2016_United_States_presidential_election'

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')

    tables = soup.find_all('table', {'class': 'wikitable sortable'})
    election_table = tables[2]

    raw_links = []
    for link in election_table.find_all('a', href=True):
        raw_links.append(link['href'])

    states = []
    for link in raw_links:
        if ('#' not in link):
            states.append(link)

    td_items = election_table.find_all('td')
    td_text = [text.get_text() for text in td_items]

    clinton_vote_indexes = []
    for index, text in enumerate(td_text):
        if text[0].isupper():
            clinton_vote_indexes.append(index + 1)

    trump_vote_indexes = []
    for index, text in enumerate(td_text):
        if text[0].isupper():
            trump_vote_indexes.append(index + 4)

    clinton_votes = operator.itemgetter(*clinton_vote_indexes)(td_text) 
    trump_votes = operator.itemgetter(*trump_vote_indexes)(td_text)

    vote_share_dict = {
        'STATE': states,
        'CLINTON_VOTES': clinton_votes,
        'TRUMP_VOTES': trump_votes,
    }

    df = pd.DataFrame(vote_share_dict)

    return df


def wiki_cleaner(dataframe):
    """Extracts only the name of the state from hyperlinks in the State column,
    and cleans up vote counts to manipulatable numeric format.
    """

    df = dataframe.copy()

    df = df.replace(',', '', regex=True)
    cols = ['CLINTON_VOTES', 'TRUMP_VOTES']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')

    df['STATE'] = [text.split('in_')[-1] for text in df['STATE']]
    df = df[~df['STATE'].str.startswith('/')].reset_index().drop('index', 1)
    state_replacements = {
        'the_District_of_Columbia': 'DC',
        'Washington_(state)': 'Washington'
    }
    df['STATE'] = df['STATE'].replace(state_replacements)
    df['STATE'] = df['STATE'].str.replace('_', ' ')

    return df


def party_calculator(dataframe):
    """Creates new column based on scraped Wikipedia data determining if a
    given state is red or blue.
    """

    df = dataframe.copy()

    df['PARTY_ID'] = np.where(
        df['CLINTON_VOTES'] > df['TRUMP_VOTES'],
        'Democratic',
        'Republican'
    )

    return df


def get_states():
    """Returns a list of state abbreviations + District of Columbia."""

    fips_state_xwalk = us.states.mapping('fips', 'abbr')

    fips_state_xwalk = {fips: state for fips, state in fips_state_xwalk.items()
                            if fips is not None} 

    fips_state_xwalk = {int(fips): str(state) for fips, state in fips_state_xwalk.items()}

    fips_state_xwalk = dict(sorted(fips_state_xwalk.items()))

    exclusions = [60, 66, 69, 72, 78]
    fips_state_xwalk = {fips: state for fips, state in fips_state_xwalk.items()
                            if fips not in exclusions}

    states = list(fips_state_xwalk.values())

    return states


def county_vote_extractor():
    """Turns the raw html text from townhall.com into a dataframe containing
    vote counts by candidate by county. Cleans up number formatting and
    creates new column that will be used to join on FIPS codes.
    """

    def get_townhall_raw_contents():
        """Loops through townhall.com for each state and returns the raw
        html text on each page into a list.
        """

        states = get_states()

        raw_text = []
        for state in states:
            response = requests.get('https://townhall.com/election/2016/president/{}/county'.format(state))
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table', attrs={'class': 'table ec-table'})

            for table in tables:
                table_cells = table.find_all('td')

                for cell in table_cells:
                    cell_contents = cell.get_text()
                    raw_text.append(cell_contents)

        return raw_text

    raw_text = get_townhall_raw_contents()

    def county_names_retriever():
        """Extracts and cleans county names from the list containing the raw 
        html output.
        """

        county_names = [item for item in raw_text if item.startswith('\n')]
        county_names = [text.split('\n')[1] for text in county_names]

        return county_names

    def state_extractor():
        """Returns a list of states that correspond to each county."""

        states = get_states()

        counts = []
        for state in states:
            response = requests.get('https://townhall.com/election/2016/president/{}/county'.format(state))
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table', attrs={'class': 'table ec-table'})

            for table in tables:
                div_tags = table.find_all('div')
                counts.append(
                    sum(1 for div in div_tags if str(div).startswith('<div>'))
                )

        state_county_counts = dict(zip(states, counts))

        nested_states = [[state] * county_count for state, county_count in state_county_counts.items()]

        states_column = [state for sublist in nested_states for state in sublist]

        return states_column

    def vote_getter(candidate_name):
        """Stores the vote count from each county for a specified candidate
        into a list.
        """

        vote_indexes = []
        for index, text in enumerate(raw_text):
            if text == candidate_name:
                vote_indexes.append(index + 1)

        candidate_votes = operator.itemgetter(*vote_indexes)(raw_text)

        return candidate_votes

    df = pd.DataFrame(
        {
            'COUNTY': county_names_retriever(),
            'STATE': state_extractor(),
            'CLINTON_COUNTY_VOTES': vote_getter('Hillary Clinton'),
            'TRUMP_COUNTY_VOTES': vote_getter('Donald Trump'),
        }
    )

    cols = ['CLINTON_COUNTY_VOTES', 'TRUMP_COUNTY_VOTES']
    df[cols] = df[cols].replace(',', '', regex=True).astype(int)

    df['COUNTY'] = [name[:-3] if name.endswith('Co.') else name for name in df['COUNTY']]

    replacements = {
        'Sainte Genevieve': 'Ste. Genevieve',
        'Carson City': 'Carson',
        'Charles City': 'Charles',
        'Colonial Heights': 'Colonial Heights Cit',
        'James City': 'James'
    } 
    df['COUNTY'] = df['COUNTY'].replace(replacements)
    # Need to replace the following "cells" by their specific index locations.
    df.iat[1555, 0] = 'St Louis City'
    df.iat[2801, 0] = 'Bedford County'
    df.iat[2828, 0] = 'Fairfax City'
    df.iat[2829, 0] = 'Fairfax County'
    df.iat[2835, 0] = 'Franklin County'
    df.iat[2896, 0] = 'Richmond County'
    df.iat[2898, 0] = 'Roanoke County'

    df['MATCH_ID'] = df['COUNTY'] + df['STATE']
    df['MATCH_ID'] = [id.lower() for id in df['MATCH_ID']]
    df['MATCH_ID'] = (df['MATCH_ID'].str.replace('.', '')
                                    .str.replace(' ', '')
                                    .str.replace("'", ''))

    return df


def usda_extractor():
    """Turns the raw data scraped from the USDA into a dataframe containing
    FIPS codes, counties, and state abbreviations.
    """

    raw_info = get_usda_raw_contents()

    df = pd.DataFrame(
        {
            'FIPS': fips_column_creator('01001', '56045', 1),
            'COUNTY': fips_column_creator('Autauga', 'Weston', 1),
            'STATE': fips_column_creator('AL', 'AS', 0),
        }
    )

    df['COUNTY'] = [name[:-4] if name.endswith('City') else name for name in df['COUNTY']]

    df.at[1593, 'COUNTY'] = 'St Louis City'
    df.at[2826, 'COUNTY'] = 'Bedford County'
    df.at[2923, 'COUNTY'] = 'Fairfax City'
    df.at[2845, 'COUNTY'] = 'Fairfax County'
    df.at[2849, 'COUNTY'] = 'Franklin County'
    df.at[2892, 'COUNTY'] = 'Richmond County'
    df.at[2893, 'COUNTY'] = 'Roanoke County'

    df['MATCH_ID'] = df['COUNTY'] + df['STATE']
    df['MATCH_ID'] = [id.lower() for id in df['MATCH_ID']]
    df['MATCH_ID'] = (df['MATCH_ID'].str.replace(' ', '')
                                    .str.replace('.', ''))

    df = df[['FIPS', 'MATCH_ID']]

    return df


def get_usda_raw_contents():
    """Scrapes the USDA website and returns its raw html contents as a list of
    text.
    """

    fips_url = 'https://www.nrcs.usda.gov/wps/portal/nrcs/detail/national/home/?cid=nrcs143_013697'

    response = requests.get(fips_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    cells = soup.find_all('td')
    raw_info = [cell.get_text() for cell in cells]

    return raw_info


def fips_column_creator(first, last, offset):
    """Using data from USDA, this function dentifies the index positions of all
    FIPS codes, county names, and state abbreviations and extracts the data
    for each of the aforementioned variables into a list.
    """

    raw_info = get_usda_raw_contents()

    first_item = raw_info.index(first)
    last_item = raw_info.index(last) + offset
    items = raw_info[first_item:last_item:3]

    return items


def county_fips_merger(dataframe1, dataframe2):
    """Merges FIPS code data from USDA with votes by county data from
    townhall.com.
    """

    df = pd.merge(dataframe1, dataframe2, on='MATCH_ID')

    df.iat[223, 5] = '08017'
    df.iat[1166, 5] = '24510'
    df.iat[1167, 5] = '24005'
    df.iat[2383, 5] = '46111'
    df.iat[2385, 5] = '46117'

    df = df[df['COUNTY'] != 'Alaska']

    df = df[['FIPS', 'CLINTON_COUNTY_VOTES', 'TRUMP_COUNTY_VOTES']]
    df.columns = ['COUNTYFP', 'CLINTON_COUNTY_VOTES', 'TRUMP_COUNTY_VOTES']

    df['COUNTYFP'] = df['COUNTYFP'].astype(int)

    # Need to add county oglala lakota manually because it's not included in the usda website
    oglala_lakota = {
        'COUNTYFP': 46102,
        'CLINTON_COUNTY_VOTES': 2504,
        'TRUMP_COUNTY_VOTES': 241
    }
    df = df.append(oglala_lakota, ignore_index=True)

    return df


def vote_margin_calculator(dataframe):
    """Creates new column that reports the Clinton vote margin
    as a percentage difference from Trump's vote share.
    """

    df = dataframe.copy()

    df['CLINTON_COUNTY_PCT'] = df['CLINTON_COUNTY_VOTES'] / (df['CLINTON_COUNTY_VOTES'] + df['TRUMP_COUNTY_VOTES'])

    df['TRUMP_COUNTY_PCT'] = df['TRUMP_COUNTY_VOTES'] / (df['CLINTON_COUNTY_VOTES'] + df['TRUMP_COUNTY_VOTES'])

    df['COUNTY_PCT_DIFF'] = df['CLINTON_COUNTY_PCT'] - df['TRUMP_COUNTY_PCT']

    df = df[['COUNTYFP', 'COUNTY_PCT_DIFF']]

    return df


def cases_loader():
    """Stores case and death csv data from NYT's respository into dataframe."""

    cases_url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'
    cases = pd.read_csv(cases_url)

    cases.columns = ['DATE', 'COUNTY', 'STATE', 'COUNTYFP', 'CASES', 'DEATHS']

    return cases


def population_loader():
    """Returns a dataframe with population estimates from 2019 in each US 
    County using USDA data.
    """

    url = 'https://www.ers.usda.gov/webdocs/DataFiles/48747/PopulationEstimates.xls?v=6825.4'

    cols = ['FIPStxt', 'POP_ESTIMATE_2019']
    df = pd.read_excel(
        url,
        skiprows=range(0, 2),
        usecols=cols,
    )

    df.columns = ['COUNTYFP', 'POP_EST_2019']

    return df


def density_loader():
    """Loads population density by county from the U.S. Census into a 
    dataframe.
    """

    density_url = 'https://opendata.arcgis.com/datasets/21843f238cbb46b08615fc53e19e0daf_1.geojson'

    df = gpd.read_file(density_url)

    df = df[['GEOID', 'B01001_calc_PopDensity']]

    df['GEOID'] = df['GEOID'].astype(float)
    df.columns = ['COUNTYFP', 'POP_DENSITY']

    return df


def get_shape_files():
    """Checks directory for necessary shape files. If files are not there, then
    they are downloaded from the Census. Returns the path to the .dbf file
    that is read by GeoPandas. If files are there, nothing is downloaded and
    only a statement saying files exist is returned.
    """

    path = os.path.dirname(os.path.abspath("__file__"))

    fnames = [
        'cb_2018_us_county_500k.cpg',
        'cb_2018_us_county_500k.prj',
        'cb_2018_us_county_500k.dbf',
        'cb_2018_us_county_500k.shx',
        'cb_2018_us_county_500k.shp',
        'cb_2018_us_county_500k.shp.iso.xml',
        'cb_2018_us_county_500k.shp.ea.iso.xml'
    ]
    booleans = [os.path.exists(fname) for fname in fnames]

    url = 'https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip'

    if False in booleans:
        response = requests.get(url)
        zip_folder = zipfile.ZipFile(io.BytesIO(response.content))
        zip_folder.extractall(path=path)
        file_endings = ['dbf', 'prj', 'shp', 'shx']
        files = [file for file in zip_folder.namelist() if file.endswith(tuple(file_endings))]
        dbf, prj, shp, shx = [file for file in files]
        shp_path = os.path.join(path, shp)
    else:
        shp_path = 'Files already exist!'

    return shp_path


def geo_data_loader():
    """Uses the shape files are either downloaded or already exist on the machine
    to return a dataframe containing all the info required to create a map.
    """

    path = os.path.dirname(os.path.abspath("__file__"))
    file_path = get_shape_files()

    if file_path == 'Files already exist!':
        fname = os.path.join(path, 'cb_2018_us_county_500k.dbf')
        df = gpd.read_file(fname)
    else:
        df = gpd.read_file(file_path)

    return df


def geo_data_cleaner(dataframe):
    """Cleans up the GeoDataFrame so that it can be merged with the vote data
    and the COVID-19 case data.
    """

    df = dataframe.copy()

    drop_counties = ['02', '15', '72']
    df = df[~df['STATEFP'].isin(drop_counties)]

    projection = '+proj=laea +lat_0=30 +lon_0=-95'
    df = df.to_crs(projection)

    df['COUNTYFP'] = df['STATEFP'] + df['COUNTYFP']

    df = df[[
        'COUNTYFP',
        'COUNTYNS',
        'AFFGEOID',
        'GEOID',
        'NAME',
        'LSAD',
        'ALAND',
        'AWATER',
        'geometry'
    ]]
    df.columns = [col.upper() for col in df.columns.values.tolist()]
    df['COUNTYFP'] = df['COUNTYFP'].astype(int)

    return df


def data_merger(dataframe1, dataframe2, dataframe3, dataframe4, dataframe5,
                dataframe6):
    """Merges all datasets, keeps relevant columns, and formats fips codes
    correctly.
    """

    df = (dataframe1.merge(dataframe2, on='STATE')
                    .merge(dataframe3, on='COUNTYFP', how='inner')
                    .merge(dataframe4, on='COUNTYFP', how='inner')
                    .merge(dataframe5, on='COUNTYFP', how='inner')
                    .merge(dataframe6, on='COUNTYFP', how='inner'))

    df = df.drop(['CLINTON_VOTES', 'TRUMP_VOTES'], 1)

    df['DEATH_RATE'] = df['DEATHS'] / df['CASES']

    df['COUNTYFP'] = df['COUNTYFP'].astype(str)
    df['COUNTYFP'] = ['0' + fips if len(fips) == 6 else fips for fips in df['COUNTYFP']]
    df['COUNTYFP'] = [fips[:-2] for fips in df['COUNTYFP']]

    df['INFECTION_RATE'] = (df['CASES'] / df['POP_EST_2019']) * 100

    df = df[df['DATE'] <= '2020-12-01']

    return df


def bin_creator(dataframe):
    """Creates bins for continuous variables that will be used for 
    choropleths.
    """

    df = dataframe.copy()

    infection_conditions = [
        df['INFECTION_RATE'] < 1,
        ((df['INFECTION_RATE'] >= 1) & (df['INFECTION_RATE'] < 2)),
        ((df['INFECTION_RATE'] >= 2) & (df['INFECTION_RATE'] < 3)),
        ((df['INFECTION_RATE'] >= 3) & (df['INFECTION_RATE'] < 4)),
        ((df['INFECTION_RATE'] >= 4) & (df['INFECTION_RATE'] < 5)),
        df['INFECTION_RATE'] >= 5
    ]
    infection_groups = [
        'Less than 1',
        '1 to 2',
        '2 to 3',
        '3 to 4',
        '4 to 5',
        '5 +'
    ]
    df['INFECTION_BINS'] = np.select(infection_conditions, infection_groups)

    density_conditions = [
        df['POP_DENSITY'] < 1,
        ((df['POP_DENSITY'] >= 1) & (df['POP_DENSITY'] < 20)),
        ((df['POP_DENSITY'] >= 20) & (df['POP_DENSITY'] < 80)),
        ((df['POP_DENSITY'] >= 80) & (df['POP_DENSITY'] < 250)),
        ((df['POP_DENSITY'] >= 250) & (df['POP_DENSITY'] < 500)),
        df['POP_DENSITY'] >= 500
    ]
    density_groups = [
        'Less than 1',
        '1 to 20',
        '20 to 80',
        '80 to 250',
        '250 to 500',
        '500 +'
    ]
    df['DENSITY_BINS'] = np.select(density_conditions, density_groups)

    vote_conditions = [
        ((df['COUNTY_PCT_DIFF'] >= -.99) & (df['COUNTY_PCT_DIFF'] < -.66)),
        ((df['COUNTY_PCT_DIFF'] >= -.66) & (df['COUNTY_PCT_DIFF'] < -.33)),
        ((df['COUNTY_PCT_DIFF'] >= -.33) & (df['COUNTY_PCT_DIFF'] < 0)),
        ((df['COUNTY_PCT_DIFF'] >= 0) & (df['COUNTY_PCT_DIFF'] < .33)),
        ((df['COUNTY_PCT_DIFF'] >= .33) & (df['COUNTY_PCT_DIFF'] < .66)),
        ((df['COUNTY_PCT_DIFF'] >= .66) & (df['COUNTY_PCT_DIFF'] < .99))
    ]
    vote_groups = [
        '-0.99 to -0.66',
        '-0.66 to -0.33',
        '-0.33 to 0',
        '0 to 0.33',
        '0.33 to 0.66',
        '0.66 to 0.99'
    ]
    df['VOTE_BINS'] = np.select(vote_conditions, vote_groups)

    return df


def region_grouper(dataframe):
    """Creates a new column that puts states into regional bins."""

    df = dataframe.copy()

    north_east_regions = [
        'Connecticut',
        'Maine',
        'Massachusetts',
        'New Hampshire',
        'New Jersey',
        'New York',
        'Pennsylvania',
        'Rhode Island',
        'Vermont'
    ]

    southern_regions = [
        'Alabama',
        'Arkansas',
        'Delaware',
        'Florida',
        'Georgia',
        'Kentucky',
        'Louisiana',
        'Maryland',
        'Mississippi',
        'North Carolina',
        'Oklahoma',
        'South Carolina',
        'Tennessee',
        'Texas',
        'Virginia',
        'West Virginia'
    ]

    midwest_regions = [
        'Illinois',
        'Indiana',
        'Iowa',
        'Kansas',
        'Michigan',
        'Minnesota',
        'Missouri',
        'Nebraska',
        'North Dakota',
        'Ohio',
        'South Dakota',
        'Wisconsin'
    ]

    western_regions = [
        'Alaska',
        'Arizona',
        'California',
        'Colorado',
        'Hawaii',
        'Idaho',
        'Montana',
        'Nevada',
        'New Mexico',
        'Oregon',
        'Utah',
        'Washington',
        'Wyoming'
    ]

    regions = [
        north_east_regions,
        southern_regions,
        midwest_regions,
        western_regions
    ]

    region_conditions = [df['STATE'].isin(region) for region in regions]
    region_groups = ['Northeast', 'South', 'Midwest', 'West']

    df['REGION'] = np.select(region_conditions, region_groups)

    return df


def default_graph(ax):
    """Creates standard format for all subplots."""

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(2)

    ax.yaxis.set_ticks_position('left')
    ax.xaxis.set_ticks_position('bottom')
    ax.tick_params(axis=u'both', which=u'both', length=0)

    ax.margins(x=0, y=0)

    return ax


def plotter(dataframe):
    """Creates two plots. First, the daily change in Coronavirus cases over time
    between states who voted for Clinton in 2016 and states who voted for
    Trump in 2016. Second, the daily change in Coronavirus cases over time
    in different regions of the United States.
    """

    df = dataframe.copy()

    df = df[df['DATE'] <= '2020-12-01']

    df['DATE'] = pd.to_datetime(df['DATE'])
    grouped_df = (df.groupby(['DATE', 'PARTY_ID'])
                    .agg({'CASES': 'sum', 'DEATH_RATE': 'mean'})
                    .reset_index())

    """Calculates daily new cases for first subplot."""
    grouped_cases = (grouped_df.pivot(index='DATE',
                                      columns='PARTY_ID',
                                      values='CASES')
                     .reset_index())
    grouped_cases['DATE'] = pd.to_datetime(grouped_cases['DATE'])
    grouped_cases['DEM_NEW_CASES'] = grouped_cases['Democratic'].diff(1)
    grouped_cases['GOP_NEW_CASES'] = grouped_cases['Republican'].diff(1)

    """Calculates new daily cases by region for second subplot."""
    regions_df = (df.groupby(['DATE', 'REGION'])
                    .agg({'CASES': 'sum'})
                    .reset_index()
                    .pivot(index='DATE',
                           columns='REGION',
                           values='CASES')
                    .reset_index())

    regions_df['DATE'] = pd.to_datetime(regions_df['DATE'])
    regions_df['MW_NEW_CASES'] = regions_df['Midwest'].diff(1)
    regions_df['NE_NEW_CASES'] = regions_df['Northeast'].diff(1)
    regions_df['S_NEW_CASES'] = regions_df['South'].diff(1)
    regions_df['W_NEW_CASES'] = regions_df['West'].diff(1)

    """Plots grouped dataframes."""
    fig, axs = plt.subplots(2, 1, figsize=(15, 10))

    plt.rcParams['font.family'] = 'arial'

    axs = [default_graph(ax) for ax in axs]

    """Plot first subplot."""
    axs[0].fill_between(grouped_cases['DATE'],
                        grouped_cases['DEM_NEW_CASES'],
                        color='skyblue',
                        alpha=0.4)
    axs[0].plot(grouped_cases['DATE'],
                grouped_cases['DEM_NEW_CASES'],
                color='blue',
                alpha=.6,
                linewidth=2,
                label='Voted Clinton in 2016')
    axs[0].fill_between(grouped_cases['DATE'],
                        grouped_cases['GOP_NEW_CASES'],
                        color='lightpink',
                        alpha=0.4)
    axs[0].plot(grouped_cases['DATE'],
                grouped_cases['GOP_NEW_CASES'],
                color='red',
                alpha=.6,
                linewidth=2,
                label='Voted Trump in 2016')

    axs[0].xaxis.set_ticklabels([], minor=True)
    axs[0].xaxis.set_ticklabels([], minor=False)

    axs[0].yaxis.get_offset_text().set_visible(False)

    flag_height_tall = 121000
    flag_height_short = 110000

    axs[0].axvline(datetime.datetime(2020, 2, 3), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 2, 4),
                flag_height_tall,
                'US Declares Public \nHealth Emergency',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 3, 13), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 3, 14),
                flag_height_tall,
                'Trump Declares \nNational Emergency',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 5, 26), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 5, 27),
                flag_height_tall,
                'George Floyd \nProtests Begin',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 7, 4), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 7, 5),
                125500,
                'Fourth of July',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 9, 7), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 9, 8),
                flag_height_tall,
                ' Labor Day \nWeekend',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 10, 3), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 10, 4),
                flag_height_short,
                'White House \nCeremony \nfor Amy \nBarrett',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 10, 31), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 11, 1),
                127000,
                'Halloween (10/31) and \nElection Day \n(11/03)',
                horizontalalignment='left',
                style='italic',
                fontsize=9)
    axs[0].axvline(datetime.datetime(2020, 11, 26), color='k', linestyle=':')
    axs[0].text(datetime.datetime(2020, 11, 28),
                125500,
                'Thanksgiving',
                horizontalalignment='left',
                style='italic',
                fontsize=9)

    axs[0].set_xlim(['2020-01-21', '2020-12-01'])

    axs[0].spines['bottom'].set_linewidth(2)

    axs[0].set_title('Cases by 2016 Presidential Vote \n\n')

    axs[0].legend(loc=(1.03, .5), framealpha=0)

    """Plot second subplot."""
    axs[1] = plt.gca()
    axs[1].fill_between(regions_df['DATE'],
                        regions_df['MW_NEW_CASES'],
                        color='#66c2a5',
                        alpha=0.4)
    axs[1].plot(regions_df['DATE'],
                regions_df['MW_NEW_CASES'],
                color='#47887e',
                alpha=.6,
                linewidth=2,
                label='Midwest')
    axs[1].fill_between(regions_df['DATE'],
                        regions_df['NE_NEW_CASES'],
                        color='#ffc9b1',
                        alpha=0.4)
    axs[1].plot(regions_df['DATE'],
                regions_df['NE_NEW_CASES'],
                color='#fc8d62',
                alpha=.6,
                linewidth=2,
                label='Northeast')
    axs[1].fill_between(regions_df['DATE'],
                        regions_df['S_NEW_CASES'],
                        color='#bfdffb',
                        alpha=0.4)
    axs[1].plot(regions_df['DATE'],
                regions_df['S_NEW_CASES'],
                color='#8da0cb',
                alpha=.6,
                linewidth=2,
                label='South')
    axs[1].fill_between(regions_df['DATE'],
                        regions_df['W_NEW_CASES'],
                        color='#ffe5fb',
                        alpha=0.4)
    axs[1].plot(regions_df['DATE'],
                regions_df['W_NEW_CASES'],
                color='#e78ac3',
                alpha=.6,
                linewidth=2,
                label='West')

    """Add vertical flags."""
    axs[1].axvline(datetime.datetime(2020, 2, 3), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 3, 13), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 5, 26), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 7, 4), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 9, 7), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 10, 3), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 10, 31), color='k', linestyle=':')
    axs[1].axvline(datetime.datetime(2020, 11, 26), color='k', linestyle=':')

    axs[1].axhline(0, color='k', linestyle='-')
    axs[1].spines['bottom'].set_visible(False)

    axs[1].set_xlim(['2020-01-21', '2020-12-01'])
    xfmt = mdates.DateFormatter('%b')
    months = mdates.MonthLocator()
    axs[1].xaxis.set_major_locator(months)
    axs[1].xaxis.set_major_formatter(xfmt)

    axs[1].set_title('Cases by Geographic Region \n')

    axs[1].legend(loc=(1.03, .5), framealpha=0)

    fig.suptitle('Tracking Coronavirus Cases in the United States',
                 fontsize=15, fontweight='bold',
                 x=.445, y=.97)
    fig.text(0.08, 0.5,
             'Change in Reported Number of Cases',
             ha="center", va="center", rotation=90)

    fig.subplots_adjust(right=.78)

    #plt.show;
    plt.savefig('Lineplots.png', dpi=800, facecolor='white')
    plt.close()


def df_to_gdf(dataframe):
    """Converts a normal pandas dataframe into a geopandas dataframe."""

    df = dataframe.copy()

    df = GeoDataFrame(
        df,
        crs='+proj=laea +lat_0=30 +lon_0=-95',
        geometry=df['GEOMETRY']
    )

    return df


def label_creator(dictionary):
    """Returns the keys of a dictionary in reverse order.
    Helper function to create categorial labels in GeoPandas choropleths.
    """

    labels = [key for key, value in dictionary.items()]
    labels = labels[::-1]

    return labels


def choropleth_plotter(dataframe, column, cmap, plot_title, legend_title,
                       legend_labels, filename):
    """Creates choropleth and saves as a .png."""

    df = dataframe.copy()

    fig, ax = plt.subplots(figsize=(17, 10))
    df.plot(ax=ax,
            column=column,
            linewidth=0.5,
            edgecolor='black',
            categorical=True,
            legend=True,
            cmap=cmap,
            legend_kwds=dict(title=legend_title,
                             loc='upper left',
                             bbox_to_anchor=(1, 1),
                             frameon=False))

    ax.axis('off')
    ax.set_title(plot_title, fontsize=16, fontweight='bold')

    leg = ax.get_legend()
    for text, label in zip(leg.get_texts(), legend_labels):
        text.set_text(label)

    #plt.show;
    plt.savefig(filename, dpi=800, facecolor='white')
    plt.close()


def choropleth_infection(dataframe):
    """Saves a choropleth of the infection rate across the continential U.S."""

    df = dataframe.copy()
    df = df[df['DATE'] == '2020-12-01']
    df = df_to_gdf(df)

    infection_rankings = {
        '5 +': 5,
        '4 to 5': 4,
        '3 to 4': 3,
        '2 to 3': 2,
        '1 to 2': 1,
        'Less than 1': 0
    }
    infection_labels = label_creator(infection_rankings)

    df['INFECTION_RANKINGS'] = df['INFECTION_BINS'].map(infection_rankings)

    choropleth_plotter(dataframe=df,
                       column='INFECTION_RANKINGS',
                       cmap='RdBu_r',
                       plot_title='COVID-19 Infection Rate as of December 1, 2020',
                       legend_title='Infection Rate (%)',
                       legend_labels=infection_labels,
                       filename='Infection Choropleth.png')


def choropleth_density(dataframe):
    """Saves a choropleth of the population density across the continential 
    U.S.
    """

    df = dataframe.copy()
    df = df[df['DATE'] == '2020-12-01']
    df = df_to_gdf(df)

    density_rankings = {
        '500 +': 5,
        '250 to 500': 4,
        '80 to 250': 3,
        '20 to 80': 2,
        '1 to 20': 1,
        'Less than 1': 0
    }
    density_labels = label_creator(density_rankings)

    df['DENSITY_RANKINGS'] = df['DENSITY_BINS'].map(density_rankings)

    choropleth_plotter(dataframe=df,
                       column='DENSITY_RANKINGS',
                       cmap='RdBu_r',
                       plot_title='Population Density 2019',
                       legend_title='People per Square KM',
                       legend_labels=density_labels,
                       filename='Density Choropleth.png')


def choropleth_vote(dataframe):
    """Saves a choropleth of 2016 Clinton Vote Margin across the continential 
    U.S.
    """

    df = dataframe.copy()
    df = df[df['DATE'] == '2020-12-01']
    df = df_to_gdf(df)

    vote_rankings = {
        '0.66 to 0.99': 5,
        '0.33 to 0.66': 4,
        '0 to 0.33': 3,
        '-0.33 to 0': 2,
        '-0.66 to -0.33': 1,
        '-0.99 to -0.66': 0
    }
    vote_labels = label_creator(vote_rankings)

    df['VOTE_RANKINGS'] = df['VOTE_BINS'].map(vote_rankings)

    leg_title = ('         Clinton 2016 Margin'
                 '\n(Percent Difference vs. Trump)')

    choropleth_plotter(dataframe=df,
                       column='VOTE_RANKINGS',
                       cmap='RdBu',
                       plot_title='2016 Clinton Vote Margin',
                       legend_title=leg_title,
                       legend_labels=vote_labels,
                       filename='Vote Choropleth.png')


def run_ols(dataframe):
    """Takes dataframe, runs two regressions, and writes each regression
    output into a .txt file.
    """

    df = dataframe.copy()

    df = df[df['DATE'] == '2020-12-01']
    df['BINARY_PARTY_ID'] = [1 if pct > 0 else 0 for pct in df['COUNTY_PCT_DIFF']]

    cases_formula = 'CASES ~ BINARY_PARTY_ID + POP_EST_2019'
    rate_formula = 'INFECTION_RATE ~ BINARY_PARTY_ID'
    formulas = [cases_formula, rate_formula]

    models = [smf.ols(formula=formula, data=df).fit() for formula in formulas]
    summaries = [model.summary() for model in models]

    output_names = ['Total Cases Regression', 'Infection Rate Regression']

    ols_dict = dict(zip(output_names, summaries))

    for name, output in ols_dict.items():
        with open('{}.txt'.format(name), 'w') as file:
            file.write(output.as_text())


if __name__ == '__main__':
    main()
