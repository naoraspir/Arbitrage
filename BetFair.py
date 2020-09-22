# imports:
import datetime

import betfairlightweight
import pandas as pd


def GetSportId(trading, SportsName):
    # Filter for just the chosen sport
    Sport_filter = betfairlightweight.filters.market_filter(text_query=SportsName)

    # This returns a list
    Sport_event_type = trading.betting.list_event_types(
        filter=Sport_filter)

    # Get the first element of the list
    Sport_event_type = Sport_event_type[0]

    Sport_event_type_id = Sport_event_type.event_type.id
    return Sport_event_type_id


def createDFCompetitions(trading, SportsId, weeksNum):
    # Get a datetime object in a week and convert to string
    datetime_in_a_week = (datetime.datetime.utcnow() + datetime.timedelta(weeks=weeksNum)).strftime("%Y-%m-%dT%TZ")

    # Create a competition filter
    competition_filter = betfairlightweight.filters.market_filter(
        event_type_ids=[SportsId],  # Soccer's event type id is 1
        market_start_time={
            'to': datetime_in_a_week
        })

    # Get a list of competitions for chosen sport
    competitions = trading.betting.list_competitions(
        filter=competition_filter
    )

    # Iterate over the competitions and create a dataframe of competitions and competition ids
    Sport_competitions = pd.DataFrame({
        'Competition': [competition_object.competition.name for competition_object in competitions],
        'ID': [competition_object.competition.id for competition_object in competitions]
    })
    return Sport_competitions


def GetUpcomingEventsIdLst(trading, SportId, daysNum, nation=None, competitionIds=None):
    id_lst = []
    # Define a market filter
    thoroughbreds_event_filter = betfairlightweight.filters.market_filter(
        event_type_ids=[SportId],
        # market_countries=[nation],
        # competition_ids=competitionIds,
        market_start_time={'from': datetime.datetime.utcnow().strftime("%Y-%m-%dT%TZ"),
                           'to': (datetime.datetime.utcnow() + datetime.timedelta(days=daysNum)).strftime("%Y-%m-%dT%TZ")
                           }
    )

    # Get a list of all thoroughbred events as objects
    thoroughbred_events = trading.betting.list_events(
        filter=thoroughbreds_event_filter
    )
    for event in thoroughbred_events:
        id_lst.append(event.event.id)

    return id_lst


def GetFinalDf(trading, event_id_lst, BetType):
    # filter request
    market_catalogue_filter = betfairlightweight.filters.market_filter(event_ids=event_id_lst,
                                                                       market_type_codes=[BetType])
    marketProjection = ['EVENT', 'RUNNER_DESCRIPTION', 'COMPETITION']
    # recive market catalog with all relevant information.
    market_catalogues = trading.betting.list_market_catalogue(
        filter=market_catalogue_filter,
        max_results='1000',
        market_projection=marketProjection
    )

    # create lists for all fields in the data frame
    market_ids_lst = []
    Event_Name_lst = []
    market_ids_for_df=[]
    selection_ids=[]
    Date_list = []
    runners_lst = []
    lay_price_lst = []
    lay_size_lst = []
    back_price_lst = []
    back_size_lst = []

    # sort the catalog to make data match with books.
    market_catalogues.sort(key=lambda x: x.market_id)
    # fill some of the fields with coressponding data
    for market_cat_object in market_catalogues:
        Event_Name_lst.append(market_cat_object.event.name)
        Event_Name_lst.append(market_cat_object.event.name)
        Event_Name_lst.append(market_cat_object.event.name)
        market_ids_for_df.append(market_cat_object.market_id)
        market_ids_for_df.append(market_cat_object.market_id)
        market_ids_for_df.append(market_cat_object.market_id)
        Date_list.append(market_cat_object.event.open_date)
        Date_list.append(market_cat_object.event.open_date)
        Date_list.append(market_cat_object.event.open_date)
        runners_lst.append(market_cat_object.runners[0].runner_name)
        selection_ids.append(market_cat_object.runners[0].selection_id)
        runners_lst.append(market_cat_object.runners[1].runner_name)
        selection_ids.append(market_cat_object.runners[1].selection_id)
        runners_lst.append(market_cat_object.runners[2].runner_name)
        selection_ids.append(market_cat_object.runners[2].selection_id)
        market_ids_lst.append(market_cat_object.market_id)

    # with this criteria its possible to request 100 market ids tops!
    price_filter = betfairlightweight.filters.price_projection(
        ex_best_offers_overrides={'bestPricesDepth': 1},
        price_data=['EX_BEST_OFFERS']
    )

    # make a loop to request up to 400 markets in 4 requests!:
    # recive market books with all relevant information.(for the first batch in size 100)
    market_books = trading.betting.list_market_book(
        market_ids=market_ids_lst[0:100],
        price_projection=price_filter
    )
    j = 100
    for i in range(200, len(market_ids_lst) + 100, 100):
        if j + 100 <= len(market_ids_lst):
            # recive market books with all relevant information.(batches of 100 markets each)
            market_books += trading.betting.list_market_book(
                market_ids=market_ids_lst[j:i],
                price_projection=price_filter
            )
            j = i
        else:
            # recive market books with all relevant information.(for the last batch that is smaller then 100)
            market_books += trading.betting.list_market_book(
                market_ids=market_ids_lst[j:],
                price_projection=price_filter
            )

    # sort the books to make data match with catalougess.
    market_books.sort(key=lambda x: x.market_id)

    # fill the prices and sizes lists for all runners.
    for market_book in market_books:
        for runner in market_book.runners:
            lay_price_lst.append(runner.ex.available_to_lay[0].price
                                 if len(runner.ex.available_to_lay) != 0
                                 else 1.00)
            lay_size_lst.append(runner.ex.available_to_lay[0].size
                                if len(runner.ex.available_to_lay) != 0
                                else 0)
            back_price_lst.append(runner.ex.available_to_back[0].price
                                  if len(runner.ex.available_to_back) != 0
                                  else 1.00)
            back_size_lst.append(runner.ex.available_to_back[0].size
                                 if len(runner.ex.available_to_back) != 0
                                 else 0)

    # Create a DataFrame for each market\event
    final_betfair_table = pd.DataFrame({
        'Event Name': Event_Name_lst,
        'Market Id':market_ids_for_df,
        'Date': Date_list,
        'Bet On': runners_lst,
        'Selection Id':selection_ids,
        'Best Lay Price': lay_price_lst,
        'Best Lay Size': lay_size_lst,
        'Best Back Price': back_price_lst,
        'Best Back Size': back_size_lst
    })

    return final_betfair_table


# MAIN FUNCTION!
def GetBetFairDF(wanted_sport='Soccer', days_ahead_to_search=1, wanted_league='UEFA', bet_type='MATCH_ODDS'):
    # Change this certs path to wherever you're storing your certificates
    certs_path = r'C:\Users\Administrator\Desktop\certs'

    # Change these login details to your own
    my_username = "charlotteemeijer@protonmail.com"
    my_password = "Um3yp6sis0s"
    my_app_key = "l1iIyzDSriFuUeci"

    trading = betfairlightweight.APIClient(username=my_username,
                                           password=my_password,
                                           app_key=my_app_key,
                                           certs=certs_path)

    trading.login()
    ssoid = trading.session_token

    # get the wanted sport id.
    sportName = wanted_sport  # USER VAR
    SportId = GetSportId(trading, sportName)

    # create a data frame with all of the chosen sport's competitions for the next daysNum as a pairs sports name:sport id.
    daysNum = days_ahead_to_search  # USER VAR
    trading.betting.read_timeout=100
    Sport_events_id_lst = GetUpcomingEventsIdLst(trading, SportId, daysNum)
    # SportCompetitions = createDFCompetitions(trading, SportId, daysNum)

    # filter the data frame for the league\competions wanted.
    # LeagueName = wanted_league  # USER VAR
    # SportCompetitionId = SportCompetitions[SportCompetitions.Competition.str.contains(LeagueName)]
    # # SportCompetitionIdList = SportCompetitionId['ID'].tolist() TODO make the request in blocks of 120+- games per request, for now i cut randomly 1st 120
    # SportCompetitionIdList = SportCompetitions['ID'].tolist()

    # get df of market catalogs/books
    BetType = bet_type  # USER VAR
    final_df_betfair = GetFinalDf(trading, Sport_events_id_lst, BetType)

    return final_df_betfair, trading
