# imports:
import json
import collections
import pandas as pd
from pymongo import MongoClient
import requests
import datetime
import time
from bs4 import BeautifulSoup as bs
import numpy as np


# open Matchbook session
def login():
    login_data = '{"username": "charlotteme","password": "Um3yp6sis0s"}'
    headers = {"Content-Type": "application/json;"}
    return requests.post('https://www.matchbook.com/edge/rest/security/session', data=login_data, headers=headers)


# Logout from session
def logout(headers):
    url = "https://api.matchbook.com/bpapi/rest/security/session"
    response = requests.request("DELETE", url, headers=headers)
    return response


# Get a list of current offers i.e. offers on markets yet to be settled.
def getCurOffers(querystring, headers):
    url = "https://api.matchbook.com/edge/rest/reports/v2/offers/current"

    return requests.request("GET", url, headers=headers, params=querystring)


# gives the sport's id for a given sports name.
def getSportId(name, headers):
    url = "https://api.matchbook.com/edge/rest/lookups/sports"

    querystring = {"offset": "0", "per-page": "500", "order": "name asc", "status": "active"}

    response = requests.request("GET", url, headers=headers, params=querystring)

    sports = response.json()["sports"]
    ids = []
    for sport in sports:
        if name in sport["name"]:
            ids.append(sport["id"])
    return ids


# Get a list of events available on Matchbook ordered by start time.
def getSportsEvents(ids, headers, tags):
    url = "https://api.matchbook.com/edge/rest/events"
    strIds = str(ids).replace("[", "")
    strIds = str(strIds).replace("]", "")
    today = datetime.datetime.now()
    tomorrow = (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d  %H:%M:%S')
    t = '2020-09-3 12:00:00'
    ts = time.strptime(tomorrow, '%Y-%m-%d  %H:%M:%S')
    before = int(time.mktime(ts))
    querystring = {"offset": "0", "per-page": "5000", "states": "open",
                   "exchange-type": "back-lay", "odds-type": "DECIMAL", "include-prices": "true", "price-depth": "1",
                   "price-mode": "expanded", "include-event-participants": "false",
                   "sport-ids": strIds, "before": before,"currency":"USD"}  # ,'tag-url-names':tags}

    response = requests.request("GET", url, headers=headers, params=querystring)
    events = []
    events2 = response.json()["events"]
    for event in events2:
        if event['in-running-flag'] == False:
            events.append(event)
    return events


# filter the list of sport selected events by league,recives events list and league string.
def FilterByLeague(events, League):
    fillteredDict = {}
    fillteredList = []
    for event in events:
        fillteredDict[event['name']] = event

    return fillteredDict


def GetFinalDf(events_dictionary):
    Event_Name_lst = []
    Date_list = []
    runners_lst = []
    runners_id_lst = []
    lay_price_lst = []
    lay_size_lst = []
    back_price_lst = []
    back_size_lst = []
    od = collections.OrderedDict(sorted(events_dictionary.items()))
    for event in od:
        try:
            for market in od[event]['markets']:
                if market['name'] == 'Total':
                    # over and under event name
                    Event_Name_lst.append(od[event]['name'])
                    Event_Name_lst.append(od[event]['name'])

                    # over and under date
                    Date_list.append(od[event]['start'])
                    Date_list.append(od[event]['start'])

                    for runner in market['runners']:
                        # bet on
                        runners_lst.append(runner['name'])
                        # runner id
                        runners_id_lst.append(runner['id'])

                        lay_price_lst.append(runner['prices'][1]['odds']
                                             if (len(runner['prices']) == 2)
                                             else runner['prices'][0]['odds'] if (
                                len(runner['prices']) == 1 and runner['prices'][0]['side'] == 'lay')
                        else 1.00)
                        lay_size_lst.append(runner['prices'][1]['available-amount']
                                            if (len(runner['prices']) == 2)
                                            else runner['prices'][0]['available-amount'] if (
                                len(runner['prices']) == 1 and runner['prices'][0]['side'] == 'lay')
                        else 0)
                        back_price_lst.append(runner['prices'][0]['odds']
                                              if (len(runner['prices']) == 2)
                                              else runner['prices'][0]['odds'] if (
                                len(runner['prices']) == 1 and runner['prices'][0]['side'] == 'back')
                        else 1.00)
                        back_size_lst.append(runner['prices'][0]['available-amount']
                                             if (len(runner['prices']) == 2)
                                             else runner['prices'][0]['available-amount'] if (
                                len(runner['prices']) == 1 and runner['prices'][0]['side'] == 'back')
                        else 0)
        except:
            continue

    # Create a DataFrame for each market\event
    final_df = pd.DataFrame({
        'Event Name': Event_Name_lst,
        'Date': Date_list,
        'Bet On': runners_lst,
        'Runner Id': runners_id_lst,
        'Best Lay Price': lay_price_lst,
        'Best Lay Size': lay_size_lst,
        'Best Back Price': back_price_lst,
        'Best Back Size': back_size_lst
    })
    return final_df


# MAIN FUNCTION!
def GetMatchBookDF(wanted_sport='Soccer', weeks_ahead_to_search=2, wanted_league='UEFA', bet_type='MATCH_ODDS',headers=""):

    # get the wanted sport id.
    sportName = wanted_sport  # USER VAR
    sportIds = getSportId(sportName, headers)

    # get the events for chosen sport. use tags to reach sepc events
    tags = 'uefa-champions-league-qualification,regional'  # USER VAR
    SportEvents = getSportsEvents(sportIds, headers, tags)

    # get the events for a specific league.
    LeagueName = wanted_league  # USER VAR
    LeagueEventsDict = FilterByLeague(SportEvents, LeagueName)
    final_df = GetFinalDf(LeagueEventsDict)

    return final_df, headers


if __name__ == "__main__":
    final_df, headers = GetMatchBookDF()
