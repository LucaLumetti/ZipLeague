from django.contrib import admin
from .models import Player, Match, RegistrationToken

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'elo_rating', 'matches_played', 'matches_won', 'matches_lost', 'win_percentage')
    search_fields = ('name', 'email')
    list_filter = ('created_at',)
    ordering = ('-elo_rating',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'team1_player1', 'team1_player2', 'team2_player1', 'team2_player2', 
                   'team1_score', 'team2_score', 'result', 'elo_change', 'date_played')
    search_fields = ('team1_player1__name', 'team1_player2__name', 'team2_player1__name', 'team2_player2__name')
    list_filter = ('date_played', 'result')
    ordering = ('-date_played',)

@admin.register(RegistrationToken)
class RegistrationTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'created_by', 'created_at', 'expires_at', 'is_used', 'used_by', 'used_at', 'is_valid')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('token', 'created_by__username', 'used_by__username')
    readonly_fields = ('token', 'used_at', 'is_valid', 'is_expired')
    ordering = ('-created_at',)
    
    def get_readonly_fields(self, request, obj=None):
        # Make certain fields readonly when editing existing tokens
        if obj:  # editing an existing object
            return self.readonly_fields + ('created_by', 'expires_at')
        return self.readonly_fields