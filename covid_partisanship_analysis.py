from bs4 import BeautifulSoup
import numpy as np
import operator
import pandas as pd
import requests
import us


def wiki_extractor():
    '''
    Scrapes wikipedia table to return a dataframe with the Clinton versus
    Trump vote counts from 2016.
    '''

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
    '''
    Extracts only the name of the state from hyperlinks in the State column,
    and cleans up vote counts to manipulatable numeric format.
    '''

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
    '''
    Creates new column based on scraped Wikipedia data determining if a
    given state is red or blue.
    '''

    df = dataframe.copy()

    df['PARTY_ID'] = np.where(
        df['CLINTON_VOTES'] > df['TRUMP_VOTES'],
        'Democratic',
        'Republican'
    )

    return df


def get_states():
    '''
    Returns a list of state abbreviations + District of Columbia.
    '''

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
    '''
    Turns the raw html text from townhall.com into a dataframe containing
    vote counts by candidate by county. Cleans up number formatting and
    creates new column that will be used to join on FIPS codes.
    '''

    def get_townhall_raw_contents():
        '''
        Loops through townhall.com for each state and returns the raw
        html text on each page into a list.
        '''

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
        '''
        Extracts and cleans county names from the list containing the raw html
        output.
        '''

        county_names = [item for item in raw_text if item.startswith('\n')]
        county_names = [text.split('\n')[1] for text in county_names]

        return county_names

    def state_extractor():
        '''
        Returns a list of states that correspond to each county.
        '''

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
        '''
        Stores the vote count from each county for a specified candidate
        into a list.
        '''

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
    '''
    Turns the raw data scraped from the USDA into a dataframe containing
    FIPS codes, counties, and state abbreviations.
    '''

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
    '''
    Scrapes the USDA website and returns its raw html contents as a list of
    text.
    '''

    fips_url = 'https://www.nrcs.usda.gov/wps/portal/nrcs/detail/national/home/?cid=nrcs143_013697'

    response = requests.get(fips_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    cells = soup.find_all('td')
    raw_info = [cell.get_text() for cell in cells]

    return raw_info


def fips_column_creator(first, last, offset):
    '''
    Using data from USDA, this function dentifies the index positions of all
    FIPS codes, county names, and state abbreviations and extracts the data
    for each of the aforementioned variables into a list.
    '''

    raw_info = get_usda_raw_contents()

    first_item = raw_info.index(first)
    last_item = raw_info.index(last) + offset
    items = raw_info[first_item:last_item:3]

    return items


def county_fips_merger(dataframe1, dataframe2):
    '''
    Merges FIPS code data from USDA with votes by county data from
    townhall.com.
    '''

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
    '''
    Creates new column that reports the Clinton vote margin
    as a percentage difference from Trump's vote share.
    '''

    df = dataframe.copy()

    df['CLINTON_COUNTY_PCT'] = df['CLINTON_COUNTY_VOTES'] / (df['CLINTON_COUNTY_VOTES'] + df['TRUMP_COUNTY_VOTES'])

    df['TRUMP_COUNTY_PCT'] = df['TRUMP_COUNTY_VOTES'] / (df['CLINTON_COUNTY_VOTES'] + df['TRUMP_COUNTY_VOTES'])

    df['COUNTY_PCT_DIFF'] = df['CLINTON_COUNTY_PCT'] - df['TRUMP_COUNTY_PCT']

    df = df[['COUNTYFP', 'COUNTY_PCT_DIFF']]

    return df


def cases_loader():
    '''
    Stores case and death csv data from NYT's respository into dataframe.
    '''

    cases_url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'
    cases = pd.read_csv(cases_url)

    cases.columns = ['DATE', 'COUNTY', 'STATE', 'COUNTYFP', 'CASES', 'DEATHS']

    return cases


def population_loader():
    '''
    Returns a dataframe with population estimates from 2019 in each US County
    using USDA data.
    '''

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
    '''
    Loads population density by county from the U.S. Census into a dataframe.
    '''

    density_url = 'https://opendata.arcgis.com/datasets/21843f238cbb46b08615fc53e19e0daf_1.geojson'

    df = gpd.read_file(density_url)

    df = df[['GEOID', 'B01001_calc_PopDensity']]

    df['GEOID'] = df['GEOID'].astype(float)
    df.columns = ['COUNTYFP', 'POP_DENSITY']

    return df
