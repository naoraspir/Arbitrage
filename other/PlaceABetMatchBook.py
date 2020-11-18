import json

import numpy
import requests

import MatchBook

if __name__ == "__main__":
    m_b_df, headers = MatchBook.GetMatchBookDF(wanted_league='Ligue 1')
    token = headers["session-token"]

    # choose params
    choose_game_index = 0
    event = 'Sandnes Ulf vs Tromsø'
    bet_on = 'Sandnes Ulf'
    a = m_b_df.loc[(m_b_df['Event Name'] == event) & (m_b_df['Bet On'] == bet_on)]['Best Lay Price'].item()
    b = m_b_df.loc[(m_b_df['Event Name'] == event) & (m_b_df['Bet On'] == bet_on)]['Best Back Price'].item()
    # market_id = m_b_df.loc[(m_b_df['Event Name'] == event) & (m_b_df['Bet On'] == bet_on)]['Market Id'].item()
    selection_id = numpy.long(
        m_b_df.loc[(m_b_df['Event Name'] == event) & (m_b_df['Bet On'] == bet_on)]['Runner Id'].item())
    back_or_lay = 'back'
    # url_offer_matchbook = 'https://api.matchbook.com/edge/rest/v2/offers'
    x = 0  # amount to lay in betfair
    y = 3.0  # amount to back in betfair

    # try order in matchbook
    #

    send_offer_url = "https://api.matchbook.com/edge/rest/v2/offers"

    bet_params = {
        "odds-type": "DECIMAL",
        "exchange-type": "back-lay",
        "offers":
            [{
                "runner-id": selection_id,
                "side": "back",
                "odds": b,
                "stake": y,
                "keep-in-play": False
            }
            ]}

    headers = {"Content-Type": "application/json;",'session-token': token}
    response = requests.request("POST", send_offer_url, data=json.dumps(bet_params), headers=headers)
    print(response)
    print()
