import json
from os import path
import pandas as pd

from data import team

kt = team.KickingTeam


class PKShootout:
    def __init__(self):
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
        self.shootout_is_over = self.is_shootout_over(
            n_kicks_attempted=self.n_kicks_attempted,
            team_1_score=self.shootout_team_progress[kt.team_1.value]['score'],
            team_2_score=self.shootout_team_progress[kt.team_2.value]['score'],
        )
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

    def is_shootout_over(
        self, n_kicks_attempted: int, team_1_score: int, team_2_score: int,
    ): #  -> tuple[bool, bool | None]
        """Check if the team ahead has guaranteed a win.
        
        If true, also return whether the team that just kicked won"""
        # return false if the shootout is tied
        if team_1_score == team_2_score:
            return False, None
        
        # get the score difference and determine who is losing based on this difference
        score_diff = team_1_score - team_2_score
        score_diff_abs = abs(score_diff)
        leading_team = kt.team_1 if score_diff > 0 else kt.team_2
        trailing_team = kt.team_1 if score_diff < 0 else kt.team_2

        # if the trailing team doesn't have enough kicks left, the game is over
        if n_kicks_attempted % 2 == 0:
            trailing_team_shots_remaining = 5 - n_kicks_attempted / 2
        else:
            if trailing_team == kt.team_1:
                trailing_team_shots_remaining = 5 - ((n_kicks_attempted + 1) / 2)
            else:
                trailing_team_shots_remaining = 5 - ((n_kicks_attempted - 1) / 2)
        # if there are not enough kicks remaining, the shootout is over and the leading team wins
        if trailing_team_shots_remaining < score_diff_abs:
            return True, self.kicking_team == leading_team

        return False

    def calc_win_probability_after_kick(
        self, team_kicking: team.KickingTeam, kick_success: bool, shootout_over: bool = False
    ) -> float:
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

        # if we don't have an empirical probability, simluate kicks until we get to one
        if pd.isna(empirical_win_probability):
            win_probability = self.simulate_win_probability(
                n_kicks_attempted=self.n_kicks_attempted,
                team_1_score=team_1_score,
                team_2_score=team_2_score,
                single_kick_prob=0.7
            )
        else:
            win_probability = empirical_win_probability

        if win_probability >= 0.95:
            return 0.95
        elif win_probability <= 0.05:
            return 0.05
        return win_probability
    
    def simulate_win_probability(
        self,
        n_kicks_attempted: int,
        team_1_score: int,
        team_2_score: int,
        single_kick_prob: float
    ) -> float:
        """TBD - need a detailed description"""
        game_key = f"{n_kicks_attempted}_{team_1_score}_{team_2_score}"
        sub_dict = self.game_probability_dict.get(game_key)
        
        # if we have a win probability, return use (only hit recursively)
        base_win_prob = sub_dict.get('win_probability')
        if pd.notna(base_win_prob):
            return base_win_prob
        
        # check if the shootout is over and return the probability if it is
        shootout_over, kicking_team_wins = self.is_shootout_over(
            n_kicks_attempted=n_kicks_attempted,
            team_1_score=team_1_score,
            team_2_score=team_2_score
        )
        if shootout_over:
            if kicking_team_wins:
                return 1.0
            else:
                return 0.0

        # get the next 2 game keys and their dictionaries
        game_key_miss_next = f"{n_kicks_attempted+1}_{team_1_score}_{team_2_score}"
        # can use the kicking team thing in the code base
        if n_kicks_attempted % 2 == 1:
            game_key_make_next = f"{n_kicks_attempted+1}_{team_1_score}_{team_2_score + 1}"
        else:
            game_key_make_next = f"{n_kicks_attempted+1}_{team_1_score + 1}_{team_2_score}"
        sub_dict_make = self.game_probability_dict[game_key_make_next]
        sub_dict_miss = self.game_probability_dict[game_key_miss_next]

        # pull each of those probabilities
        win_prob_make_next = sub_dict_make.get('win_probability')
        win_prob_miss_next = sub_dict_miss.get('win_probability')

        # if both probabilities exist, return a probability
        if pd.notna(win_prob_make_next) and pd.notna(win_prob_miss_next):
            return (single_kick_prob * win_prob_make_next +
                    (1 - single_kick_prob) * win_prob_miss_next)
        # if we now have a probability on a make, search for probabilities on a miss
        elif pd.notna(win_prob_make_next):
            win_prob_miss_next = self.simulate_win_probability(
                n_kicks_attempted=n_kicks_attempted + 1,
                team_1_score=team_1_score,
                team_2_score=team_2_score
            )
        
        # if we now have a probability on a miss, search for probabilities on a make
        elif pd.notna(win_prob_miss_next):
            if n_kicks_attempted % 2 == 1:
                win_prob_make_next = self.simulate_win_probability(
                    n_kicks_attempted=n_kicks_attempted + 1,
                    team_1_score=team_1_score,
                    team_2_score=team_2_score + 1
                )
            else:
                win_prob_make_next = self.simulate_win_probability(
                    n_kicks_attempted=n_kicks_attempted + 1,
                    team_1_score=team_1_score + 1,
                    team_2_score=team_2_score
                )

        # if neither probability exists, need to search recursively for both
        else:
            if n_kicks_attempted % 2 == 1:
                win_prob_make_next = self.simulate_win_probability(
                    n_kicks_attempted=n_kicks_attempted + 1,
                    team_1_score=team_1_score,
                    team_2_score=team_2_score + 1
                )
            else:
                win_prob_make_next = self.simulate_win_probability(
                    n_kicks_attempted=n_kicks_attempted + 1,
                    team_1_score=team_1_score + 1,
                    team_2_score=team_2_score
                )
            win_prob_miss_next = self.simulate_win_probability(
                n_kicks_attempted=n_kicks_attempted + 1,
                team_1_score=team_1_score,
                team_2_score=team_2_score
            )
        
        return (
            1 - (single_kick_prob * win_prob_make_next +
                 (1 - single_kick_prob) * win_prob_miss_next)
            )
        
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
