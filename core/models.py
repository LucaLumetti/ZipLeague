from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from datetime import timedelta
import trueskill

TRUESKILL_DEFAULT_MU = 25.0
TRUESKILL_DEFAULT_SIGMA = TRUESKILL_DEFAULT_MU / 3
TRUESKILL_DEFAULT_BETA = 4.16
TRUESKILL_DEFAULT_TAU = 0.0833
TRUESKILL_DEFAULT_DRAW_PROBABILITY = 0.1

trueskill.setup(mu=TRUESKILL_DEFAULT_MU, sigma=TRUESKILL_DEFAULT_SIGMA, beta=TRUESKILL_DEFAULT_BETA, tau=TRUESKILL_DEFAULT_TAU, draw_probability=TRUESKILL_DEFAULT_DRAW_PROBABILITY)


def get_current_year():
    """Helper function to get current year for model defaults"""
    return timezone.now().year


class Player(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    elo_rating = models.IntegerField(default=1000)
    trueskill_mu = models.FloatField(default=TRUESKILL_DEFAULT_MU)
    trueskill_sigma = models.FloatField(default=TRUESKILL_DEFAULT_SIGMA)
    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_match_date = models.DateTimeField(null=True, blank=True)
    current_year = models.IntegerField(default=get_current_year)

    def __str__(self):
        return self.name

    @property
    def win_percentage(self):
        if self.matches_played == 0:
            return 0
        return (self.matches_won / self.matches_played) * 100
    
    @property
    def effective_trueskill_sigma(self):
        """Returns the current effective TrueSkill sigma with decay applied for inactivity"""
        if self.last_match_date is None:
            return self.trueskill_sigma

        days_inactive = (timezone.now() - self.last_match_date).days
        
        if days_inactive < 7:
            return self.trueskill_sigma
        
        # Apply decay for each day after day 6
        default_sigma = TRUESKILL_DEFAULT_SIGMA
        days_of_decay = days_inactive - 6
        decay_factor = 0.99 ** days_of_decay
        decayed_sigma = self.trueskill_sigma * decay_factor + default_sigma * (1 - decay_factor)
        
        return decayed_sigma
    
    @property
    def trueskill_rating(self):
        """Returns TrueSkill rating as a Rating object with decayed sigma"""
        return trueskill.Rating(mu=self.trueskill_mu, sigma=self.effective_trueskill_sigma)
    
    @property
    def trueskill_score(self):
        """Returns conservative skill estimate (mu - 3*sigma) for ranking purposes with decayed sigma"""
        return self.trueskill_mu - (3 * self.effective_trueskill_sigma)

class RegistrationToken(models.Model):
    """Model for single-use registration tokens created by admins"""
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='created_tokens')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_tokens')
    used_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Default expiration: 7 days from creation
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired
    
    def mark_as_used(self, user):
        """Mark the token as used by a specific user"""
        self.is_used = True
        self.used_by = user
        self.used_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Registration Token {self.token} (created by {self.created_by.username})"

class Match(models.Model):
    team1_player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team1_player1')
    team1_player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team1_player2')
    team2_player1 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team2_player1')
    team2_player2 = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_team2_player2')
    
    team1_score = models.IntegerField() # Scores must be explicitly provided
    team2_score = models.IntegerField() # Scores must be explicitly provided
    date_played = models.DateTimeField(default=timezone.now)
    year = models.IntegerField(default=get_current_year)
    
    # ELO snapshots before the match
    team1_player1_elo_before = models.IntegerField(default=0)
    team1_player2_elo_before = models.IntegerField(default=0)
    team2_player1_elo_before = models.IntegerField(default=0)
    team2_player2_elo_before = models.IntegerField(default=0)
    
    # TrueSkill snapshots before the match
    team1_player1_trueskill_mu_before = models.FloatField(default=TRUESKILL_DEFAULT_MU)
    team1_player1_trueskill_sigma_before = models.FloatField(default=TRUESKILL_DEFAULT_SIGMA)
    team1_player2_trueskill_mu_before = models.FloatField(default=TRUESKILL_DEFAULT_MU)
    team1_player2_trueskill_sigma_before = models.FloatField(default=TRUESKILL_DEFAULT_SIGMA)
    team2_player1_trueskill_mu_before = models.FloatField(default=TRUESKILL_DEFAULT_MU)
    team2_player1_trueskill_sigma_before = models.FloatField(default=TRUESKILL_DEFAULT_SIGMA)
    team2_player2_trueskill_mu_before = models.FloatField(default=TRUESKILL_DEFAULT_MU)
    team2_player2_trueskill_sigma_before = models.FloatField(default=TRUESKILL_DEFAULT_SIGMA)

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

    def capture_elo_snapshots(self):
        """Capture ELO and TrueSkill ratings before the match is processed"""
        self.team1_player1_elo_before = self.team1_player1.elo_rating
        self.team1_player2_elo_before = self.team1_player2.elo_rating
        self.team2_player1_elo_before = self.team2_player1.elo_rating
        self.team2_player2_elo_before = self.team2_player2.elo_rating
        
        # Capture TrueSkill snapshots using ACTUAL sigma (not effective with decay)
        # This allows sigma to decrease naturally through matches
        self.team1_player1_trueskill_mu_before = self.team1_player1.trueskill_mu
        self.team1_player1_trueskill_sigma_before = self.team1_player1.trueskill_sigma
        self.team1_player2_trueskill_mu_before = self.team1_player2.trueskill_mu
        self.team1_player2_trueskill_sigma_before = self.team1_player2.trueskill_sigma
        self.team2_player1_trueskill_mu_before = self.team2_player1.trueskill_mu
        self.team2_player1_trueskill_sigma_before = self.team2_player1.trueskill_sigma
        self.team2_player2_trueskill_mu_before = self.team2_player2.trueskill_mu
        self.team2_player2_trueskill_sigma_before = self.team2_player2.trueskill_sigma

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
        
        # Set the year based on date_played
        if self.date_played:
            self.year = self.date_played.year
        
        # Call full_clean before saving to ensure model validation, including clean() method
        if is_new_match: # Or always, depending on desired strictness for updates too
             self.full_clean()

        # Capture ELO snapshots before processing the match (only for new matches)
        if is_new_match:
            self.capture_elo_snapshots()

        super().save(*args, **kwargs)

        if is_new_match and not hasattr(self, '_stats_updated'):
            self.update_player_stats()
            self._stats_updated = True
    
    def update_player_stats(self):
        """Updates player ELO ratings, TrueSkill ratings and win/loss records after a match."""
        players = [self.team1_player1, self.team1_player2, self.team2_player1, self.team2_player2]
        
        for player in players:
            player.matches_played += 1
        
        # Use the captured ELO snapshots for calculation
        team1_avg_elo = (self.team1_player1_elo_before + self.team1_player2_elo_before) / 2
        team2_avg_elo = (self.team2_player1_elo_before + self.team2_player2_elo_before) / 2
        
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
        
        # Update TrueSkill ratings
        # Create TrueSkill Rating objects from the captured snapshots
        team1_rating1 = trueskill.Rating(mu=self.team1_player1_trueskill_mu_before, sigma=self.team1_player1_trueskill_sigma_before)
        team1_rating2 = trueskill.Rating(mu=self.team1_player2_trueskill_mu_before, sigma=self.team1_player2_trueskill_sigma_before)
        team2_rating1 = trueskill.Rating(mu=self.team2_player1_trueskill_mu_before, sigma=self.team2_player1_trueskill_sigma_before)
        team2_rating2 = trueskill.Rating(mu=self.team2_player2_trueskill_mu_before, sigma=self.team2_player2_trueskill_sigma_before)

        # Calculate new TrueSkill ratings based on match result
        if self.result == self.MatchResult.TEAM1_WIN:
            # Team 1 won
            (new_team1_rating1, new_team1_rating2), (new_team2_rating1, new_team2_rating2) = trueskill.rate(
                [(team1_rating1, team1_rating2), (team2_rating1, team2_rating2)], ranks=[0, 1]
            )
        else:
            # Team 2 won
            (new_team1_rating1, new_team1_rating2), (new_team2_rating1, new_team2_rating2) = trueskill.rate(
                [(team1_rating1, team1_rating2), (team2_rating1, team2_rating2)], ranks=[1, 0]
            )
        
        # Update player TrueSkill ratings
        self.team1_player1.trueskill_mu = new_team1_rating1.mu
        self.team1_player1.trueskill_sigma = new_team1_rating1.sigma
        self.team1_player2.trueskill_mu = new_team1_rating2.mu
        self.team1_player2.trueskill_sigma = new_team1_rating2.sigma
        self.team2_player1.trueskill_mu = new_team2_rating1.mu
        self.team2_player1.trueskill_sigma = new_team2_rating1.sigma
        self.team2_player2.trueskill_mu = new_team2_rating2.mu
        self.team2_player2.trueskill_sigma = new_team2_rating2.sigma
        
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
            player.last_match_date = self.date_played
            player.save()
        
        super().save(update_fields=['elo_change', 'result'])


class YearArchive(models.Model):
    """Model to store archived year data and statistics"""
    year = models.IntegerField(unique=True)
    archived_at = models.DateTimeField(auto_now_add=True)
    total_matches = models.IntegerField(default=0)
    total_players = models.IntegerField(default=0)
    
    # Store statistics as JSON for flexibility
    statistics = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-year']
    
    def __str__(self):
        return f"Archive {self.year}"
    
    @property
    def is_current_year(self):
        return self.year == timezone.now().year


class ArchivedPlayerStats(models.Model):
    """Snapshot of player statistics at the time of archiving"""
    archive = models.ForeignKey(YearArchive, on_delete=models.CASCADE, related_name='player_stats')
    player_name = models.CharField(max_length=100)
    player_email = models.EmailField()
    elo_rating = models.IntegerField()
    trueskill_mu = models.FloatField()
    trueskill_sigma = models.FloatField()
    matches_played = models.IntegerField()
    matches_won = models.IntegerField()
    matches_lost = models.IntegerField()
    
    class Meta:
        ordering = ['-elo_rating']
        unique_together = ['archive', 'player_email']
    
    def __str__(self):
        return f"{self.player_name} - {self.archive.year}"
    
    @property
    def trueskill_score(self):
        return self.trueskill_mu - (3 * self.trueskill_sigma)
    
    @property
    def win_percentage(self):
        if self.matches_played == 0:
            return 0
        return (self.matches_won / self.matches_played) * 100
