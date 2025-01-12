from enum import Enum
import kagglehub
import numpy as np
import pandas as pd

# Download latest version
PATH = kagglehub.dataset_download("luigibizarro/world-cup-penalty-shootouts-1982-2022")


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


class KickingTeam(Enum):
    team_1 = "team_1"
    team_2 = "team_2"


class PKShootout:
    def __init__(self):
        df_all = pd.read_csv(f"{PATH}/WorldCupShootouts.csv")
        self.df_kicks = df_all[df_all.Goal.notna()].copy()
        self.df_kicks["team_order"] = self.df_kicks.Penalty_Number.apply(
            lambda x: KickingTeam.team_1.value if int(x) % 2 == 1 else KickingTeam.team_2.value
        )
        self.df_games = _make_games_dataframe(self.df_kicks)
        del df_all

        self.n_kicks_attempted = 0
        self.shootout_is_over = False
        self.shootout_team_progress = {
            KickingTeam.team_1.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
            KickingTeam.team_2.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
        }
        self.kicking_team = KickingTeam.team_1

        self.shootout_progress = {
            'kick': list(range(1, 11)),
            'kicks': [],
            'team_1_score': [],
            'team_2_score': [],
            'team_1_probability': [],
            'team_2_probability': [],
        }

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
        kick_team_prob = self.calc_kicking_team_probability_after_kick(
            team_kicking=self.kicking_team,
            kick_success=kick_success,
            is_shootout_over=self.shootout_is_over
        )
        self.shootout_team_progress[self.kicking_team.value]['probability'] = kick_team_prob
        
        # update the probability for the team not kicking
        other_team = (
            KickingTeam.team_1 if self.kicking_team == KickingTeam.team_2 else KickingTeam.team_2
        )
        self.shootout_team_progress[other_team.value]['probability'] = 1 - kick_team_prob

        # save results in the running dictionary
        self.shootout_progress['team_1_score'].append(
            self.shootout_team_progress[KickingTeam.team_1.value]['score']
        )
        self.shootout_progress['team_2_score'].append(
            self.shootout_team_progress[KickingTeam.team_2.value]['score']
        )
        if self.kicking_team == KickingTeam.team_1:
            self.shootout_progress['team_1_probability'].append(kick_team_prob)
            self.shootout_progress['team_2_probability'].append(1 - kick_team_prob)
        else:
            self.shootout_progress['team_2_probability'].append(kick_team_prob)
            self.shootout_progress['team_1_probability'].append(1 - kick_team_prob)
        
        # switch the kicking team to the team no longer kicking
        self.switch_kicking_team()

    def switch_kicking_team(self):
        if self.kicking_team == KickingTeam.team_1:
            self.kicking_team = KickingTeam.team_2
        else:
            self.kicking_team = KickingTeam.team_1

    def is_shootout_over(self) -> bool:
        """Check if the team ahead has guaranteed a win."""
        # return false if the shootout is tied
        if (
            self.shootout_team_progress[KickingTeam.team_1.value]['score'] ==
            self.shootout_team_progress[KickingTeam.team_2.value]['score']
        ):
            return False
        
        # get the score difference and determine who is losing based on this difference
        score_diff = (
            self.shootout_team_progress[KickingTeam.team_1.value]['score'] -
            self.shootout_team_progress[KickingTeam.team_2.value]['score']
        )
        score_diff_abs = abs(score_diff)
        leading_team = KickingTeam.team_1 if score_diff > 0 else KickingTeam.team_2
        trailing_team = KickingTeam.team_1 if score_diff < 0 else KickingTeam.team_2

        # if the trailing team doesn't have enough kicks left, the game is over
        if self.shootout_team_progress[trailing_team.value]['kicks_remaining'] < score_diff_abs:
            # REMOVE THIS PART, WE CAN'T HAVE PRINT STATEMENTS
            print(f"SHOOUTOUT IS OVER: {leading_team.value} WINS")
            return True

        return False

    def calc_kicking_team_probability_after_kick(
        self, team_kicking: KickingTeam, kick_success: bool, is_shootout_over: bool = False
    ) -> float:
        """Calcluate the probability that the kicking team will win the shootout."""
        # if the shootout is over, the kicking team wins on a make and loses on a miss
        if is_shootout_over:
            if self.kicking_team == team_kicking and kick_success:
                return 1.0
            elif self.kicking_team == team_kicking and not kick_success:
                return 0.0
            elif self.kicking_team != team_kicking and kick_success:
                return 0.0
            else:
                return 1.0
        
        # if we have done 10 kicks and the shootout is tied, set to 50%
        if (
            self.n_kicks_attempted == 10 and (
                self.shootout_team_progress[KickingTeam.team_1.value]['score'] ==
                self.shootout_team_progress[KickingTeam.team_2.value]['score']
            )
        ):
            return 0.5
        
        # get each teams score after the result of the kick
        team_1_score = self.shootout_team_progress[KickingTeam.team_1.value]['score']
        team_2_score = self.shootout_team_progress[KickingTeam.team_2.value]['score']
        
        # get a slimmed dataframe with possible shootout outcomes given the result of the kick
        df_status = self.get_df_from_given_score(
            self.df_kicks,
            n_kicks_attempted=self.n_kicks_attempted,
            team_1_score=team_1_score,
            team_2_score=team_2_score,
        )

        # filter to the historical games that this score associates with
        df_games_slim = self.df_games[self.df_games.game.isin(df_status.Game_id)]
        
        prob_kicking_team_wins = (df_games_slim.winning_team == team_kicking.value).mean()
        if prob_kicking_team_wins >= 0.95:
            return 0.95
        elif prob_kicking_team_wins <= 0.05:
            return 0.05
        return prob_kicking_team_wins

    def get_df_from_given_score(
        self,
        df_base: pd.DataFrame,
        n_kicks_attempted: int,
        team_1_score: int,
        team_2_score: int
    ) -> pd.DataFrame:
        """Given a score at any point in a shootout, return the dataframe of available games"""
        assert team_1_score + team_2_score <= n_kicks_attempted, (
            "Impossible score given number of kicks"
        )
        assert team_1_score * 2 <= n_kicks_attempted + 1, "Impossible score given number of kicks"
        assert team_2_score * 2 <= n_kicks_attempted, "Impossible score given number of kicks"
        
        df_kicks_happened = df_base[df_base['Penalty_Number'] <= n_kicks_attempted].copy()
        kick_pivot = df_kicks_happened.pivot_table(
            values='Goal', index='Game_id', columns='team_order', aggfunc='sum'
        ).reset_index()
        # if this was the first kick, we only care about the result of the first teams kick
        if n_kicks_attempted == 1:
            kick_pivot = kick_pivot[
                (kick_pivot[KickingTeam.team_1.value] == team_1_score)
            ]
        # after kick 1, we need both teams scores
        else:
            kick_pivot = kick_pivot[
                (kick_pivot[KickingTeam.team_1.value] == team_1_score) &
                (kick_pivot[KickingTeam.team_2.value] == team_2_score)
            ]
        
        return df_base[df_base['Game_id'].isin(kick_pivot['Game_id'])].copy()

    def reset_shootout(self):
        self.n_kicks_attempted = 0
        self.shootout_team_progress = {
            KickingTeam.team_1.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
            KickingTeam.team_2.value: {
                'kicks_attempted': 0,
                'kicks_remaining': 5,
                'score': 0,
                'probability': 0.5,
            },
        }
        self.kicking_team = KickingTeam.team_1
    
    def simulate_remaining_shootout(self, team_kicking: KickingTeam, kicks_remaining: int):
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

