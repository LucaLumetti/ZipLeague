from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class Player(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    elo_rating = models.IntegerField(default=1000) # Initial ELO
    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def win_percentage(self):
        if self.matches_played == 0:
            return 0
        return (self.matches_won / self.matches_played) * 100

class Match(models.Model):
    team1_player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team1_player1')
    team1_player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team1_player2')
    team2_player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team2_player1')
    team2_player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team2_player2')
    
    team1_score = models.IntegerField() # Scores must be explicitly provided
    team2_score = models.IntegerField() # Scores must be explicitly provided
    date_played = models.DateTimeField(default=timezone.now)
    
    class MatchResult(models.TextChoices):
        TEAM1_WIN = 'team1_win', 'Team 1 Win'
        TEAM2_WIN = 'team2_win', 'Team 2 Win'
    
    result = models.CharField(
        max_length=10,
        choices=MatchResult.choices,
        # Result is determined by scores in save() or clean()
    )
    elo_change = models.IntegerField(default=0)

    def __str__(self):
        team1_str = f"{self.team1_player1.name} & {self.team1_player2.name}"
        team2_str = f"{self.team2_player1.name} & {self.team2_player2.name}"
        return f"{team1_str} vs {team2_str} - {self.date_played.strftime('%Y-%m-%d')}"

    def clean(self):
        super().clean()
        if hasattr(self, 'team1_score') and hasattr(self, 'team2_score'): # Ensure scores are present before comparing
            if self.team1_score == self.team2_score:
                raise ValidationError("Match scores cannot be equal; draws are not allowed.")
        
        # Ensure all four players are distinct
        players_in_match = [self.team1_player1, self.team1_player2, self.team2_player1, self.team2_player2]
        if len(players_in_match) != len(set(players_in_match)):
            raise ValidationError("All four players in a match must be distinct.")


    def save(self, *args, **kwargs):
        # Determine match result from scores before saving
        if self.team1_score > self.team2_score:
            self.result = self.MatchResult.TEAM1_WIN
        elif self.team2_score > self.team1_score:
            self.result = self.MatchResult.TEAM2_WIN
        # If scores are equal, self.clean() should have raised an error if called by a form/admin.
        # If this save is called directly without clean, this state is problematic.
        # However, forms will call clean(). For direct saves, ensure clean() is called or logic is duplicated.

        is_new_match = self.pk is None
        
        # Call full_clean before saving to ensure model validation, including clean() method
        if is_new_match: # Or always, depending on desired strictness for updates too
             self.full_clean()

        super().save(*args, **kwargs)

        if is_new_match and not hasattr(self, '_stats_updated'):
            self.update_player_stats()
            self._stats_updated = True
    
    def update_player_stats(self):
        """Updates player ELO ratings and win/loss records after a match."""
        players = [self.team1_player1, self.team1_player2, self.team2_player1, self.team2_player2]
        
        for player in players:
            player.matches_played += 1
        
        team1_avg_elo = (self.team1_player1.elo_rating + self.team1_player2.elo_rating) / 2
        team2_avg_elo = (self.team2_player1.elo_rating + self.team2_player2.elo_rating) / 2
        
        expected_team1 = 1 / (1 + 10 ** ((team2_avg_elo - team1_avg_elo) / 400))
        k_factor = 32
        actual_team1_score_val = 1 if self.result == self.MatchResult.TEAM1_WIN else 0
        
        elo_delta = round(k_factor * (actual_team1_score_val - expected_team1))
        self.elo_change = abs(elo_delta)

        # Team 1 gets +/- elo_delta, Team 2 gets -/+ elo_delta
        team1_multiplier = 1 if self.result == self.MatchResult.TEAM1_WIN else -1
        self.team1_player1.elo_rating += team1_multiplier * abs(elo_delta)
        self.team1_player2.elo_rating += team1_multiplier * abs(elo_delta)
        self.team2_player1.elo_rating -= team1_multiplier * abs(elo_delta)
        self.team2_player2.elo_rating -= team1_multiplier * abs(elo_delta)
        
        # Update win/loss records
        team1_won = 1 if self.result == self.MatchResult.TEAM1_WIN else 0
        team1_lost = 1 - team1_won
        
        self.team1_player1.matches_won += team1_won
        self.team1_player2.matches_won += team1_won
        self.team1_player1.matches_lost += team1_lost
        self.team1_player2.matches_lost += team1_lost
        
        self.team2_player1.matches_won += team1_lost
        self.team2_player2.matches_won += team1_lost
        self.team2_player1.matches_lost += team1_won
        self.team2_player2.matches_lost += team1_won
        
        for player in players:
            player.save()
        
        super().save(update_fields=['elo_change', 'result'])