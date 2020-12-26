from bs4 import BeautifulSoup
import operator
import pandas as pd
import requests


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
