import json
import kagglehub
import numpy as np
from os import path
import pandas as pd

from data import team

# Download latest version
PATH = kagglehub.dataset_download("luigibizarro/world-cup-penalty-shootouts-1982-2022")

kt = team.KickingTeam


def _make_games_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    games = set(df.Game_id)

    res = []
    for game in games:
        res_dict = {'game': game}
        temp = df[df.Game_id == game]
        res_dict['n_kicks'] = len(temp)
        # if the last kick is a goal, the team that kicked won
        if temp.iloc[-1].Goal == 1:
            res_dict['winning_team'] = temp.iloc[-1].team_order
            res_dict['winning_country'] = temp.iloc[-1].Team
            res_dict['losing_country'] = temp.iloc[-2].Team
        else:
            res_dict['winning_team'] = temp.iloc[-2].team_order
            res_dict['winning_country'] = temp.iloc[-2].Team
            res_dict['losing_country'] = temp.iloc[-1].Team
        res.append(res_dict)
    df_games = pd.DataFrame(res)
    
    df_games = df_games.merge(
        df[df.Goal == 0].groupby('Game_id')['Penalty_Number'].min().reset_index(),
        left_on='game', right_on='Game_id', how='inner', validate='1:1'
    ).rename(columns={'Penalty_Number': 'first_missed_kick'})
    return df_games


class PKShootout:
    def __init__(self):
        df_all = pd.read_csv(f"{PATH}/WorldCupShootouts.csv")
        self.df_kicks = df_all[df_all.Goal.notna()].copy()
        self.df_kicks["team_order"] = self.df_kicks.Penalty_Number.apply(
            lambda x: kt.team_1.value if int(x) % 2 == 1 else kt.team_2.value
        )
        self.df_games = _make_games_dataframe(self.df_kicks)
        del df_all

        self.n_kicks_attempted = 0
        self.shootout_is_over = False
        self.shootout_team_progress = {
            kt.team_1.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
            kt.team_2.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
        }
        self.kicking_team = kt.team_1

        self.shootout_progress = {
            'kick': list(range(1, 11)),
            'kicks': [],
            'team_1_score': [],
            'team_2_score': [],
            'team_1_probability': [],
            'team_2_probability': [],
        }

        with open(path.join('data', 'probability_dict.json')) as f:
            self.game_probability_dict = json.load(f)

    def kick(self, kick_success: bool = True):
        """A team kicks. Update the counts, scores, probabilities and check if the game is over."""
        if self.shootout_is_over or self.n_kicks_attempted >= 10:
            return None

        kick_success_int = int(kick_success)
        self.n_kicks_attempted += 1
        self.shootout_progress['kicks'].append(kick_success)
        
        # update counts for the kicking team
        self.shootout_team_progress[self.kicking_team.value]['kicks_attempted'] += 1
        self.shootout_team_progress[self.kicking_team.value]['kicks_remaining'] -= 1
        self.shootout_team_progress[self.kicking_team.value]['score'] += kick_success_int
        
        # first check if the shootout has been won
        self.shootout_is_over = self.is_shootout_over()
        # then calculate the probablity for the team ahead
        kick_team_prob = self.calc_win_probability_after_kick(
            team_kicking=self.kicking_team,
            kick_success=kick_success,
            shootout_over=self.shootout_is_over
        )
        self.shootout_team_progress[self.kicking_team.value]['probability'] = kick_team_prob
        
        # update the probability for the team not kicking
        other_team = (
            kt.team_1 if self.kicking_team == kt.team_2 else kt.team_2
        )
        self.shootout_team_progress[other_team.value]['probability'] = 1 - kick_team_prob

        # save results in the running dictionary
        self.shootout_progress['team_1_score'].append(
            self.shootout_team_progress[kt.team_1.value]['score']
        )
        self.shootout_progress['team_2_score'].append(
            self.shootout_team_progress[kt.team_2.value]['score']
        )
        if self.kicking_team == kt.team_1:
            self.shootout_progress['team_1_probability'].append(kick_team_prob)
            self.shootout_progress['team_2_probability'].append(1 - kick_team_prob)
        else:
            self.shootout_progress['team_2_probability'].append(kick_team_prob)
            self.shootout_progress['team_1_probability'].append(1 - kick_team_prob)
        
        # switch the kicking team to the team no longer kicking
        self.switch_kicking_team()

    def switch_kicking_team(self):
        if self.kicking_team == kt.team_1:
            self.kicking_team = kt.team_2
        else:
            self.kicking_team = kt.team_1

    def is_shootout_over(self) -> bool:
        """Check if the team ahead has guaranteed a win."""
        # return false if the shootout is tied
        if (
            self.shootout_team_progress[kt.team_1.value]['score'] ==
            self.shootout_team_progress[kt.team_2.value]['score']
        ):
            return False
        
        # get the score difference and determine who is losing based on this difference
        score_diff = (
            self.shootout_team_progress[kt.team_1.value]['score'] -
            self.shootout_team_progress[kt.team_2.value]['score']
        )
        score_diff_abs = abs(score_diff)
        leading_team = kt.team_1 if score_diff > 0 else kt.team_2
        trailing_team = kt.team_1 if score_diff < 0 else kt.team_2

        # if the trailing team doesn't have enough kicks left, the game is over
        if self.shootout_team_progress[trailing_team.value]['kicks_remaining'] < score_diff_abs:
            # REMOVE THIS PART, WE CAN'T HAVE PRINT STATEMENTS
            print(f"SHOOUTOUT IS OVER: {leading_team.value} WINS")
            return True

        return False

    def calc_win_probability_after_kick(
        self, team_kicking: team.KickingTeam, kick_success: bool, shootout_over: bool = False
    ):
        # if the shootout is over, the kicking team wins on a make and loses on a miss
        if shootout_over:
            if self.kicking_team == team_kicking and kick_success:
                return 1.0
            elif self.kicking_team == team_kicking and not kick_success:
                return 0.0
            elif self.kicking_team != team_kicking and kick_success:
                return 0.0
            else:
                return 1.0
        
         # get each teams score after the result of the kick
        team_1_score = self.shootout_team_progress[kt.team_1.value]['score']
        team_2_score = self.shootout_team_progress[kt.team_2.value]['score']
        
        # pull the probability from the history of world cups
        dict_key = f"{self.n_kicks_attempted}_{team_1_score}_{team_2_score}"
        sub_dict = self.game_probability_dict[dict_key]
        empirical_win_probability = sub_dict.get('win_probability')

        # add in uncertainty if the shootout is not officially over
        if pd.isna(empirical_win_probability):
            win_probability = self.simulate_win_probability()
        else:
            win_probability = empirical_win_probability

        if win_probability >= 0.95:
            return 0.95
        elif win_probability <= 0.05:
            return 0.05
        return win_probability

    def reset_shootout(self):
        self.n_kicks_attempted = 0
        self.shootout_team_progress = {
            kt.team_1.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
            kt.team_2.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
        }
        self.shootout_progress = {
            'kick': list(range(1, 11)),
            'kicks': [],
            'team_1_score': [],
            'team_2_score': [],
            'team_1_probability': [],
            'team_2_probability': [],
        }
        self.kicking_team = kt.team_1
    
    def simulate_win_probability(self, team_kicking: team.KickingTeam, kicks_remaining: int):
        """If we don't have empirical data, we calculate the probability of winning assuming that
        each kick has the same chance of going in"""

        single_kick_prob = self.df_kicks['Goal'].mean()
        
        # we need to consider the current score, the number of kicks remaining
        # if a team is up 4-3 going into the last kick, we should assume they have a
            # ~70% chance to make the kick
            # ~30% chance to save if not
            # ~50% chance if it goes past 10
            # this is an 89.5% chance of winning
        # in general i think i want a binomial distribution calculator
        # as a backup plan, i could shift to 50% and do a binomial but this biases against the 2nd team as theyre less likely to score
        return single_kick_prob

