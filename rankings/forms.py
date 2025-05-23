from django import forms
from .models import Player, Match

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'email']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['team1_player1', 'team1_player2', 'team2_player1', 'team2_player2', 
                 'team1_score', 'team2_score', 'date_played']
        widgets = {
            'date_played': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['team1_player1'].widget.attrs.update({'class': 'form-control'})
        self.fields['team1_player2'].widget.attrs.update({'class': 'form-control'})
        self.fields['team2_player1'].widget.attrs.update({'class': 'form-control'})
        self.fields['team2_player2'].widget.attrs.update({'class': 'form-control'})
        self.fields['team1_score'].widget.attrs.update({'class': 'form-control'})
        self.fields['team2_score'].widget.attrs.update({'class': 'form-control'})
        self.fields['date_played'].widget.attrs.update({'class': 'form-control'})
        
        # Add labels for clarity
        self.fields['team1_player1'].label = "Team 1 - Player 1"
        self.fields['team1_player2'].label = "Team 1 - Player 2"
        self.fields['team2_player1'].label = "Team 2 - Player 1"
        self.fields['team2_player2'].label = "Team 2 - Player 2"
        
    def clean(self):
        cleaned_data = super().clean()
        team1_player1 = cleaned_data.get('team1_player1')
        team1_player2 = cleaned_data.get('team1_player2')
        team2_player1 = cleaned_data.get('team2_player1')
        team2_player2 = cleaned_data.get('team2_player2')
        team1_score = cleaned_data.get('team1_score')
        team2_score = cleaned_data.get('team2_score')
        
        # Check for duplicate players
        players = [team1_player1, team1_player2, team2_player1, team2_player2]
        players = [p for p in players if p is not None]
        if len(players) != len(set(players)):
            raise forms.ValidationError("A player cannot play in both teams or be selected twice.")
        
        # Check for tie scores
        if team1_score is not None and team2_score is not None:
            if team1_score == team2_score:
                raise forms.ValidationError("Matches cannot end in a tie. One team must have a higher score.")
        
        return cleaned_data