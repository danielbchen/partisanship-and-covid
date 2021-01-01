# Analysis of Political Partisanship and the Coronavirus in the United States

### 1. Essential Question

Hyper-partisanship has inevitably invaded public health in the United States. While Coronavirus cases continue to surge across the country with no end in sight, party loyalty has divided the nation into those who trust public health experts and those who follow the advice of party leaders.

With this in mind, I seek to answer: What affect, if any, does party identification have on Coronavirus cases throughout the United States? In general, it appears that Democrats are relatively more likely to follow public health guidelines while Republicans listen to elected officials who downplay the severity of the virus. Using data primarily from the New York Times and 2016 election data, I am interested in finding out whether there exists a true (versus perceived) impact on public health as it relates to COVID-19 from being either a Democrat or a Republican.

To answer this question I utilize data from the United States 2016 Presidential Election as a proxy for political partisanship. I use data from the 2016 election for two reasons. First, the data was easily retrieviable programmatically using the [BeautifulSoup library](https://www.crummy.com/software/BeautifulSoup/bs4/doc/). Second, I began writing this script in November 2020 for my final project in my Data and Programming class while a graduate student at the University of Chicago Harris School of Public Policy, and the results from the 2020 election had not yet been verified. Georgia and Wisconsion, for example, both recounted ballots. 

The model is far from perfect, and I walk through limitations at the end of this README. 

### 2. Outline of the Python Script

The diagram below (original file found [here](https://github.com/danielbchen/partisanship-and-covid/blob/main/Code%20Diagram1000.png)) presents a visual representation of the [Python script](https://github.com/danielbchen/partisanship-and-covid/blob/main/covid_partisanship_analysis.py). In short, I scrape [statewide election results from Wikipedia](https://en.wikipedia.org/wiki/2016_United_States_presidential_election/), [county level election results from Townhall](https://townhall.com/election/2016/president/), and [county FIPS codes from the USDA](https://www.nrcs.usda.gov/wps/portal/nrcs/detail/national/home/?cid=nrcs143_013697). The New York Times releases daily updated counts of COVID-19 cases by county which can be retreived from their [repository](https://github.com/nytimes/covid-19-data), and finally, I download population and density estimates alongside shape files (to create choropleths) from the [US Census](https://www.census.gov).

All data is merged into a dataframe which is then used to create two subplots tracking the daily change in reported number of Coronavirus cases across the country, three choropleths showing the infection rate by county, Clinton's 2016 vote share by county, and population density by county in 2019, and finally, two .txt files containing OLS regression outputs. 

![Image of Code Diagram](https://github.com/datasci-harris/final-project-daniel-chen-final-project/blob/master/Write%20Up%20Documents/Code%20Diagram1000.png)

Direct links to websources can be found in the Appendix. 
