from django.contrib import admin
from .models import Player, Match

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