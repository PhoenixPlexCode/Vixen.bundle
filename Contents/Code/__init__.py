import re
import random
import urllib
import urllib2 as urllib
import urlparse
import json
from datetime import datetime
from PIL import Image
from cStringIO import StringIO

VERSION_NO = '2.2018.09.08.1'

def any(s):
    for v in s:
        if v:
            return True
    return False

def Start():
    HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1MINUTE*20
    HTTP.Headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'
    HTTP.Headers['Accept-Encoding'] = 'gzip'

def capitalize(line):
    return ' '.join([s[0].upper() + s[1:] for s in line.split(' ')])

def tagAleadyExists(tag,metadata):
    for t in metadata.genres:
        if t.lower() == tag.lower():
            return True
    return False

def posterAlreadyExists(posterUrl,metadata):
    for p in metadata.posters.keys():
        Log(p.lower())
        if p.lower() == posterUrl.lower():
            Log("Found " + posterUrl + " in posters collection")
            return True

    for p in metadata.art.keys():
        if p.lower() == posterUrl.lower():
            return True
    return False
searchSites = [None] * 1
searchSites[0] = ["Vixen","Vixen","https://www.vixen.com","https://www.vixen.com/search?q="]

def getSearchBaseURL(siteID):
    return searchSites[siteID][2]
def getSearchSearchURL(siteID):
    return searchSites[siteID][3]
def getSearchFilter(siteID):
    return searchSites[siteID][0]
def getSearchSiteName(siteID):
    return searchSites[siteID][1]
def getSearchSiteIDByFilter(searchFilter):
    searchID = 0
    for sites in searchSites:
        if sites[0].lower() in searchFilter.lower().replace(" ","."):
            return searchID
        searchID += 1
    return 9999
def getSearchSettings(mediaTitle):
    mediaTitle = mediaTitle.replace(" - ", " ")
    mediaTitle = mediaTitle.replace("-", " ")
    # Search Site ID or -1 is all
    searchSiteID = None
    # Date/Actor or Title
    searchType = None
    # What to search for
    searchTitle = None
    # Date search
    searchDate = None
    # Actors search
    searchActors = None

    # Remove Site from Title
    searchSiteID = getSearchSiteIDByFilter(mediaTitle)
    Log("^^^^^^^" + str(searchSiteID))
    if searchSiteID != 9999:
        Log("^^^^^^^ Shortening Title")
        searchTitle = mediaTitle[len(searchSites[searchSiteID][0])+1:]
    else:
        searchTitle = mediaTitle

    #Search Type
    if unicode(searchTitle[:4], 'utf-8').isnumeric():
        if unicode(searchTitle[5:7], 'utf-8').isnumeric():
            if unicode(searchTitle[8:10], 'utf-8').isnumeric():
                searchType = 1
                searchDate = searchTitle[0:10].replace(" ","-")
                searchTitle = searchTitle[11:]
            else:
                searchType = 0
        else:
            searchType = 0
    else:
        searchType = 0

    return [searchSiteID,searchType,searchTitle,searchDate]

    

class EXCAgent(Agent.Movies):
    name = 'Vixen'
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang):
        title = media.name
        if media.primary_metadata is not None:
            title = media.primary_metadata.title
        title = title.replace("'","").replace('"','')
        Log('*******MEDIA TITLE****** ' + str(title))

        # Search for year
        year = media.year
        if media.primary_metadata is not None:
            year = media.primary_metadata.year

        Log("Getting Search Settings for: " + title)
        searchSettings = getSearchSettings(title)
        if searchSettings[0] == 9999:
            searchAll = True
        else:
            searchAll = False
            searchSiteID = searchSettings[0]
        searchTitle = searchSettings[2]
        Log("Site ID: " + str(searchSettings[0]))
        Log("Search Title: " + searchSettings[2])
        if searchSettings[1]:
            searchByDateActor = True
            searchDate = searchSettings[3]
            Log("Search Date: " + searchSettings[3])
        else:
            searchByDateActor = False

        encodedTitle = urllib.quote(searchTitle)
        Log(encodedTitle)

        siteNum = 0
        for searchSite in searchSites:
            if searchAll or searchSiteID == siteNum:
                searchResults = HTML.ElementFromURL(getSearchSearchURL(siteNum) + encodedTitle)
                for searchResult in searchResults.xpath('//article[@class="videolist-item"]'):
                    
                    
                    Log(searchResult.text_content())
                    titleNoFormatting = searchResult.xpath('.//h4[@class="videolist-caption-title"]')[0].text_content()
                    Log("Result Title: " + titleNoFormatting)
                    curID = searchResult.xpath('.//a[@class="videolist-link ajaxable"]')[0].get('href')
                    curID = curID.replace('/','_')
                    Log("ID: " + curID)
                    releasedDate = searchResult.xpath('.//div[@class="videolist-caption-date"]')[0].text_content()

                    Log(str(curID))
                    lowerResultTitle = str(titleNoFormatting).lower()
                    if searchByDateActor != True:
                        score = 102 - Util.LevenshteinDistance(searchTitle.lower(), titleNoFormatting.lower())
                    else:
                        searchDateCompare = datetime.strptime(searchDate, '%Y-%m-%d').strftime('%B %d, %y')
                        score = 102 - Util.LevenshteinDistance(searchDateCompare.lower(), releasedDate.lower())
                    titleNoFormatting = titleNoFormatting + " [" + searchSites[siteNum][1] + ", " + releasedDate + "]"
                    results.Append(MetadataSearchResult(id = curID + "|" + str(siteNum), name = titleNoFormatting, score = score, lang = lang))
                results.Sort('score', descending=True)         
            siteNum += 1
           

    def update(self, metadata, media, lang):

        Log('******UPDATE CALLED*******')
        siteID = int(str(metadata.id).split("|")[1])

        ##############################################################
        ##                                                          ##
        ##   Vixen                                                  ##
        ##                                                          ##
        ##############################################################
        if siteID == 0:
            temp = str(metadata.id).split("|")[0].replace('_','/')

            url = getSearchBaseURL(siteID) + temp
            detailsPageElements = HTML.ElementFromURL(url)

            # Summary
            metadata.studio = "Vixen"
            paragraph = detailsPageElements.xpath('//span[@class="moreless js-readmore"]')[0].text_content()
            paragraph = paragraph.replace('&13;', '').strip(' \t\n\r"').replace('\n','').replace('  ','') + "\n\n"
            metadata.summary = paragraph
            metadata.title = detailsPageElements.xpath('//h1[@id="castme-title"]')[0].text_content()
            date = detailsPageElements.xpath('//span[@class="player-description-detail"]//span')[0].text_content()
            date_object = datetime.strptime(date, '%B %d, %Y')
            metadata.originally_available_at = date_object
            metadata.year = metadata.originally_available_at.year    
                
            
            # Genres
            metadata.genres.clear()
            # No Source for Genres, add manual

            metadata.genres.add("Hardcore")
            metadata.genres.add("Heterosexual")
            metadata.genres.add("Boy Girl")
            metadata.genres.add("Caucasian Men")
            metadata.genres.add("Glamcore")

            # Actors
            metadata.roles.clear()
            actors = detailsPageElements.xpath('//p[@id="castme-subtitle"]//a')
            if len(actors) > 0:
                for actorLink in actors:
                    role = metadata.roles.new()
                    actorName = actorLink.text_content()
                    role.name = actorName
                    actorPageURL = actorLink.get("href")
                    actorPage = HTML.ElementFromURL("https://www.vixen.com"+actorPageURL)
                    actorPhotoURL = actorPage.xpath('//img[@class="thumb-img"]')[0].get("src")
                    role.photo = actorPhotoURL

            # Posters/Background
            posters = detailsPageElements.xpath('//div[@class="swiper-slide"]')
            background = detailsPageElements.xpath('//img[contains(@class,"player-img")]')[0].get("src")
            metadata.art[background] = Proxy.Preview(HTTP.Request(background, headers={'Referer': 'http://www.google.com'}).content, sort_order = 1)
            posterNum = 1
            for posterCur in posters:
                posterURL = posterCur.xpath('.//img[@class="swiper-content-img"]')[0].get("src")
                metadata.posters[posterURL] = Proxy.Preview(HTTP.Request(posterURL, headers={'Referer': 'http://www.google.com'}).content, sort_order = posterNum)
                posterNum = posterNum + 1