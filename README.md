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

### 3. Analysis 

This section will be divided into two parts. The first part contains observational analysis where I utilize plots and choropleths to determine trends. The second section is more “causal” where I run regressions to back-up my findings. I put "causal" in quotes because the primary purpose of this project is to write Python code to retrieve data and create visuals. This analysis is not intended to be an academic exercise. In section 4 I highlight the limitations of my model. 

#### 3.1 Observational Analysis 
As I mentioned earlier in my Essential Question section, I am interested in tracking Coronavirus cases along party lines. Media outlets have characterized a split between Democrats and Republicans where the former appears more likely to take precautions such as mask wearing while the latter has been relatively more carefree. I would like to emphasize that these are *generalizations*. I am not claiming that every single Democrat wears a mask and every single Republican does not. However, I am curious to see if the empirical evidence to back up these broad claims exists. A simple method, shown below, would be to look at the total number of Coronavirus cases among states that voted for Hillary Clinton in 2016 compared to total cases among states that voted for Donald Trump in the same year where any given state’s majority vote for a candidate in the 2016 presidential election would serve as a proxy for the overall partisan lean of that state.

*As a side note, I limit my analysis to the days between January 21, 2020 and December 1, 2020 for practical considerations. The NYT provides records beginning in late January and updates data daily, but I restrict the end date to the first of December because GitHub cannot handle the size of a .csv that includes data for more dates.*

From the first subplot below, it’s clear that the states who voted for Trump in 2016 have a much larger change in the daily reported number of cases relative to states that voted for Clinton - though cases have surged across the board since Halloween. This trend has held consistent for the larger part of 2020 with the exception of a period between when President Trump declared a national emergency and when George Floyd related protests begun. The regional subplot tells a similar story. In the South - where states are typically red - cases surged during the summer relative to the rest of the country. Cases have also skyrocketed in the Autumn months for states in the Midwest. While there are a few notable blue states in this region, the majority are red or purple.

![Image of lineplots](https://github.com/danielbchen/partisanship-and-covid/blob/main/Lineplots.png)

While it may be tempting to definitively claim that partisanship is tied to Coronavirus cases, this would fail to acknowledge two factors. First, states have different populations, and second, more states voted for Trump over Clinton four years ago. In other words, the larger change in daily reported cases of the virus in Republican states may be simply explained by a larger total population. With this caveat in mind, I turn to creating choropleths which are shown below.
