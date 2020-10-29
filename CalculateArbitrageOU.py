import json
import sched
import time
import traceback
from _datetime import datetime
from difflib import SequenceMatcher

import pandas as pd
import pulp as p
import requests
from betfairlightweight import filters
from gekko import GEKKO
from numpy import double, long

import SoccerOUBetFair
import SoccerOUMatchBook
from CalculateArbitrage import Solve_And_Place_Arb

prog_log_path = "C:/Users/Administrator/Desktop/ScriptLog/Soccer/OVER_UNDER/prog_log_15_10.csv"
log_info = ''
somthing_happened = False


def PureCalc(betfair, trading, matchbook, headers, c_betfair, c_matchbook, log_times, log_infos, mb_log_dfs,
             bf_log_dfs):
    # for each option we check if there is an arbitrage.
    betfair = betfair[~betfair['Bet On'].str.contains('8.5|7.5|6.5|5.5|4.5')]
    matchbook = matchbook[~matchbook['Bet On'].str.contains('/|1.0|2.0|3.0|4.0|5.0|6.0|7.0|4.5|5.5|6.5|7.5|8.5')]
    betfair = betfair.sort_values('Bet On', kind='mergesort').reset_index(drop=True)
    matchbook = matchbook.sort_values('Bet On', kind='mergesort').reset_index(drop=True)

    # set two dataframes to be the smae with bet on option
    key_cols = ['Bet On']
    betfair = betfair.merge(matchbook.loc[:, matchbook.columns.isin(key_cols)])

    stuff1 = ""
    final_df_to_invest1 = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                                'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                                'net prof:'])
    stuff2 = ""
    final_df_to_invest2 = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                                'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                                'net prof:'])
    for i in range(0, len(betfair)):  # len options for OU
        # min bet size and min liability betfair
        bf_min_bet_size = 3
        bf_min_liability_size = 20

        # min bet size and min liability matchbook
        mb_min_bet_size = 3
        mb_min_liability_size = 10

        # get corresponding market id and selection id in betfair
        market_id = betfair.iloc[i]['Market Id']
        selection_id = long(betfair.iloc[i]['Selection Id'])
        # get corresponding runner id and offers url in matchbook
        runner_id = long(matchbook.iloc[i]['Runner Id'])
        url_offer_matchbook = 'https://api.matchbook.com/edge/rest/v2/offers'
        # Restricting the amount lost to r dollars!
        restriction = 200

        # lay in betfair and back in matchbook
        lay_in = 'Betfair'
        back_in = 'MatchBook'
        betfair_side = 'LAY'
        matchbook_side = 'back'
        bet_on = betfair.iloc[i]['Bet On']
        x_max = betfair.iloc[i]['Best Lay Size']  # max!!
        y_max = matchbook.iloc[i]['Best Back Size']  # max!!
        a = betfair.iloc[i]['Best Lay Price']
        b = matchbook.iloc[i]['Best Back Price']
        c_back = c_matchbook
        c_lay = c_betfair

        # lay in betfair and back in matchbook
        # LOG "right before checking for competability chk :"+ + time
        if b > a and x_max > 1 and y_max > 1:
            final_df_to_invest1, stuff1 = Solve_And_Place_Arb(matchbook.iloc[i], betfair.iloc[i], x_max, y_max, a, b,
                                                            c_back, c_lay,
                                                            bet_on, selection_id,
                                                            runner_id,
                                                            url_offer_matchbook, trading, headers, market_id, lay_in,
                                                            back_in,
                                                            stuff1, betfair_side,
                                                            matchbook_side,
                                                            final_df_to_invest1, mb_min_bet_size, bf_min_bet_size,
                                                            restriction, log_times, log_infos, mb_log_dfs, bf_log_dfs)

        # lay in matchbook and back in betfair
        lay_in = 'MatchBook'
        back_in = 'Betfair'
        betfair_side = 'BACK'
        matchbook_side = 'lay'
        x_max = matchbook.iloc[i]['Best Lay Size']  # max!!
        y_max = betfair.iloc[i]['Best Back Size']  # max!!
        a = matchbook.iloc[i]['Best Lay Price']
        b = betfair.iloc[i]['Best Back Price']
        c_back = c_betfair
        c_lay = c_matchbook

        if b > a and x_max > 1 and y_max > 1:
            final_df_to_invest2, stuff2 = Solve_And_Place_Arb(matchbook.iloc[i], betfair.iloc[i], x_max, y_max, a, b,
                                                            c_back, c_lay,
                                                            bet_on, selection_id,
                                                            runner_id,
                                                            url_offer_matchbook, trading, headers, market_id, lay_in,
                                                            back_in,
                                                            stuff2, betfair_side,
                                                            matchbook_side,
                                                            final_df_to_invest2, mb_min_bet_size, bf_min_bet_size,
                                                            restriction, log_times, log_infos, mb_log_dfs, bf_log_dfs)
    stuff1 += stuff2
    final_df_to_invest1.append(final_df_to_invest2)
    return final_df_to_invest1, stuff1


def CalculateArb(site_1, trading, site_2, headers, c_betfair, c_matchbook):
    # site_1 betfair site_2 Matchbook
    global somthing_happened
    log_times = []
    log_infos = []
    mb_log_dfs = []
    bf_log_dfs = []
    # sort sites df by eventname col alphabeticly and by date for faster search with binary search option:
    site_1 = site_1.sort_values('Event Name', kind='mergesort').reset_index(drop=True)
    site_2 = site_2.sort_values('Event Name', kind='mergesort').reset_index(drop=True)

    stuff = '\nTaken start iteration time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
    df_of_result = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                         'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                         'net prof:'])
    for i2, r2 in site_2.drop_duplicates(subset='Event Name', keep='first').iterrows():
        for i1, r1 in site_1.drop_duplicates(subset='Event Name', keep='first').iterrows():
            # bfname = r1['Event Name']
            # mbname = r2['Event Name']
            if SequenceMatcher(a=r1['Event Name'], b=r2['Event Name']).ratio() >= 0.65:
                t2 = datetime.fromisoformat(r2['Date'][:-1]).strftime('%Y-%m-%d %H:%M:%S')
                t1 = r1['Date'].strftime('%Y-%m-%d %H:%M:%S')
                if t1 == t2:
                    # check for arbitrage:
                    bet_fair_to_chk = site_1.loc[site_1['Event Name'] == r1['Event Name']]
                    bet_fair_to_chk = bet_fair_to_chk.reset_index(drop=True)
                    matchbook_to_chk = site_2.loc[site_2['Event Name'] == r2['Event Name']]
                    matchbook_to_chk = matchbook_to_chk.reset_index(drop=True)

                    df_append_result, tempstuff = PureCalc(bet_fair_to_chk, trading, matchbook_to_chk, headers,
                                                           c_betfair, c_matchbook, log_times, log_infos, mb_log_dfs,
                                                           bf_log_dfs)
                    stuff += tempstuff
                    if ~df_append_result.empty:
                        df_of_result = df_of_result.append(df_append_result, ignore_index=True)
                    break

    if somthing_happened:
        t2 = "C:/Users/Administrator/Desktop/ScriptLog/Soccer/OVER_UNDER/omri_to_chk_15_10.csv"
        t = "C:/Users/Administrator/Desktop/ScriptLog/Soccer/OVER_UNDER/log_15_10.csv"

        tuff = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'

        # write metadata
        with open(t2, "a") as f:
            f.write(tuff)
            f.write('\n BETFAIR \n')

        site_1.to_csv(t2, index=True, mode='a')
        with open(t2, "a") as f:
            f.write("\n")
            f.write('\n MATCHBOOK \n')
        site_2.to_csv(t2, index=True, mode='a')

        # write metadata
        with open(t, "a") as f:
            f.write(stuff)
        # append df to existing file filled by metadata
        df_of_result.to_csv(t, index=False, mode='a')

    with open(prog_log_path, "a") as f:
        for i in range(0, len(log_infos)):
            f.write(log_times[i])
            f.write(log_infos[i])
            if isinstance(mb_log_dfs[i], pd.Series):
                mb_log_dfs[i].to_csv(prog_log_path, index=True, mode='a')
            if isinstance(bf_log_dfs[i], pd.Series):
                bf_log_dfs[i].to_csv(prog_log_path, index=True, mode='a')

    somthing_happened = False
    return


def Main_to_run(headers, trading, sc=None):
    start_time = time.time()

    m_b_df, headers = SoccerOUMatchBook.GetMatchBookDF(headers=headers)
    b_f_df, trading = SoccerOUBetFair.GetBetFairDF(trading=trading)
    # LOG "succsessfully extracted x games in MB and y games in BF" +time
    # x = len(m_b_df['Event Name'].value_counts())
    # y = len(b_f_df['Event Name'].value_counts())
    # log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
    # log_info = '\n succsessfully extracted ' + str(x) + 'games in MB and ' + str(y) + ' games in BF\n'
    # with open(prog_log_path, "a") as f:
    #     f.write(log_time)
    #     f.write(log_info)
    c_matchbook = 0.04
    c_betfair = 0.05

    CalculateArb(b_f_df, trading, m_b_df, headers, c_betfair, c_matchbook)

    # measure time and show on console:
    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
    last_login = datetime.utcnow()
    # first login to api.
    r = SoccerOUMatchBook.login()
    trading = SoccerOUBetFair.login()
    if r.status_code != 200:
        raise ConnectionError(
            'something went wrong connecting to server status code: ' + str(r.status_code))
    # LOG: "Made MB login" + time
    log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
    log_info = '\nfirst login MatchBook and Betfair\n'
    with open(prog_log_path, "a") as f:
        f.write(log_time)
        f.write(log_info)

    SessionTok = r.json()["session-token"]
    headers = {"Content-Type": "application/json;", "session-token": SessionTok}
    while True:
        try:
            now_time = datetime.utcnow()
            delta = now_time - last_login
            if delta.seconds // 3600 > 1:
                # login to api.
                r = SoccerOUMatchBook.login()
                trading = SoccerOUBetFair.login()
                if r.status_code != 200:
                    raise ConnectionError(
                        'something went wrong connecting to server status code: ' + str(r.status_code))
                # LOG: "Made MB login" + time
                log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
                log_info = '\nRelogin MatchBook\n'
                with open(prog_log_path, "a") as f:
                    f.write(log_time)
                    f.write(log_info)
                last_login = datetime.utcnow()
                SessionTok = r.json()["session-token"]
                headers = {"Content-Type": "application/json;", "session-token": SessionTok}
            Main_to_run(headers, trading)
            #     Clean.CleanNames()
        except Exception as ex:
            # LOG: catch exception and log the traceback + time
            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            tb = traceback.format_exc()
            log_info = '\nThere was an exception, trace back is: \n' + tb
            with open(prog_log_path, "a") as f:
                f.write(log_time)
                f.write(log_info)
            print("there was an exeption unrelated to lp solve!!!")
            print(ex)
            continue
