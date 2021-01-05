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

![Infection Rate Choropleth](https://github.com/danielbchen/partisanship-and-covid/blob/main/Infection%20Choropleth.png)

The image above displays the infection rate on a county basis. I have purposefully limited the number of bins to six to more easily compare metrics across choropleths. However, it is worth noting that some counties have infection rates above 15%. I suspect that population may play a role, and I would would expect the counties with the highest rates of infection to line up with the counties that are the most heavily populated. This rationale makes sense given CDC recommendations to socially distance and wear a mask. People living in crowded areas likely face greater rates of transmission. However, this is not the case when looking at figure below which illustrates population density.

![Population Density Choropleth](https://github.com/danielbchen/partisanship-and-covid/blob/main/Density%20Choropleth.png)

While there are certainly similarities between the two maps especially in looking at dense urban locations including - but not limited to - New York City, Chicago, Southern Florida, and Southern California. With these exceptions, the two choropleths are otherwise different. Large parts of the central United States, such as North Dakota, South Dakota, Kansas, and Oklahoma do not line up. These states have populations spread thin relative to coastal cities, and yet, I observe higher rates of infections. To synthesize, population may not be the only predictor of cases, but it still plays an important role. To explore another possible predictor, I plot Clinton’s vote margin in 2016 shown below.

![Clinton Vote Margin Choropleth](https://github.com/danielbchen/partisanship-and-covid/blob/main/Vote%20Choropleth.png)


The infection rate choropleth and the Clinton vote margin choropleth are not carbon copies, but in comparing two maps, the former more closely resembles the latter as opposed to comparing the infection rate choropleth and the population density choropleth. The intensities are not exactly identical, but on the surface, it appears that counties that voted for Trump to a greater degree are also counties that exhibit greater rates of infection. In other words, the margin in which Trump wins does not perfectly predict the intensity of infection, but the two appear to be somewhat related in general. In the next section, I turn to regression analyses to examine whether or not there is a ”causal” relationship.

#### 3.2 "Causal" Analysis 

In this section, I put causal in quotes because though I find statistically significant results in one of my models, the model is likely biased by many correlated factors which better explain the results. I explore these factors at the the end of this README.

In the first model I run, the dependent variable is the total number of cases and the independent variables are party identification and population estimate. Note, that in the final .txt file outputted by the Python script the Party variable is labeled as “BINARY PARTY ID” and the Population variable is referred to as “POP EST 2019”. Table 1 below the regression results (output generated by Python can be found [here](https://github.com/danielbchen/partisanship-and-covid/blob/main/Total%20Cases%20Regression.txt)). The number of reported cases in Democratic counties is less than the number reported in Republican counties by a difference of about 822. This finding is statistically different from zero when controlling for the population of a county. However, in this model I worry about the high r-squared value. Moreover, Python returns a multicollinearity warning. I suspect that the population variable poses a potential issue in predicting cases too well.

##### Table 1: Dependent Variable - Total Cases
| Coefficient |   Estimate  | Standard Error |
|:-----------:|:-----------:|:--------------:|
|    Party    | -822.442*** |     236.230    |
|  Population |   0.042***  |      0.000     |
|  Intercept  |    60.978   |     88.778     |

As a result, I attempt to standardize the measure of spread before running the regression by looking at the infection rate per county as the new dependent variable in my second model. Table 2, below, summarizes the findings (output generated by Python can be found [here](https://github.com/danielbchen/partisanship-and-covid/blob/main/Infection%20Rate%20Regression.txt)). Here I derive the infection rate by taking the total number of cases in a given county, and dividing that value by the estimated total number of people living in that county in the year 2019 in hopes of drawing a fairer comparison between places like Los Angeles County, California and Fairfield County, Connecticut where, by construction, the former is more likely to face a significantly larger number of cases because its population is much larger. In this second model, Democratic counties have a smaller rate of infection by the magnitude of roughly half a percentage point than their Republican counterparts. This difference is statistically meaningful at the 99% level of significance. Taken at face value, the model suggests that party identification has some predictive power.

##### Table 2: Dependent Variable - Infection Rate

| Coefficient |  Estimate  | Standard Error |
|:-----------:|:----------:|:--------------:|
|    Party    | -0.470**** |      0.120     |
|  Intercept  |  4.815***  |      0.047     |

### 4. Limitations of the Model  

Though the difference in the infection rate between democratic and republican counties is statistically significant, there are several limitations of the model that *prevent the findings from being truly causal*.

In looking at the R-Squared value, party identification in model 2 only explains about 5% of the variation in the infection rate. Put differently, party identification is most likely correlated with other observables excluded from the model that better explain infection rates. Party identification is likely tied to race and income. I suspect income to be a driver of infection because individuals with higher incomes are better equipped to follow public health guidelines. They have the capital to purchase personal protective equipment and are likely privileged to work remotely where they are less exposed to human interaction compared to a low wage working individual in the gig economy who is required to serve restaurant patrons or fulfill online orders.

Moreover, income is tied to other extraneous factors such as access to health care and one’s individual well-being. Higher income areas arguably have better access to health care services that mitigate the risk of infection. Additionally, higher-income earners are likely better able to afford a healthy lifestyle. They are likely to be better off in terms of personal health and wellness. Lower-income earners may face more health hardships and pre-existing conditions and compromised immune systems likely increase susceptibility to the novel virus.

### 5. Appendix 

This section details all the files included in this repository and contains links to data sources. 

1. [covid_partisanship_analysis.py](https://github.com/danielbchen/partisanship-and-covid/blob/main/covid_partisanship_analysis.py): Python script containing entire code. 
2. [Code Diagram1000.png](https://github.com/danielbchen/partisanship-and-covid/blob/main/Code%20Diagram1000.png): A .png file outlining structure of the Python script. Identical to the image found in section 2. 
3. [Votes by State in 2016.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/Votes%20by%20State%20in%202016.csv): A .csv file containing 2016 presidential election votes by state retreived from [Wikipedia](https://en.wikipedia.org/wiki/2016_United_States_presidential_election).
4. [Votes by County in 2016.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/Votes%20by%20County%20in%202016.csv): A .csv file containing 2016 presidential election votes by county retrieved from [Townhall](https://townhall.com/election/2016/president).
5. [FIPS codes.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/FIPS%20codes.csv): A .csv file containing county names along with their corresponding state and five digit FIPS codes retreived from [the USDA](https://www.nrcs.usda.gov/wps/portal/nrcs/detail/national/home/?cid=nrcs143_013697).
6. [Reported Daily Coronavirus Cases.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/Reported%20Daily%20Coronavirus%20Cases.csv): A .csv file containing the daily cumulative reported number of Coronavirus cases by county retrieved from [the NYT GitHub Repository](https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv).
7. [Poplation Estimates 2019.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/Poplation%20Estimates%202019.csv): A .csv file containing 2019 population estimates by county retrieved from the [the USDA](https://www.ers.usda.gov/webdocs/DataFiles/48747/PopulationEstimates.xls?v=6825.4).
8. [Population Density Estimates.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/Population%20Density%20Estimates.csv): A .csv file containing population density estimates by county retrieved from [the U.S. Census Open Data](https://opendata.arcgis.com/datasets/21843f238cbb46b08615fc53e19e0daf_1.geojson).
9. [Final Dataframe.csv](https://github.com/danielbchen/partisanship-and-covid/blob/main/Final%20Dataframe.csv): A .csv file that merges all of the aforementioned .csv files together. 
10. [cb_2018_us_county_500k.cpg](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.cpg), [cb_2018_us_county_500k.dbf](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.dbf), [cb_2018_us_county_500k.prj](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.prj), [cb_2018_us_county_500k.shp](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.shp), [cb_2018_us_county_500k.shp.ea.iso.xml](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.shp.ea.iso.xml), [cb_2018_us_county_500k.shp.iso.xml](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.shp.iso.xml), [cb_2018_us_county_500k.shx](https://github.com/danielbchen/partisanship-and-covid/blob/main/cb_2018_us_county_500k.shx): Shape files retrieved from [the U.S. Census](https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip) to create choropleths. 
11. [Lineplots.png](https://github.com/danielbchen/partisanship-and-covid/blob/main/Lineplots.png): A .png file showing the two subplots found in section 3.1 of the README. 
12. [Infection Choropleth.png](https://github.com/danielbchen/partisanship-and-covid/blob/main/Infection%20Choropleth.png): A .png file showing the choropleth of the Coronavirus infection rate by county across the continental United States. 
13. [Density Choropleth.png](https://github.com/danielbchen/partisanship-and-covid/blob/main/Density%20Choropleth.png): A .png file showing the choropleth of population density by county across the continental United States. 
14. [Vote Choropleth.png](https://github.com/danielbchen/partisanship-and-covid/blob/main/Vote%20Choropleth.png): A .png file showing the choropleth of Clinton's vote margin as a percentage difference between Clinton's vote share and Trump's vote share by county across the continental United States. 
15. [Total Cases Regression.txt](https://github.com/danielbchen/partisanship-and-covid/blob/main/Total%20Cases%20Regression.txt): A .txt file containing the regression output by regressing the total number of cases on party identification and population. 
16. [Infection Rate Regression.txt](https://github.com/danielbchen/partisanship-and-covid/blob/main/Infection%20Rate%20Regression.txt): A .txt file containing the regression output by regressing the infection rate on party identification. 
