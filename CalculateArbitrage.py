import json
import sched
import time
from _datetime import datetime
from difflib import SequenceMatcher
import pulp as p
import pandas as pd
import requests
from betfairlightweight import filters
from gekko import GEKKO
from numpy import double, long

import TeamNamesCleaner as Clean
import BetFair
import MatchBook
import betfairlightweight

s = sched.scheduler(time.time, time.sleep)


def PureCalc(betfair, trading, matchbook, headers, c_betfair, c_matchbook):
    # for each option we check if there is an arbitrage.
    # sort to match the criteria:

    stuff = ""
    final_df_to_invest = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                               'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                               'net prof:'])
    for i in range(0, 3):
        # lay in betfair and back in matchbook
        bet_on = betfair.iloc[i]['Bet On']
        x_max = betfair.iloc[i]['Best Lay Size']  # max!!
        y_max = matchbook.iloc[i]['Best Back Size']  # max!!
        a = betfair.iloc[i]['Best Lay Price']
        b = matchbook.iloc[i]['Best Back Price']
        c_1 = c_matchbook
        c_2 = c_betfair

        # min bet size and min liability betfair
        bf_min_bet_size = 3
        bf_min_liability_size = 20

        # min bet size and min liability matchbook
        mb_min_bet_size = 1
        mb_min_liability_size = 10

        # get corresponding market id and selection id in betfair
        market_id = betfair.iloc[i]['Market Id']
        selection_id = long(betfair.iloc[i]['Selection Id'])
        # get corresponding runner id and offers url in matchbook
        runner_id = long(matchbook.iloc[i]['Runner Id'])
        url_offer_matchbook = 'https://api.matchbook.com/edge/rest/v2/offers'
        # Restricting the amount lost to r dollars!
        r = 100

        # lay in betfair and back in matchbook
        if b > a and x_max >= 1 and y_max >= 1:
            # Create a LP Maximization problem
            m = GEKKO(remote=False)
            m.options.LINEAR = 1
            m.options.SOLVER = 1

            Lp_prob = p.LpProblem('Problem1', p.LpMaximize)
            # p.LpVariable("x1", 1, x_max,cat=p.LpInteger)
            x = m.Var(lb=1, ub=x_max)
            # p.LpVariable("y1", 1, y_max, cat=p.LpInteger)
            y = m.Var(lb=1, ub=y_max)
            m_y = (b - 1) * (1 - c_1)
            m_x1 = a - 1
            m_x2 = 1 - c_2

            # Objective Function
            # Lp_prob += m_y * y - m_x1 * x + m_x2 * x - y
            m.Maximize(m_y * y - m_x1 * x + m_x2 * x - y)

            # Constraints:
            # Lp_prob += m_y * y - m_x1 * x >= 0
            # Lp_prob += m_x2 * x - y >= 0
            m.Equation(m_y * y - m_x1 * x >= 0)
            m.Equation(m_x2 * x - y >= 0)

            # min bet size and liability constraints.
            m.Equation(y >= mb_min_bet_size)
            m.Equation(y <= r)
            # m.Equation(y >= mb_min_liability_size)

            m.Equation(x >= bf_min_bet_size)
            m.Equation(m_x1 * x <= r)

            # solve prob:
            # status = Lp_prob.solve()
            try:
                m.solve(disp=False)
                # lay in betfair and back in matchbook
                x = round(x.value[0], 2)  # amount to lay in betfair
                y = round(y.value[0], 2)  # amount to back in MatchBook
                # TODO get: trading for BETFAIR and headers for MATCHBOOK, MARKET ID , SELECTION ID , LAY OR BACK
                # try order in matchbook
                querystring = {"odds-type": "DECIMAL",
                               "exchange-type": "back-lay",
                               "offers":
                                   [{
                                       "runner-id": runner_id,
                                       "side": "back",
                                       "odds": float(b),
                                       "stake": float(y),
                                       "keep-in-play": False
                                   }
                                   ]}

                response = requests.request("POST", url_offer_matchbook, data=json.dumps(querystring), headers=headers)
                order_report_MB = response.json()['offers'][0]

                offer_id = order_report_MB['id']

                if (order_report_MB['status'] == "matched"):
                    # try order in betfair
                    limit_order = filters.limit_order(
                        size=double(x), price=double(a),  # persistence_type="LAPSE",
                        time_in_force="FILL_OR_KILL", min_fill_size=double(x)
                    )
                    instruction = filters.place_instruction(
                        order_type="LIMIT",
                        selection_id=selection_id,
                        side="LAY",
                        limit_order=limit_order,
                    )
                    order_report_BF = trading.betting.place_orders(
                        market_id=market_id, instructions=[instruction]  # list
                    )

                    print(order_report_MB)
                    print(order_report_BF.place_instruction_reports[0].order_status)

                    # if order_report_BF.status == 'SUCCESS' and order_report_MB['status'] == "matched":
                    #     if order_report_BF.place_instruction_reports[0].order_status == 'EXECUTION_COMPLETE':
                    #         for order in order_report_BF.place_instruction_reports:
                    #             print(
                    #                 "in BetFair : Status: {0}, BetId: {1}, Average Price Matched: {2}\n".format(
                    #                     order.status,
                    #                     order.bet_id,
                    #                     order.average_price_matched
                    #                 )
                    #             )
                    #         print(order_report_MB['matched-bets'][0])
                    # else:
                    #     print('status of failed in betfair?: ' + order_report_BF.place_instruction_reports[
                    #         0].error_code + '\n')
                    #     print('status of failed in matchbook?: ' + order_report_MB['status'])

                    # if lay in betfair wins:
                    rev_if_betfair = (x * (1 - c_betfair))
                    loss_if_betfair = y
                    prof_net_if_betfair_wins = rev_if_betfair - loss_if_betfair

                    # if back wins in matchbook
                    rev_if_matchbook = ((y * b) - y) * (1 - c_matchbook)
                    loss_if_matchbook = (a * x) - x
                    prof_net_if_matchbook_wins = rev_if_matchbook - loss_if_matchbook

                    # lay in betfair and back in matchbook
                    stuff += "\ncompered '" + betfair.iloc[i]['Event Name'] + "' in betfair to '" + matchbook.iloc[i][
                        'Event Name'] + "' in matchbook\n"
                    mb_win_col = [betfair.iloc[i]['Event Name'], betfair.iloc[i]['Date'], bet_on, a, x_max, b, y_max,
                                  str(y) + ' in MatchBook',
                                  str(x) + ' in Betfair', 'if matchbook wins: ' + str(prof_net_if_matchbook_wins)]
                    bf_wins_col = [betfair.iloc[i]['Event Name'], betfair.iloc[i]['Date'], bet_on, a, x_max, b, y_max,
                                   str(y) + ' in MatchBook',
                                   str(x) + ' in Betfair', 'if betfair wins: ' + str(prof_net_if_betfair_wins)]
                    to_append = pd.DataFrame([mb_win_col, bf_wins_col],
                                             columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                                      'Best Back Price',
                                                      'Max Back Size', 'should back:', 'should lay:', 'net prof:'])
                    final_df_to_invest = pd.concat([to_append, final_df_to_invest])
                    print("FOUND!!!! lay in betfair back in matchbook")
                else:
                    cancel_url = 'https://api.matchbook.com/edge/rest/v2/offers/offer_id'
                    response = requests.request("DELETE", cancel_url, headers=headers)

                    print(response.text)

            except Exception as ex:
                print(ex)

        # lay in matchbook and back in betfair
        bet_on = matchbook.iloc[i]['Bet On']
        x_max = matchbook.iloc[i]['Best Lay Size']  # max!!
        y_max = betfair.iloc[i]['Best Back Size']  # max!!
        a = matchbook.iloc[i]['Best Lay Price']
        b = betfair.iloc[i]['Best Back Price']
        c_1 = c_betfair
        c_2 = c_matchbook

        if b > a and x_max >= 1 and y_max >= 1:
            # Create a LP Maximization problem
            # Lp_prob2 = p.LpProblem('Problem2', p.LpMaximize)
            m2 = GEKKO(remote=False)
            m2.options.LINEAR = 1
            m2.options.SOLVER = 1

            x2 = m2.Var(lb=1, ub=x_max)  # p.LpVariable("x2", 1, x_max,cat=p.LpInteger)
            y2 = m2.Var(lb=1, ub=y_max)  # p.LpVariable("y2", 1, y_max,cat=p.LpInteger)
            m_y = (b - 1) * (1 - c_1)
            m_x1 = a - 1
            m_x2 = 1 - c_2

            # Objective Function
            # Lp_prob2 += m_y * y2 - m_x1 * x2 + m_x2 * x2 - y2
            m2.Maximize(m_y * y2 - m_x1 * x2 + m_x2 * x2 - y2)

            # Constraints:
            # Lp_prob2 += m_y * y2 - m_x1 * x2 >= 0
            # Lp_prob2 += m_x2 * x2 - y2 >= 0
            m2.Equation(m_y * y2 - m_x1 * x2 >= 0)
            m2.Equation(m_x2 * x2 - y2 >= 0)

            # min bet size and liability constraints.
            m2.Equation(y2 >= bf_min_bet_size)
            m2.Equation(y2 <= r)
            # m.Equation(y >= mb_min_liability_size)

            m2.Equation(x2 >= mb_min_bet_size)
            m2.Equation(m_x1 * x2 <= r)

            # solve prob:
            # status = Lp_prob2.solve()
            # lay in matchbook and back in betfair
            try:
                m2.solve(disp=False)
                x2 = round(x2.value[0], 2)
                y2 = round(y2.value[0], 2)

                # try order in matchbook
                querystring = {"odds-type": "DECIMAL",
                               "exchange-type": "back-lay",
                               "offers":
                                   [{
                                       "runner-id": runner_id,
                                       "side": "lay",
                                       "odds": float(a),
                                       "stake": float(x2),
                                       "keep-in-play": False
                                   }
                                   ]}

                response = requests.request("POST", url_offer_matchbook, data=json.dumps(querystring), headers=headers)
                order_report_MB = response.json()['offers'][0]
                offer_id = order_report_MB['id']

                if order_report_MB['status'] == "matched":#TODO cancel matchbook if order in betfair is not completed
                    limit_order = filters.limit_order(
                        size=double(y2), price=double(b),  # persistence_type="LAPSE",
                        time_in_force="FILL_OR_KILL", min_fill_size=double(y2)
                    )
                    instruction = filters.place_instruction(
                        order_type="LIMIT",
                        selection_id=selection_id,
                        side="BACK",
                        limit_order=limit_order,
                    )
                    order_report_BF = trading.betting.place_orders(
                        market_id=market_id, instructions=[instruction]  # list
                    )

                    print(order_report_MB)
                    print(order_report_BF.place_instruction_reports[0].order_status)
                    rev_if_matchbook = (x2 * (1 - c_matchbook))
                    loss_if_matchbook = y2
                    prof_net_if_matchbook_wins = rev_if_matchbook - loss_if_matchbook

                    # if back wins in betfair
                    rev_if_betfair = ((y2 * b) - y2) * (1 - c_betfair)
                    loss_if_betfair = (a * x2) - x2
                    prof_net_if_betfair_wins = rev_if_betfair - loss_if_betfair

                    stuff += "\ncompered '" + betfair.iloc[i]['Event Name'] + "' in betfair to '" + matchbook.iloc[i][
                        'Event Name'] + "' in matchbook\n"

                    mb_win_col = [betfair.iloc[i]['Event Name'], betfair.iloc[i]['Date'], bet_on, a, x_max, b, y_max,
                                  str(y2) + ' in Betfair',
                                  str(x2) + ' in MatchBook', 'if matchbook wins: ' + str(prof_net_if_matchbook_wins)]
                    bf_wins_col = [betfair.iloc[i]['Event Name'], betfair.iloc[i]['Date'], bet_on, a, x_max, b, y_max,
                                   str(y2) + ' in Betfair',
                                   str(x2) + ' in MatchBook', 'if betfair wins: ' + str(prof_net_if_betfair_wins)]

                    to_append = pd.DataFrame([mb_win_col, bf_wins_col],
                                             columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                                      'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                                      'net prof:'])
                    final_df_to_invest = pd.concat([to_append, final_df_to_invest])
                    print(
                        "FOUND!!!! lay in matchbook and back in betfair")
                else:
                    cancel_url = 'https://api.matchbook.com/edge/rest/v2/offers/'+offer_id
                    response = requests.request("DELETE", cancel_url, headers=headers)

                    print(response.text)
            except Exception as e:
                print(e)

    return final_df_to_invest, stuff


def CalculateArb(site_1, trading, site_2, headers, c1, c2):
    # site_1 betfair site_2 Matchbook

    t = "C:/Users/Administrator/Desktop/ScriptLog/omri_to_chk10.csv"
    tuff = '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'

    # write metadata
    with open(t, "a") as f:
        f.write(tuff)
        f.write('\n BETFAIR \n')

    site_1.to_csv(t, index=True, mode='a')
    with open(t, "a") as f:
        f.write("\n")
        f.write('\n MATCHBOOK \n')
    site_2.to_csv(t, index=True, mode='a')  # TODO omri to chk is now disabled

    # sort sites df by eventname col alphabeticly and by date for faster search with binary search option:

    site_1 = site_1.sort_values('Event Name', kind='mergesort').reset_index(drop=True)
    site_2 = site_2.sort_values('Event Name', kind='mergesort').reset_index(drop=True)

    # append all names of the teams to csv of names, ne for each site:
    betfair_team_names_path = "C:/Users/Administrator/Desktop/ScriptLog/BetFairTeamsName.csv"
    q = site_1.loc[:, 'Bet On']
    q.to_csv(betfair_team_names_path, index=True, mode='a')
    matchbook_team_names_path = "C:/Users/Administrator/Desktop/ScriptLog/MatchBookTeamsName.csv"
    q = site_2.loc[:, 'Bet On']
    q.to_csv(matchbook_team_names_path, index=True,
             mode='a')  # TODO make a seperate code for this searching historical data api. in match book chk how also.

    stuff = ""
    df_of_result = pd.DataFrame(columns=['Event Name', 'Date', 'Bet On', 'Best Lay Price', 'Max Lay Size',
                                         'Best Back Price', 'Max Back Size', 'should back:', 'should lay:',
                                         'net prof:'])
    for i2, r2 in site_2.drop_duplicates(subset='Event Name', keep='first').iterrows():
        for i1, r1 in site_1.drop_duplicates(subset='Event Name', keep='first').iterrows():
            bfname = r1['Event Name']
            mbname = r2['Event Name']
            if (SequenceMatcher(a=r1['Event Name'], b=r2['Event Name']).ratio() >= 0.65):
                # check for arbitrage:
                bet_fair_to_chk = site_1.loc[site_1['Event Name'] == r1['Event Name']]
                # del bet_fair_to_chk['index']
                bet_fair_to_chk = bet_fair_to_chk.reset_index(drop=True)
                matchbook_to_chk = site_2.loc[site_2['Event Name'] == r2['Event Name']]
                # del matchbook_to_chk['index']
                matchbook_to_chk = matchbook_to_chk.reset_index(drop=True)

                df_append_result, tempstuff = PureCalc(bet_fair_to_chk, trading, matchbook_to_chk, headers, c1, c2)
                stuff += tempstuff
                df_of_result = df_of_result.append(df_append_result, ignore_index=True)
                break

    t = "C:/Users/Administrator/Desktop/ScriptLog/log15.csv"
    stuff += '\nTaken time: ' + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + '\n'

    # write metadata
    with open(t, "a") as f:
        f.write(stuff)
    df_of_result.drop_duplicates(keep='first', inplace=True)
    # append df to existing file filled by metadata
    df_of_result.to_csv(t, index=False, mode='a')
    return df_of_result


def Main_to_run(sc=None):
    start_time = time.time()

    m_b_df, headers = MatchBook.GetMatchBookDF(wanted_league='Ligue 1')
    b_f_df, trading = BetFair.GetBetFairDF(wanted_league='Ligue 1')
    c_matchbook = 0.04
    c_betfair = 0.05

    CalculateArb(b_f_df, trading, m_b_df, headers, c_betfair, c_matchbook)

    # measure time and show on console:
    print("--- %s seconds ---" % (time.time() - start_time))
    # r = MatchBook.logout(headers)
    # if r.status_code == 200:
    #     print("Logged out successfully")
    # else:
    #     print(r.text)
    # s.enter(15, 1, Main_to_run, (sc,))


if __name__ == "__main__":
    # s.enter(15, 1, Main_to_run, (s,))
    # s.run()
    counter = 0
    while True:
        try:
            Main_to_run()
            counter += 1
            if counter == 1000:
                counter = 0
                Clean.CleanNames()
        except Exception as ex:
            print("there was an exeption unrelated to lp solve!!!")
            print(ex)
            continue
