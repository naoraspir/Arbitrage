import pandas as pd

def CleanNames():
    betfair_team_names_path = "C:/Users/Administrator/Desktop/ScriptLog/BetFairTeamsName.csv"
    matchbook_team_names_path = "C:/Users/Administrator/Desktop/ScriptLog/MatchBookTeamsName.csv"

    bf = pd.read_csv(betfair_team_names_path)
    del bf['Unnamed: 0']
    bf = bf.drop_duplicates(subset='Bet On', keep='first').sort_values('Bet On', kind='mergesort').reset_index(drop=True)
    bf.to_csv(betfair_team_names_path)

    mb = pd.read_csv(matchbook_team_names_path)
    del mb['Unnamed: 0']
    mb = mb.drop_duplicates(subset='Bet On', keep='first').sort_values('Bet On', kind='mergesort').reset_index(drop=True)
    mb.to_csv(matchbook_team_names_path)


if __name__ == "__main__":
    CleanNames()