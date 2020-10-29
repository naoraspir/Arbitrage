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

import BetFair
import MatchBook
import telegramBot

prog_log_path = "C:/Users/Administrator/Desktop/ScriptLog/Soccer/Match_Odds/prog_log_15_10.csv"
log_info = ''
somthing_happened= False


# solves and places arb and update log correspondingly !!
def Solve_And_Place_Arb(matchbook, betfair, x_max, y_max, a, b, c_back, c_lay, bet_on, selection_id,
                        runner_id,
                        url_offer_matchbook, trading, headers, market_id, lay_in, back_in, stuff, betfair_side,
                        matchbook_side,
                        final_df_to_invest, mb_min_bet_size, bf_min_bet_size, restriction, log_times, log_infos,
                        mb_log_dfs, bf_log_dfs):
    global somthing_happened
    # LOG "back was higher then lay! :"
    log_time1 = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
    log_info1 = '\n Back in ' + back_in + ' was higher then lay in ' + lay_in + '!, in DataFrames:(matchbook then betfair) \n'
    log_times.append(log_time1)
    log_infos.append(log_info1)
    mb_log_dfs.append(matchbook)
    bf_log_dfs.append(betfair)

    # Create a LP Maximization problem
    m = GEKKO(remote=False)
    m.options.LINEAR = 1
    m.options.SOLVER = 1

    Lp_prob = p.LpProblem('Problem1', p.LpMaximize)
    x = m.Var(lb=1, ub=x_max)
    y = m.Var(lb=1, ub=y_max)
    m_y = (b - 1) * (1 - c_back)
    m_x1 = a - 1
    m_x2 = 1 - c_lay

    # Objective Function
    m.Maximize(m_y * y - m_x1 * x + m_x2 * x - y)

    # Constraints:
    m.Equation(m_y * y - m_x1 * x >= 0)
    m.Equation(m_x2 * x - y >= 0)
    m.Equation(2 * (m_y * y - m_x1 * x) - (m_x2 * x - y) >= 0)
    m.Equation(2 * (m_x2 * x - y) - (m_y * y - m_x1 * x) >= 0)

    # min bet size and liability constraints.
    m.Equation(y >= mb_min_bet_size)
    m.Equation(y <= restriction)
    # # m.Equation(y >= mb_min_liability_size)
    m.Equation(x >= bf_min_bet_size)
    m.Equation(m_x1 * x <= restriction)

    # solve prob:
    # status = Lp_prob.solve()
    try:
        m.solve(disp=False)
        x = round(x.value[0], 2)  # amount to lay
        y = round(y.value[0], 2)  # amount to back
        somthing_happened = True
        # LOG: Found! +arbitrage data+time
        log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
        log_info = '\n Found arbitrage betting on: ' + bet_on + ' back in ' + back_in + ': ' + str(
            y) + ' lay in ' + lay_in + ': ' + str(x) + '\n'
        log_times.append(log_time)
        log_infos.append(log_info)
        mb_log_dfs.append(None)
        bf_log_dfs.append(None)

        print("trying to place bets, found arbitrage!!")
        if betfair_side == "LAY":  # lay in betfair back in match
            limit_order = filters.limit_order(
                size=double(x), price=double(a),  # persistence_type="LAPSE",
                time_in_force="FILL_OR_KILL", min_fill_size=double(x)
            )

            # try order in matchbook
            querystring = {"odds-type": "DECIMAL",
                           "exchange-type": "back-lay",
                           "offers":
                               [{
                                   "runner-id": runner_id,
                                   "side": matchbook_side,
                                   "odds": float(b),
                                   "stake": float(y),
                                   "keep-in-play": False
                               }
                               ]}
        else:  # lay in match back in betfair
            limit_order = filters.limit_order(
                size=double(y), price=double(b),  # persistence_type="LAPSE",
                time_in_force="FILL_OR_KILL", min_fill_size=double(y)
            )
            # try order in matchbook
            querystring = {"odds-type": "DECIMAL",
                           "exchange-type": "back-lay",
                           "offers":
                               [{
                                   "runner-id": runner_id,
                                   "side": matchbook_side,
                                   "odds": float(a),
                                   "stake": float(x),
                                   "keep-in-play": False
                               }
                               ]}
        instruction = filters.place_instruction(
            order_type="LIMIT",
            selection_id=selection_id,
            side=betfair_side,
            limit_order=limit_order,
        )
        rev_if_lay = (x * (1 - c_lay))
        loss_if_lay = y
        prof_net_if_lay_wins = rev_if_lay - loss_if_lay

        # if back wins in matchbook
        rev_if_back = ((y * b) - y) * (1 - c_back)
        loss_if_back = (a * x) - x
        prof_net_if_back_wins = rev_if_back - loss_if_back

        response = requests.request("POST", url_offer_matchbook, data=json.dumps(querystring), headers=headers)
        order_report_MB = response.json()['offers'][0]
        print("MB oreder status: " + order_report_MB['status'])

        if order_report_MB['status'] == "matched":
            # try order in betfair

            order_report_BF = trading.betting.place_orders(
                market_id=market_id, instructions=[instruction]  # list
            )

            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            log_info = '\n Response from matchbook: ' + str(order_report_MB) + '\n'
            log_times.append(log_time)
            log_infos.append(log_info)
            mb_log_dfs.append(None)
            bf_log_dfs.append(None)
            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            log_info = '\n Response from betfair: ' + str(
                order_report_BF.json()) + '\n'#TODO
            log_times.append(log_time)
            log_infos.append(log_info)
            mb_log_dfs.append(None)
            bf_log_dfs.append(None)
            if order_report_BF.place_instruction_reports[0].order_status == 'EXECUTION_COMPLETE':

                text = 'PLACED!!!! lay in ' + lay_in + ' back in ' + back_in + '\n' + 'if ' + back_in + ' wins: ' + str(
                    prof_net_if_back_wins) + '\n' + 'if ' + lay_in + ' wins: ' + str(prof_net_if_lay_wins) + '\n'
                print(text)
                telegramBot.send_msg(text)
            else:
                offer_id = order_report_MB['id']
                cancel_url = 'https://api.matchbook.com/edge/rest/v2/offers/' + str(offer_id)
                response = requests.request("DELETE", cancel_url, headers=headers)
                print(response.text)
                if response.json()['status'] != 'cancelled':
                    text = 'MATCHED in matchbook and DID NOT match in betfair: SOMEONE PLEASE CHECK IF CASHOUT/CANCEL ' \
                           'IS NEEDED AND POSSIBLE in Matchbook or Betfair!!! '
                    telegramBot.send_msg(text)
            print(order_report_MB)
            print(order_report_BF.place_instruction_reports[0].order_status)

        elif order_report_MB['status'] == "failed":
            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            log_info = '\n Arbitrage DID NOT match in MATCHBOOK(someone probably beat us to it), it is either ' \
                       'OPEN\DELEYED: ' + '\n' + str(order_report_MB) + '\n '
            log_times.append(log_time)
            log_infos.append(log_info)
            mb_log_dfs.append(None)
            bf_log_dfs.append(None)
        else:
            offer_id = order_report_MB['id']
            cancel_url = 'https://api.matchbook.com/edge/rest/v2/offers/' + str(offer_id)
            response = requests.request("DELETE", cancel_url, headers=headers)
            print(order_report_MB)
            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            log_info = '\n Arbitrage DID NOT match in MATCHBOOK(someone probably beat us to it), it is either ' \
                       'OPEN\DELEYED: ' + '\n' + str(order_report_MB) + '\n '
            log_times.append(log_time)
            log_infos.append(log_info)
            mb_log_dfs.append(None)
            bf_log_dfs.append(None)
            print(response.text)
            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            log_info = '\n response from cancellation: ' + '\n' + str(
                response.text) + '\n'
            log_times.append(log_time)
            log_infos.append(log_info)
            mb_log_dfs.append(None)
            bf_log_dfs.append(None)
            if response.json()['status'] != 'cancelled':
                text = 'Arbitrage DID NOT match in MATCHBOOK(someone probably beat us to it), it is either OPEN\DELEYED: SOMEONE PLEASE CHECK IF CASHOUT/CANCEL IS NEEDED AND POSSIBLE in MATCHBOOK!!!'
                telegramBot.send_msg(text)

        # lay in betfair and back in matchbook
        stuff += "\ncompered '" + betfair['Event Name'] + "' in betfair to '" + \
                 matchbook[
                     'Event Name'] + "' in matchbook\n"
        mb_win_col = [betfair['Event Name'], betfair['Date'], bet_on, a, x_max, b,
                      y_max,
                      str(y) + ' in ' + back_in,
                      str(x) + ' in ' + lay_in, 'if ' + back_in + ' wins: ' + str(prof_net_if_back_wins)]
        bf_wins_col = [betfair['Event Name'], betfair['Date'], bet_on, a, x_max, b,
                       y_max,
                       str(y) + ' in ' + back_in,
                       str(x) + ' in ' + lay_in, 'if ' + lay_in + ' wins: ' + str(prof_net_if_lay_wins)]
        to_append = pd.DataFrame([mb_win_col, bf_wins_col],
                                 columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price',
                                          'Max Lay Size',
                                          'Best Back Price',
                                          'Max Back Size', 'should back:', 'should lay:', 'net prof:'])
        final_df_to_invest = pd.concat([to_append, final_df_to_invest])
        return final_df_to_invest, stuff

    except Exception as ex:
        print(ex)
        # LOG: catch exception and log the traceback + time
        if 'Solution Not Found' not in str(ex):
            log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
            tb = traceback.format_exc()
            log_info = '\nThere was an exception, trace back is: \n' + tb
            log_times.append(log_time)
            log_infos.append(log_info)
            mb_log_dfs.append(None)
            bf_log_dfs.append(None)
        return final_df_to_invest, stuff


def PureCalc(betfair, trading, matchbook, headers, c_betfair, c_matchbook, log_times, log_infos, mb_log_dfs,
             bf_log_dfs):
    # for each option we check if there is an arbitrage.
    stuff1 = ""
    final_df_to_invest1 = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                               'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                               'net prof:'])
    stuff2 = ""
    final_df_to_invest2 = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                                'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                                'net prof:'])
    for i in range(0, 3):  # 3 options for match odds
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
    stuff1+=stuff2
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
        t2 = "C:/Users/Administrator/Desktop/ScriptLog/Soccer/Match_Odds/omri_to_chk_15_10.csv"
        t = "C:/Users/Administrator/Desktop/ScriptLog/Soccer/Match_Odds/log_15_10.csv"

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

    m_b_df, headers = MatchBook.GetMatchBookDF(wanted_league='Ligue 1', headers=headers)
    # x = len(m_b_df['Event Name'].value_counts())
    b_f_df, trading = BetFair.GetBetFairDF(trading=trading, wanted_league='Ligue 1')
    # y = len(b_f_df['Event Name'].value_counts())
    # LOG "succsessfully extracted x games in MB and y games in BF" +time
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
    r = MatchBook.login()
    trading = BetFair.login()
    if r.status_code != 200:
        raise ConnectionError(
            'something went wrong connecting to server status code: ' + str(r.status_code))
    # LOG: "Made MB login" + time
    log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
    log_info = '\nfirst login MatchBook and betfair\n'
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
                r = MatchBook.login()
                trading = BetFair.login()
                if r.status_code != 200:
                    raise ConnectionError(
                        'something went wrong connecting to server status code: ' + str(r.status_code))
                # LOG: "Made MB login" + time
                log_time = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'
                log_info = '\nRelogin MatchBook and betfair\n'
                with open(prog_log_path, "a") as f:
                    f.write(log_time)
                    f.write(log_info)
                last_login = datetime.utcnow()
                SessionTok = r.json()["session-token"]
                headers = {"Content-Type": "application/json;", "session-token": SessionTok}
            Main_to_run(headers, trading)
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
