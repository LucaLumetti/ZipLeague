from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone
import json

from .models import Player, Match, RegistrationToken
from .forms import PlayerForm, MatchForm # Assuming these forms are well-defined

class HomeView(ListView):
    model = Player
    template_name = 'rankings/home.html'
    context_object_name = 'players'
    ordering = ['-elo_rating'] # Show top players on home page
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add recent matches to context for home page display
        context['recent_matches'] = Match.objects.order_by('-date_played')[:5]
        return context

class PlayerListView(ListView):
    model = Player
    template_name = 'rankings/player_list.html'
    context_object_name = 'players'
    ordering = ['-elo_rating'] # Default sort by ELO rating

class PlayerDetailView(DetailView):
    model = Player
    template_name = 'rankings/player_detail.html'
    context_object_name = 'player'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.get_object()
        # Fetch all matches involving this player for their detail page
        matches = Match.objects.filter(
            Q(team1_player1=player) | Q(team1_player2=player) | 
            Q(team2_player1=player) | Q(team2_player2=player)
        ).distinct().order_by('-date_played') # Ensure distinct matches and order by date
        context['matches'] = matches
        
        # Generate ELO history data for chart
        elo_history = self.generate_elo_history(player)
        # Convert to JSON to prevent JavaScript errors with None values
        context['elo_history_json'] = json.dumps(elo_history) if elo_history else json.dumps([])
        context['elo_history'] = elo_history
        
        return context
    
    def generate_elo_history(self, player):
        """Generate historical ELO progression for chart display"""
        # Get all matches involving this player in chronological order
        matches = Match.objects.filter(
            Q(team1_player1=player) | Q(team1_player2=player) | 
            Q(team2_player1=player) | Q(team2_player2=player)
        ).distinct().order_by('date_played')
        
        elo_data = []
        current_elo = 1000  # Starting ELO
        
        # Add starting point
        if matches.exists():
            first_match = matches.first()
            # Get the ELO before the first match
            if player == first_match.team1_player1:
                current_elo = first_match.team1_player1_elo_before
            elif player == first_match.team1_player2:
                current_elo = first_match.team1_player2_elo_before
            elif player == first_match.team2_player1:
                current_elo = first_match.team2_player1_elo_before
            elif player == first_match.team2_player2:
                current_elo = first_match.team2_player2_elo_before
            
            # Add starting point (before first match) - use null instead of None
            elo_data.append({
                'date': first_match.date_played.strftime('%Y-%m-%d'),
                'elo': current_elo,
                'match_id': None,  # This will be converted to null in JSON
                'elo_change': None,  # Add this to avoid undefined errors
                'won': None,  # Add this to avoid undefined errors
                'is_starting_point': True
            })
        
        # Process each match to build ELO progression
        for match in matches:
            # Determine if player won or lost and calculate ELO change
            player_won = False
            elo_before = current_elo
            
            if player in [match.team1_player1, match.team1_player2]:
                # Player was in team 1
                player_won = (match.result == match.MatchResult.TEAM1_WIN)
                if player == match.team1_player1:
                    elo_before = match.team1_player1_elo_before
                else:
                    elo_before = match.team1_player2_elo_before
            else:
                # Player was in team 2
                player_won = (match.result == match.MatchResult.TEAM2_WIN)
                if player == match.team2_player1:
                    elo_before = match.team2_player1_elo_before
                else:
                    elo_before = match.team2_player2_elo_before
            
            # Calculate ELO after match
            elo_change = match.elo_change if player_won else -match.elo_change
            elo_after = elo_before + elo_change
            
            elo_data.append({
                'date': match.date_played.strftime('%Y-%m-%d'),
                'elo': elo_after,
                'match_id': match.id,
                'elo_change': elo_change,
                'won': player_won,
                'is_starting_point': False
            })
            
            current_elo = elo_after
        
        return elo_data

class PlayerCreateView(LoginRequiredMixin, CreateView):
    model = Player
    form_class = PlayerForm
    template_name = 'rankings/player_form.html'
    success_url = reverse_lazy('player-list') # Redirect to player list after creation
    
    def form_valid(self, form):
        messages.success(self.request, f"Player {form.instance.name} created successfully.")
        return super().form_valid(form)

class PlayerUpdateView(LoginRequiredMixin, UpdateView):
    model = Player
    form_class = PlayerForm
    template_name = 'rankings/player_form.html'
    # success_url is dynamically set in get_success_url

    def get_success_url(self):
        # Redirect to the updated player's detail page
        # self.object is available after form_valid has been called and the object is saved.
        # If called before, self.get_object() should be used if direct pk is not available.
        return reverse_lazy('player-detail', kwargs={'pk': self.kwargs['pk']})
    
    def form_valid(self, form):
        messages.success(self.request, f"Player {form.instance.name} updated successfully.")
        return super().form_valid(form)

class MatchListView(ListView):
    model = Match
    template_name = 'rankings/match_list.html'
    context_object_name = 'matches'
    ordering = ['-date_played'] # Show most recent matches first

class MatchDetailView(DetailView):
    model = Match
    template_name = 'rankings/match_detail.html'
    context_object_name = 'match'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.get_object()
        
        # Use the stored ELO snapshots for accurate historical data
        team1_avg_elo = (match.team1_player1_elo_before + match.team1_player2_elo_before) / 2
        team2_avg_elo = (match.team2_player1_elo_before + match.team2_player2_elo_before) / 2
        
        # Calculate win probability using ELO formula with historical data
        expected_team1_win = 1 / (1 + 10 ** ((team2_avg_elo - team1_avg_elo) / 400))
        expected_team2_win = 1 - expected_team1_win
          # Calculate what would have happened if the other team won
        k_factor = 32
        if match.result == match.MatchResult.TEAM1_WIN:
            # What if team 2 had won instead (Team 1 gets actual_result = 0)
            elo_delta_if_team2_won = round(k_factor * (0 - expected_team1_win))
            context['alt_elo_change'] = abs(elo_delta_if_team2_won)  # Show positive value in template
            context['alt_winner'] = 'team2'
        else:
            # What if team 1 had won instead (Team 1 gets actual_result = 1)
            elo_delta_if_team1_won = round(k_factor * (1 - expected_team1_win))
            context['alt_elo_change'] = elo_delta_if_team1_won
            context['alt_winner'] = 'team1'
        
        # Add historical ELO snapshots for template display
        context.update({
            'team1_avg_elo': round(team1_avg_elo, 1),
            'team2_avg_elo': round(team2_avg_elo, 1),
            'team1_win_probability': round(expected_team1_win * 100, 1),
            'team2_win_probability': round(expected_team2_win * 100, 1),
            # Historical ELO ratings (before the match)
            'team1_player1_elo_before': match.team1_player1_elo_before,
            'team1_player2_elo_before': match.team1_player2_elo_before,
            'team2_player1_elo_before': match.team2_player1_elo_before,
            'team2_player2_elo_before': match.team2_player2_elo_before,
        })
        
        return context

class MatchCreateView(LoginRequiredMixin, CreateView):
    model = Match
    form_class = MatchForm
    template_name = 'rankings/match_form.html'
    success_url = reverse_lazy('match-list') # Redirect to match list after creation
    
    def form_valid(self, form):
        # The Match model's save() method handles ELO calculation and player stat updates.
        # MatchForm should validate that a player is not selected more than once.
        response = super().form_valid(form)
        messages.success(self.request, "Match recorded successfully and ELO ratings updated.")
        return response

class RankingListView(ListView):
    model = Player
    template_name = 'rankings/ranking_list.html' # Template to display player rankings
    context_object_name = 'players'
    
    def get_queryset(self):
        sort_by = self.request.GET.get('sort', 'elo_rating') # Default sort: elo_rating
        direction = self.request.GET.get('direction', 'desc') # Default direction: descending
        
        # Handle sorting by win_percentage (a model property)
        if sort_by == 'win_percentage':
            # For win_percentage, we need to use Python sorting since it's a property
            from django.http import HttpResponse
            from django.template import loader
            
            # Return all players and let the template handle the sorting display
            # The template will need to handle the win_percentage sorting
            return Player.objects.all().order_by('-elo_rating')
        
        order_by_field = f"{'-' if direction == 'desc' else ''}{sort_by}"
        return Player.objects.all().order_by(order_by_field)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort_by = self.request.GET.get('sort', 'elo_rating')
        direction = self.request.GET.get('direction', 'desc')
        
        # Handle win_percentage sorting in context since it's a property
        if sort_by == 'win_percentage':
            players = list(Player.objects.all())
            players.sort(key=lambda p: p.win_percentage, reverse=(direction == 'desc'))
            context['players'] = players
        
        return context

class UserRegistrationView(UserPassesTestMixin, CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('home')
    
    def test_func(self):
        # Only allow superusers (admin) to register new users
        return self.request.user.is_superuser
    
    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f"User {user.username} has been registered successfully.")
        return super().form_valid(form)

class CreateRegistrationTokenView(UserPassesTestMixin, View):
    """Admin-only view to create registration tokens"""
    
    def test_func(self):
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        try:
            token = RegistrationToken.objects.create(created_by=request.user)
            registration_url = request.build_absolute_uri(
                f"/register-with-token/{token.token}/"
            )
            messages.success(
                request, 
                f"Registration link created successfully! Share this link: {registration_url}"
            )
        except Exception as e:
            messages.error(request, f"Error creating registration token: {str(e)}")
        
        return redirect('register')
    
    def get(self, request, *args, **kwargs):
        # Show the create token page
        active_tokens = RegistrationToken.objects.filter(
            created_by=request.user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')
        
        return render(request, 'registration/create_token.html', {
            'active_tokens': active_tokens
        })

class TokenBasedRegistrationView(CreateView):
    """Public view for registration using a token"""
    model = User
    form_class = UserCreationForm
    template_name = 'registration/token_register.html'
    success_url = reverse_lazy('home')
    
    def dispatch(self, request, *args, **kwargs):
        self.token_uuid = kwargs.get('token')
        try:
            self.token = RegistrationToken.objects.get(token=self.token_uuid)
        except RegistrationToken.DoesNotExist:
            messages.error(request, "Invalid registration token.")
            return redirect('home')
        
        if not self.token.is_valid:
            if self.token.is_used:
                messages.error(request, "This registration token has already been used.")
            else:
                messages.error(request, "This registration token has expired.")
            return redirect('home')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['token'] = self.token
        return context
    
    def form_valid(self, form):
        user = form.save()
        self.token.mark_as_used(user)
        messages.success(
            self.request, 
            f"Welcome {user.username}! Your account has been created successfully."
        )
        return super().form_valid(form)

@method_decorator(user_passes_test(lambda u: u.is_superuser), name='dispatch')
class EloRecomputeView(View):
    """Admin-only view to recompute all ELO ratings from scratch"""
    
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Reset all players to default ELO and stats
                Player.objects.all().update(
                    elo_rating=1000,
                    matches_played=0,
                    matches_won=0,
                    matches_lost=0
                )
                
                # Reset all match ELO changes and snapshots
                Match.objects.all().update(
                    elo_change=0,
                    team1_player1_elo_before=0,
                    team1_player2_elo_before=0,
                    team2_player1_elo_before=0,
                    team2_player2_elo_before=0
                )
                
                # Process all matches in chronological order
                matches = Match.objects.all().order_by('date_played')
                
                for match in matches:
                    # Refresh player data from database to get current ELO ratings
                    match.team1_player1.refresh_from_db()
                    match.team1_player2.refresh_from_db()
                    match.team2_player1.refresh_from_db()
                    match.team2_player2.refresh_from_db()
                    
                    # Capture ELO snapshots before processing this match
                    match.capture_elo_snapshots()
                    
                    # Update player stats and save the match with snapshots
                    match._stats_updated = False
                    match.update_player_stats()
                    
                    # Save the match with updated snapshots and elo_change
                    match.save(update_fields=['elo_change', 'team1_player1_elo_before', 
                                            'team1_player2_elo_before', 'team2_player1_elo_before', 
                                            'team2_player2_elo_before'])
                
                messages.success(request, f"ELO ratings have been recomputed successfully. Processed {matches.count()} matches.")
                
        except Exception as e:
            messages.error(request, f"Error recomputing ELO ratings: {str(e)}")
        
        return redirect('rankings')
    
    def get(self, request, *args, **kwargs):
        # Show confirmation page
        return render(request, 'rankings/elo_recompute_confirm.html', {
            'total_matches': Match.objects.count(),
            'total_players': Player.objects.count()
        })