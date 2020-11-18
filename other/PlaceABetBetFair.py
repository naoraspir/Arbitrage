import numpy
from betfairlightweight import filters

import BetFair

if __name__ == "__main__":
    trading = BetFair.login()
    b_f_df, trading = BetFair.GetBetFairDF(trading=trading,wanted_league='Ligue 1')

    # choose params
    choose_game_index = 0
    event = 'Torpedo Vladimir v Olimp-Dolgoprudny'
    bet_on = 'The Draw'
    a = b_f_df.loc[(b_f_df['Event Name'] == event) & (b_f_df['Bet On'] == bet_on)]['Best Lay Price'].item()
    b = b_f_df.loc[(b_f_df['Event Name'] == event) & (b_f_df['Bet On'] == bet_on)]['Best Back Price'].item()
    market_id = b_f_df.loc[(b_f_df['Event Name'] == event) & (b_f_df['Bet On'] == bet_on)]['Market Id'].item()
    selection_id = numpy.long(b_f_df.loc[(b_f_df['Event Name'] == event) & (b_f_df['Bet On'] == bet_on)]['Selection Id'].item())
    back_or_lay = 'LAY'
    x = -1  # amount to lay in betfair
    y = 0  # amount to back in betfair

    # try order in betfair

    limit_order = filters.limit_order(
        size=numpy.double(x), price=numpy.double(a),  # persistence_type="LAPSE",
        time_in_force="FILL_OR_KILL", min_fill_size=numpy.double(x)
    )
    instruction = filters.place_instruction(
        order_type="LIMIT",
        selection_id=selection_id,
        side=back_or_lay,
        limit_order=limit_order,
    )
    order_report_BF = trading.betting.place_orders(
        market_id=market_id, instructions=[instruction]  # list
    )
    x=str(order_report_BF.json())
    print(x)
    print(order_report_BF.place_instruction_reports[0].json())
