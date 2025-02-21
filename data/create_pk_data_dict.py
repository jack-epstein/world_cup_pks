import json
import kagglehub
import pandas as pd

import team

# Download latest version
PATH = kagglehub.dataset_download("luigibizarro/world-cup-penalty-shootouts-1982-2022")

kt = team.KickingTeam


def get_df_from_given_score(
    df_base: pd.DataFrame,
    n_kicks_attempted: int,
    team_1_score: int,
    team_2_score: int
) -> pd.DataFrame:
    """Given a score at a point in a shootout, get the dataframe of games/kicks with that score."""
    assert team_1_score + team_2_score <= n_kicks_attempted, (
        "Impossible score given number of kicks"
    )
    assert team_1_score * 2 <= n_kicks_attempted + 1, "Impossible score given number of kicks"
    assert team_2_score * 2 <= n_kicks_attempted, "Impossible score given number of kicks"
    
    # filter the kicks dataframe to only that point in the shootout and pivot by game
    df_kicks_happened = df_base[df_base['Penalty_Number'] <= n_kicks_attempted].copy()
    kick_pivot = df_kicks_happened.pivot_table(
        values='Goal', index='Game_id', columns='team_order', aggfunc='sum'
    ).reset_index()
    if n_kicks_attempted == 1:
        kick_pivot = kick_pivot[
            (kick_pivot[kt.team_1.value] == team_1_score)
        ]
    # after kick 1, we need both teams scores
    else:
        kick_pivot = kick_pivot[
            (kick_pivot[kt.team_1.value] == team_1_score) &
            (kick_pivot[kt.team_2.value] == team_2_score)
        ]
    
    # return the initial dataframe based on the game id in the pivoted and filtered frame
    return df_base[df_base['Game_id'].isin(kick_pivot['Game_id'])].copy()


def calc_kicking_team_probability_after_kick(
    df_kicks_slimmed: pd.DataFrame, df_games: pd.DataFrame,
    n_kicks_attempted: int, team_1_score: int, team_2_score: int
) -> float:
    """Calcluate the probability that the team that just kicked will win the shootout.
    
    Use the get_df_from_given_score to get a filtered dataframe and use those game IDs to cut down
    the games dataframe. With the games dataframe, get the percent of time the team that kicked won
    """
    df_status = get_df_from_given_score(
        df_base=df_kicks_slimmed,
        n_kicks_attempted=n_kicks_attempted,
        team_1_score=team_1_score,
        team_2_score=team_2_score,
    )

    df_games_slim = df_games[df_games.game.isin(df_status.Game_id)]
    team_kicking = kt.team_1.value if n_kicks_attempted % 2 == 1 else kt.team_2.value
    return (df_games_slim.winning_team == team_kicking).mean()


def is_score_possible(
    n_kicks_attempted: int, team_1_score: int, team_2_score: int
):
    # both teams scores cant be greater than attempted kicks
    if team_1_score + team_2_score  > n_kicks_attempted:
        return False
    
    # team 1 can't be 1 more than half of the total kicks
    if team_1_score * 2 > n_kicks_attempted + 1:
        return False
    
    # team 2 can't be more than half of the total kicks
    if team_2_score * 2 > n_kicks_attempted:
        return False
    
    # assuming the previous, all ties are possible
    if team_1_score == team_2_score:
        return True

    # if we have an even number of kicks, both teams have take the same amount
    if n_kicks_attempted % 2 == 0:
        trailing_team_kick_remaining = 5 - n_kicks_attempted / 2
    else:
        # on an odd kick team 2 has an extra kick remaining
        if team_1_score < team_2_score:
            trailing_team_kick_remaining = 5 - (n_kicks_attempted + 1) / 2
        else:
            trailing_team_kick_remaining = 5 - (n_kicks_attempted - 1) / 2

    # if the previous kick
    if trailing_team_kick_remaining + 1 < abs(team_2_score - team_1_score):
        return False

    return True


def main():
    df_all = pd.read_csv(f"{PATH}/WorldCupShootouts.csv")
    
    # get a dataframe of all kicks
    df_kicks = df_all[df_all.Goal.notna()].copy()
    df_kicks["team_order"] = df_kicks.Penalty_Number.apply(
        lambda x: kt.team_1.value if int(x) % 2 == 1 else kt.team_2.value
    )

    # get a dataframe of all games
    games = set(df_kicks.Game_id)
    res = []
    for game in games:
        res_dict = {'game': game}
        temp = df_kicks[df_kicks.Game_id == game]
        res_dict['n_kicks'] = len(temp)
        # if the last kick is a goal, the team that kicked won
        if temp.iloc[-1].Goal == 1:
            res_dict['winning_team'] = temp.iloc[-1].team_order
        else:
            res_dict['winning_team'] = temp.iloc[-2].team_order
        res.append(res_dict)
    df_games = pd.DataFrame(res)

    # for every possible score at any point in a shootout, get the probability of winning
    probability_dict = {}
    n_kicks_list = list(range(1, 11))
    n_goals_list = list(range(0, 6))
    for n_kicks in n_kicks_list:
        for n_goals_team_1 in n_goals_list:
            for n_goals_team_2 in n_goals_list:
                win_probability = None
                if is_score_possible(
                    n_kicks_attempted=n_kicks,
                    team_1_score=n_goals_team_1,
                    team_2_score=n_goals_team_2
                ):
                    # logic for 10 kicks
                    if n_kicks == 10:
                        # if it's a tie set to 0.5
                        if n_goals_team_1 == n_goals_team_2:
                            win_probability = 0.5
                        # if not a tie, team 2 just kicked so assume they lose with a lower score
                        elif n_goals_team_1 > n_goals_team_2:
                            win_probability = 0.0
                        else:
                            win_probability = 1.0

                    if pd.isna(win_probability):
                        try:
                            df_kicks_slim = get_df_from_given_score(
                                df_base=df_kicks,
                                n_kicks_attempted=n_kicks,
                                team_1_score=n_goals_team_1,
                                team_2_score=n_goals_team_2
                            )
                            win_probability = calc_kicking_team_probability_after_kick(
                                df_kicks_slimmed=df_kicks_slim,
                                df_games=df_games,
                                n_kicks_attempted=n_kicks,
                                team_1_score=n_goals_team_1,
                                team_2_score=n_goals_team_2
                            )
                        except KeyError:
                            win_probability = None
                    dict_key = f"{n_kicks}_{n_goals_team_1}_{n_goals_team_2}"
                    probability_dict[dict_key] = {
                        'n_kicks_attempted': n_kicks,
                        'team_1_score': n_goals_team_1,
                        'team_2_score': n_goals_team_2,
                        'win_probability': win_probability
                    }

    with open('probability_dict.json', 'w') as fp:
        json.dump(probability_dict, fp)


if __name__ == "__main__":
    main()
