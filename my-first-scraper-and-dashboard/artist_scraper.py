# -*- coding: utf-8 -*-
"""
Created on Wed Nov  8 22:26:47 2023

@author: Scott Pliniussen, Anne Lindberg, Nikolaj Søndergaard, Tobias Vemmelund
"""
#%%

# LOAD NECESSARY MODULES AND HEADERS
import urllib
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
from datetime import datetime
import pandas
from geopy.geocoders import Nominatim

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "utf-8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0"
}

#%%

# INPUT URL TO AN ARTIST TO SCRAPE THEIR CONCERT INFORMATION
artist = 'https://www.setlist.fm/setlists/imagine-dragons-5bd1b7fc.html'

# EXTRACT ARTIST NAME
artist_name = artist.rsplit('/', 1)[1].rsplit('-', 1)[0]

# CREATE A FOLDER WITH THE ARTIST NAME IF IT DOESN'T EXIST
if not os.path.exists(artist_name):
    os.makedirs(artist_name)


#%%

def scrape_pages(headers, url):
    
    # CREATE A 'PAGES' FOLDER IF IT DOESN'T EXIST
    if not os.path.exists(f'{artist_name}/pages'):
        os.makedirs(f'{artist_name}/pages')
    
    # REQUEST WEBPAGE CONTENT AND MAKE IT INTO A SOUP
    request = urllib.request.Request(url, None, headers)
    response = urllib.request.urlopen(request)
    soup = BeautifulSoup(response, features="lxml")
    
    # FIND THE TOTAL NUMBER OF WEBPAGES
    total_pages = int(soup.find('a', title='Go to last page').text)
    
    # ITERATE THROUGH THE PAGES
    for page in tqdm(range(1, total_pages + 1)):
        page_url = f'{url}?page={page}'
        
        # REQUEST PAGE CONTENT
        page_request = urllib.request.Request(page_url, None, headers)
        page_response = urllib.request.urlopen(page_request)
        
        # SAVE THE PAGE TO A FILE IN THE 'PAGES' FOLDER
        with open(f'{artist_name}/pages/{page}.html', 'w', encoding='utf-8') as f:
            f.write(str(page_response.read().decode('utf-8')))
            
        # ADD A DELAY TO AVOID OVERLOADING THE SERVER
        time.sleep(1)
        
scrape_pages(headers, artist)

#%%

def scrape_concerts(headers):
    
    # CREATE A 'CONCERTS' FOLDER IF IT DOESN'T EXIST
    if not os.path.exists(f'{artist_name}/concerts'):
        os.makedirs(f'{artist_name}/concerts')
    
    # CREATE A LIST CONTAINING ALL THE PAGES IN THE 'PAGES' FOLDER
    pages = os.listdir(f'{artist_name}/pages')
    
    # CREATE A COUNTER
    count = 1
    
    # ITERATE THROUGH EACH PAGE
    for page in tqdm(pages):
        
        # READ PAGE CONTENT AND MAKE IT INTO A SOUP
        text = open(f'{artist_name}/pages/{page}', encoding="utf-8").read()
        soup = BeautifulSoup(text,features="lxml")
        
        #  FIND ALL CONCERT LINKS ON THE PAGE
        concerts = soup.findAll('a',attrs={'class':'summary url'})
        
        # ITERATE TROUGH EACH CONCERT LINK
        for concert in tqdm(concerts):
            
            # EXTRACT THE LINK AND CREATE THE COMPLETE URL FOR THE CONCERT PAGE
            link = concert['href'][2:]
            url = f'https://www.setlist.fm{link}'
            
            # REQUEST CONTENT FROM THE CONCERT PAGE
            request = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(request)
            
            # SAVE THE CONCERT PAGE TO A FILE IN THE 'PAGES' FOLDER 
            with open(f'{artist_name}/concerts/{count}.html', 'w', encoding='utf-8') as f:
                f.write(str(response.read().decode('utf-8')))
                
            # ADD A DELAY TO AVOID OVERLOADING THE SERVER
            time.sleep(1)
            
            # INCREMENT COUNTER
            count += 1
            
scrape_concerts(headers)

#%%
        
def parse_concert_data():
    
    # CREATE A LIST TO CONTAIN THE EXTRACTED DATA
    data = []
    
    # CREATE A LIST CONTAINING ALL THE CONCERT PAGES IN THE 'CONCERTS' FOLDER
    concerts = os.listdir(f'{artist_name}/concerts')
    
    # ITERATE THROUGH EACH CONCERT PAGE
    for concert in tqdm(concerts):
        
        # READ PAGE CONTENT AND MAKE IT INTO A SOUP
        text = open(f'{artist_name}/concerts/{concert}', encoding="utf-8").read()
        soup = BeautifulSoup(text,features="lxml")

        # FIND DATE INFORMATION ON THE CONCERT PAGE
        dateblock = soup.find('div', attrs={'class':'dateBlock'})
        month = dateblock.find('span', attrs={'class':'month'}).text
        day = dateblock.find('span', attrs={'class':'day'}).text
        year = dateblock.find('span', attrs={'class':'year'}).text
        
        # CONVERT DATE FORMAT TO ISO STANDARD FOR READABILITY
        date_string = f'{year}-{month}-{day}'
        dt = datetime.strptime(date_string, '%Y-%b-%d')
        
        # EXTRACT DATE INFORMATION
        date = dt.strftime('%Y-%m-%d')
        
        # FIND AND EXTRACT VENUE INFORMATION
        meta = soup.find('meta', attrs={'property':'qc:venue'})
        venue = meta.get('content')
        
        # CREATE NOMINATIM GEOCODER INSTANCE AND CONVERT VENUE INFORMATION
        geolocator = Nominatim(user_agent='venue_geocoder')
        location = geolocator.geocode(venue, timeout=120)
        
        # CREATE LATITUDE AND LONGITUDE PLACEHOLDER
        latitude = None
        longitude = None
        
        # IF LOCATION IS FOUND, EXTRACT GEOCODES
        if location:
            latitude = location.latitude
            longitude = location.longitude
        
        # IF NO LOCATION IS FOUND, CREATE A NEW VENUE VARIABLE
        else:
            imprecise_venue = venue
            
            # INITIATE WHILE COUNTER UNTIL GEOCODES ARE FOUND
            while latitude == None and longitude == None:
                
                # REMOVE THE FRONT PART OF THE VENUE INFORMATION AND CONVERT
                imprecise_venue = imprecise_venue.split(',', 1)[1]
                location = geolocator.geocode(imprecise_venue, timeout=120)
                
                # IF LOCATION IS FOUND, EXTRACT GEOCODES
                if location:
                    latitude = location.latitude
                    longitude = location.longitude
        
        # TRY TO FIND THE TOUR INFORMATION AND EXTRACT IF FOUND
        try:
            tour_info = soup.find('div', attrs={'class':'infoContainer'})
            tour_spans = tour_info.find('p').findAll('span')
            tour = tour_spans[2].text
            
        # HANDLE EXCEPTION IF NO TOUR INFORMATION IS FOUND
        except AttributeError:
            tour = 'NO TOUR INFORMATION'
        
        # CREATE A LIST TO CONTAIN SONG NAMES
        song_list = []
        
        # FIND THE SONG INFORMATION
        setlist = soup.find('div', attrs={'class': 'setlistList'})
        song_labels = setlist.findAll('a', attrs={'class':'songLabel'})
        
        # IF SONG INFORMATION IS FOUND, EXTRACT NAME AND APPEND TO SONGS LIST
        if song_labels:
            for song in song_labels:
                name = song.text
                song_list.append(name)
            
            # MAKE THE SONG LIST INTO A STRING TO REMOVE QUOTATION MARKS
            songs = ', '.join(song_list)
                
        # IF NO SONG INFORMATION IS FOUND, SET SONGS TO ''
        else:
            songs = 'NO SETLIST INFORMATION'


        # APPEND ALL THE EXTRACTED DATA TO THE DATA LIST
        data.append([date, venue, tour, songs, latitude, longitude])
    
    # CREATE A PANDAS DATAFRAME AND SAVE TO AS CSV FILE
    df = pandas.DataFrame(data, columns = ['date', 'venue', 'tour', 'songs', 'latitude', 'longitude'])
    df.to_csv(f'{artist_name}/concerts.csv', index=False, encoding='utf-8')

parse_concert_data()


#%%
