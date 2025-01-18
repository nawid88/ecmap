import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
import requests
import pandas as pd
from duckduckgo_search import DDGS
from tavily import TavilyClient
import googlemaps
from bs4 import BeautifulSoup
import scrapy
from scrapy.crawler import CrawlerProcess
import scrapy.crawler as crawler
from scrapy.utils.log import configure_logging
from multiprocessing import Process, Queue
from twisted.internet import reactor
import multiprocessing
import json, operator

multiprocessing.set_start_method('fork', force=True)

configure_logging()
with open("./SECRET.txt", "r") as s_file:
    data = [line.replace("\n", "") for line in s_file.readlines()]
    API_KEY1 = data[0]
    API_KEY2 = data[1]


api_key = API_KEY1


gmaps = googlemaps.Client(key=api_key) #Defining google maps client


st.set_page_config(
    layout= "wide",
    page_icon ='/Users/school/ecmap/pageIcon.jpg',
    initial_sidebar_state= 'collapsed'
    )

# HTML and CSS for the banner 
banner =    """
    <style>
        .banner {
            background-color: #121926;
            color: white;                       
            padding:20px;
            font-size: 40px;
            text-align: center;
            border-radius: 10px;
            border: 1px solid #313439
            
        }
    </style>
    <h1 class="banner">EC Map</h1>

"""

# Display the banner in markdown
st.markdown(banner, unsafe_allow_html=True)


def orgName(link):
    homeLink = "https://" #starting homepage url with "https://"
    #Finding main page of website 
    for char in range(8, len(link)): #For each character in the websites url
        if link[char] == "/": #If character is '/', stop 
            break
        else:
            homeLink += link[char] #other wise add the character to the homeLink url
    #This grabs text before first '/' to get home page url

    #Finding title of main page which will usually be the name of the organization
    headers={'User-Agent':"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9"} #User agent so websites dont know webscraper is webscraper
    results = requests.get(url=homeLink, headers=headers) #Sending a request to the main page
    soup = BeautifulSoup(results.content, "lxml") #Turning the contents into a soup 
    title = soup.find("meta", property="og:site_name") #finding the site_name property with a meta tag and setting it to title
    if title: #if there is a title
        return title.get("content") #get the content of the site_name which will have the actual site_name text
    else:
        return "".join((soup.title).get_text(strip=True).splitlines()) #otherwise just use the built in soup.title and get the actual title of the site
    
    #site_name is usually more accurate to the organizations name rather than the title of the website
    

def cleanS(word): #Removes "s" if it exists at the end of the word
    if word.endswith("s"): #if the word ends with s
        s_location = len(word) - 1 #find s location
        cleaned = word[: s_location] #grab text up until s location
        return cleaned #return cleaned
    if word == "Volunteering": 
        cleaned = word[: 9] #removed 'ing'
        return cleaned  #returns Volunteer

    return word

def findType(contents, title): #finds out what type of opportunity the website is offering based on its content or title
        typeMatches = 0
        type_ = ""
        types =  ["volunteer", "intern", "research"] #possible types
        title = title.lower() 
        contents = contents.lower()

        for eachType in types: #for each type
            if eachType in title.lower(): #checks to see if that type is already in the title
                type_ = eachType #if it is, type is set to the type found in title

        if not type_: #if type not found still
            for eachType in types: #for each type
                possibleType = contents.count(eachType) #cound how many times that type occurs in the contents of the website
                if possibleType > typeMatches: #if this type has more text occurences than the most occurences found for a type
                    type_ = eachType #set it as the new type
                    typeMatches = possibleType #most occurences found for the type is now set to how many times the current type occured
        if type_ == "volunteer":
            return "Volunteering"
        elif type_ == "intern":
            return "Internship"
        else:
            return "Research"

def getDesc(content): #gets short description
    try:
        desc = DDGS().chat(f"Sumarrize the opportunity they are offering in 3 sentences {content}", model="gpt-4o-mini") #using duckduck go chat gpt with prompt to the summary based on text contents of website
    except:
        return "No description available" #if theres an error
    else:
        if "DuckDuckGo" in desc: #if it returns something weird it will usually have DuckDuckgo inside the response
            return "No description available" #then set the description to n/a
        else:
            return desc #other wise return what chatgpt responded with



#Html inside markdown for the "Filters" header box
st.sidebar.markdown("""

    <style>
        .header {

            border-radius: 10px;
            text-align: center;
            border: 1px solid #313439
        }
    </style>
    <h1 class='header'>Filters</h1>


""",unsafe_allow_html=True)

#html inside markdown for the buttons to increase their width
st.sidebar.markdown("""
    <style>
        .stButton>button {
            width: 100%;  
        }
    </style>
""", unsafe_allow_html=True)


co1, co2 = st.sidebar.columns([1,1], vertical_alignment="bottom") #columns for the buttons 1:1 ratio, aligned with the bottom of each button
clear = co1.button("Clear") #button to clear text inputs and map


if clear:
    st.session_state.opp = None #clears opp box
    st.session_state.loc = "" #clears loc box
    st.session_state.edu = None #clears edu box
    st.session_state.intr = "" #clears intr box
    st.session_state.org = "" #clears org box
    st.session_state.rst = 0 #clears results box
    with open("items.csv", "w") as file: #Clears items.csv
            pass

edu = st.sidebar.selectbox("Academic Level:", ["Highschool Student", "Undergraduate Student", "Graduate Student"], key="edu") #education level select box in sidebar
intr = st.sidebar.text_input("Interested in:", key="intr",placeholder="Enter an interest.") #interests input box in side bar
opp = st.sidebar.selectbox("Looking for: ", ["Volunteering", "Internships", "Research"] , key="opp") #opportunities interested in select box in side bar
loc = st.sidebar.text_input("City:", key="loc",placeholder='Enter a specific city.') #location input in sidebar
org = st.sidebar.text_input("Specific Organizations:", key="org",placeholder='Enter a specific organization.') #specific organization input in side bar
max_search_results = st.sidebar.number_input("Number of sites to query:", key="rst", placeholder='Enter how many sites to search.', step=1) #how many sites to be queried


search = co2.button("Search") #search button


    
query="" #query for tavily search
if intr:
    query += intr
if opp:
    query += f' "{cleanS(opp)}" opportunities '
if edu:
    query += "student"
if loc:
    query += f" {loc}"
if org:
    query += f" {org}"
query += " site:.ca"




if search:
    my_bar = st.progress(0, text="Loading")
    with open("items.csv", "w") as file: #Clears items.csv
        pass
    with open("filtered.csv", "w") as file: #Clears filtered.csv
        file.write("link,relevance") #Adds columns "link, relevance"
        file.write('\n') #Creates a new line for info to be added to
    with open("possible_links.csv", "w") as file: #Clears possible_links.csv
        file.write("links") #Adds column "links"
        file.write('\n') #Creates a new line for info to be added to
    
    
    tavily_client = TavilyClient(api_key=API_KEY2) #tavily client setup

    results = tavily_client.search(query,max_results=max_search_results) #Tavily search using query and max searches wanted
    

    possible_links = []

    for result in results["results"]: #For every link in search results
        url = result["url"] #Find url
    
        possible_links.append(url) #Add url to "possible links"
    
    
    


    filtered_list = {}
    urls = []
    relevanceScores = []
    
    headers={'User-Agent':"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9"} #User agent so websites dont know webscraper is webscraper
    for url in possible_links: #For each url in possible links csv
  

        if '"' not in url and '.ca' in url:# if link is canadian
            relevanceScore = 0 #starts with 0 relevance
            try:
                result = requests.get(url=url, headers=headers) #send result request using user agent already stated
    
            except: #If any errors
                relevanceScore = 0 #Site cant be accessed so it automatically has 0 relevance
            else: #If no errors
                soup = BeautifulSoup(result.content, 'lxml') #create beuatiful soup
                contents = (soup.get_text(strip=True)).lower() #get text contents from soup
                relevanceScore = contents.count("opportunit") + contents.count("program") + contents.count("apply") + contents.count("eligib") + contents.count("student") + contents.count(opp)   #Count how many times each phrase occurs and add to relevance score
    
            if relevanceScore >= 10: #if relevance score is equal to or larger than 10
                urls.append(url) #add it to the urls list
                
                relevanceScores.append(relevanceScore) #storing the relevance for future reference

    filtered_list  = {"link" : urls, "relevance": relevanceScores} #Creates dict with links and their relative relevance scores
    filtered_df = pd.DataFrame(filtered_list) #Turns links into table format
    filtered_df.to_csv("filtered.csv", mode="a", index=False,header=False) #adds table data frame to filtered csv to then be checked if its an actual opportunity if so then categorized

    #Categorizing begins
        
    filtered_links_df = pd.read_csv("filtered.csv") #filtered.csv link column into pd dataframe
    possible_links = filtered_links_df.link.values.tolist() #pd dataframe into list, to make it more accessible
    
    relevance_list = filtered_links_df.relevance.values.tolist() #relevance pd datafram into list to make it more accessible
    link_relevance = dict(zip(possible_links, relevance_list)) #turn links and their relevance into a dict so relevance of a link can be found later on when needed
    
    
    class WebScraper(scrapy.Spider): #Create scrapy class
        name = 'web_scraper' #webscraper name
        start_urls = possible_links #urls webscraper will scrape


        def parse(self, response): #What its going to scrape and return
            title = response.css('title::text').get() #Getting title of website 
            link = response.url #link of website
            linkContent = "".join(response.css('p::text').getall()) #getting text content of the website "p::text"
            type_ = findType(linkContent, title) #getting type of content using the findType function with the website title and contents
            desc = getDesc(linkContent) #getting description of content using the websites contents and the getDesc function
            organization = orgName(link) #getting organizations name using orgName function with the link to the website
            location_results = DDGS().maps(keywords=organization,country='Canada',state='ontario',place=loc,max_results=1) #using duckduck go maps to find location information of opportunity using the organizations name restricting results to the location entered by user
            if not title and type_: #if no title but has type
                title = f"{type_} Opportunity" #set title to a default title 
            if location_results: #if duck duck go maps returns a result
                address = location_results[0]['address'] #grabbing address
                lat =  location_results[0]['latitude'] #grabbing latitude
                lon = location_results[0]['longitude'] #grabbing longitude
            else: #if no results from duck duck go maps
                results = gmaps.places(query=organization,location='43.665960, -79.359272', radius=40000, open_now=False) #Getting location information using google maps since it has better searching capabilities, search is being restricted by only returning results around a 40000 km radius of toronto using organization name
                if results:
                    address= results['results'][0]['formatted_address'] #grabbing address 
                    lat = results['results'][0]['geometry']['location']['lat'] #grabbing latitude
                    lon = results['results'][0]['geometry']['location']['lng'] #grabbing longitude
                else: #if both duckduck go and google maps fails
                    address= "unknown" #Unknown address
                    lat = 1 #Unknown latitude
                    lon = 1 #Unknown longitude
            
            yield { #Information that will be returned
                "title": title.strip(),
                "type": type_,
                "desc": desc,
                "organization": organization,
                "link": link,
                "address":address,
                "lat": lat,
                "lon": lon,
                "relevance": [link_relevance[link]]
                
            }

    #run_spider and f function is the wrapper from https://stackoverflow.com/questions/41495052/scrapy-reactor-not-restartable
    #They both help to allow the scrapy spider to run more than once after it started, I editted them a little bit since they wouldnt work for my code at first
    def run_spider(spider): 
    
        q = Queue()
        p = Process(target=f, args=(q,))
        p.start()
        result = q.get()
        p.join()
        
        if result is not None:
            raise result

    def f(q):
        spider = WebScraper
        try:
            runner = crawler.CrawlerRunner(settings = { 
                'FEED_URI': 'items.csv', #Webscraper will export all results to items.csv
                'FEED_FORMAT': 'csv', #Csv file format
                'LOG_ENABLED': False #No logging in terminal
            
            })
            deferred = runner.crawl(spider)
            deferred.addBoth(lambda _: reactor.stop())
            reactor.run()
            q.put(None)
        except Exception as e:
            q.put(e)


    run_spider(WebScraper) #Running webscraper spider         


#Mapping
try:  #try to read the items.csv which has all the opportunities and their information
    mergedDF = pd.read_csv("items.csv") 
except:#if an error (emtpy csv file)
    mergedDF = pd.DataFrame() #set the DF to be empty
else:
    mergedDF = pd.read_csv("items.csv")  #if successfull, store csv contents into pandas dataframe




mergedJson = mergedDF.to_json(orient="records") #turn the pandas dataframe into a json
mergedJson = json.loads(mergedJson) #load the json into python


if mergedJson: #if the json has the opportunity information in it
    mergedJson.sort(key=operator.itemgetter("relevance")) #sorts the opportunities based on least to most relevant
    mergedJson.reverse() #reverse to get most to least relevance




ecmap = folium.Map()     #create main map of ec's
ecmap.fit_bounds([[43.6, -79.5], [43.8, -79.3]]) #Bounds for Toronto and surronding areas to make map stay in the GTA
folium.TileLayer("cartodb_dark_matter").add_to(ecmap) #To make map dark

st.write(" ")# adds space inbetween list/map and banner

col1, col2 = st.columns([5,10], vertical_alignment="top") #columns for the map and list, ratio of 5:10


for item in mergedJson: # for each ec item in the json 
    if item["title"]: #if the ec has a title
        #create popup using information inside the json item about each ec opportunity
        #<br>: puts break inbetween 2 lines
        #<b>: bold text
        #<a: embedding link to visit organizations website
        popupItem =f"""                       
        <b>{item["title"]}</b><br><br>
        <b>Type:</b> {item["type"]}<br>
        <b>Address:</b> {item["address"]}<br>
        <b>Organization:</b> {item["organization"]}<br><br>
        <b>Description:</b> {item["desc"]}<br><br>
        <a href={item["link"]} target='_blank'>Visit {item["organization"]}</a>

    """

        if item["type"] == "Research": #if the item is a research opportunity
            icon=folium.features.CustomIcon("/Users/school/ecmap/research.png",icon_size=(30,30)) #set icon of pin to custom research icon pin
        elif item["type"] == "Internship": #if the item is an internship opportunity
            icon=folium.features.CustomIcon("/Users/school/ecmap/intern.png",icon_size=(33,33)) #set icon of pin to custom internship icon pin
        else: #otherwise must be volunteering 
            icon=folium.features.CustomIcon("/Users/school/ecmap/volunteer.png",icon_size=(32,29)) #set icon of pin to custom volunteering icon pin
        if item["lat"] != 1: #as long as the lat isnt 1, meaning its not unknown
            folium.Marker( 

                location = [item['lat'],item['lon']], #set location using ec items latitude and longitude coords
                popup = folium.Popup(popupItem, max_width=500, max_height=500), #set popup 
                tooltip = item["type"], #create hoverable text showing what pin is (volunteering, internship, research)
                icon= icon #set icon predetermined icon based on type of opportunity

            ).add_to(ecmap) #adds the pin and popup to main map


with col2: #in the second column

    st_folium(ecmap,width=1000)  #displays folium ec map with width of 1000


#Creating the expandable list
with col1.container(height=700): #in the first column
    
    i = 0 #current key of each expandable list item
    resultsCounter = 0 #to cound results
    #counting how many results there are 
    for item in mergedJson: #for each item in merged json
        if item["title"]: #if the item has a title
            resultsCounter += 1 #increase results by 1
    st.header(f"{resultsCounter} Results") #create results header with number of results on top of list
    st.divider() #divider between the results header and actual list items
    for item in mergedJson: #For each opportunity it adds title, type, a description and the link as an expandable list item
        
        if item["title"]: #if item has title   
           
            miniMap = folium.Map() #create a mini map to display the location of opportunity
            miniMap.fit_bounds([[item['lat'],item['lon']], [item['lat']+0.1,item['lon']+0.1]]) #Bounds for Toronto and surronding areas to make map stay in the GTA
           
            itemExpander = st.expander(f"**{"".join(item["title"].splitlines())}**") #create an expandable item to store information of opportunity with a bold title
            i+=1 #key goes up by one
            with itemExpander: #contents of expandable item in ec list
            
                st.write(f"**Type:** {item["type"]}")  #type
                st.write(f"**Address:** {item["address"]}") #address
                st.write(f"**Organization:** {item["organization"]}") #organizations name
                st.write(f"{item["desc"]}") #a short description
                st.write(f"[Visit {item["organization"]}](%s)" %item["link"]) #embedded link to website of opportunity
            
            

                folium.Marker(location = [item['lat'],item['lon']]).add_to(miniMap) #add the pinned location of the opportunity to the mini map inside the expandable list item


                if item["lat"] != 1: #as long as the opporunity doesnt have an unknown latitude or longitude
                    st_folium(miniMap,width=500,height=200,key = i) #create a mini map to display the opportunities location, each mini map has a key ("i") in order to create and display more than one in a single streamlit session
