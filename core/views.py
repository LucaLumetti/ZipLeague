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
import trueskill

from .models import TRUESKILL_DEFAULT_MU, TRUESKILL_DEFAULT_SIGMA, Player, Match, RegistrationToken, YearArchive, ArchivedPlayerStats
from .forms import PlayerForm, MatchForm # Assuming these forms are well-defined

class HomeView(ListView):
    model = Player
    template_name = 'core/home.html'
    context_object_name = 'players'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Order by TrueSkill score for home page
        players = list(Player.objects.all())
        players.sort(key=lambda p: p.trueskill_score, reverse=True)
        context['players'] = players[:10]  # Show top 10 players on home page
        # Add recent matches to context for home page display
        context['recent_matches'] = Match.objects.order_by('-date_played')[:5]
        return context

class PlayerListView(ListView):
    model = Player
    template_name = 'core/player_list.html'
    context_object_name = 'players'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Order by TrueSkill score by default
        players = list(Player.objects.all())
        players.sort(key=lambda p: p.trueskill_score, reverse=True)
        context['players'] = players
        return context

class PlayerDetailView(DetailView):
    model = Player
    template_name = 'core/player_detail.html'
    context_object_name = 'player'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.get_object()
        current_year = timezone.now().year
        # Fetch only current year matches involving this player
        matches_qs = Match.objects.filter(
            Q(team1_player1=player) | Q(team1_player2=player) |
            Q(team2_player1=player) | Q(team2_player2=player),
            year=current_year
        ).distinct().order_by('-date_played')  # Ensure distinct matches and order by date
        
        # We need to annotate matches with trueskill changes.
        matches_with_trueskill = self.annotate_matches_with_trueskill_change(matches_qs, player)
        context['matches'] = matches_with_trueskill

        # Generate TrueSkill history data for chart
        trueskill_history = self.generate_trueskill_history(player)
        # Convert to JSON to prevent JavaScript errors with None values
        context['trueskill_history_json'] = json.dumps(trueskill_history) if trueskill_history else json.dumps([])
        context['trueskill_history'] = trueskill_history

        return context

    def annotate_matches_with_trueskill_change(self, matches, player):
        """
        Annotates each match with the TrueSkill score change for the given player.
        This is complex because a player's TrueSkill score depends on all previous matches.
        """
        
        # Get all matches in chronological order to calculate historical TrueSkill
        all_matches_chrono = list(matches.order_by('date_played'))
        
        if not all_matches_chrono:
            return []

        # Create a map of match.id to the calculated change
        trueskill_change_map = {}

        # Function to get mu and sigma before a match
        def get_before_ratings(match, player_obj):
            if player_obj == match.team1_player1:
                return match.team1_player1_trueskill_mu_before, match.team1_player1_trueskill_sigma_before
            elif player_obj == match.team1_player2:
                return match.team1_player2_trueskill_mu_before, match.team1_player2_trueskill_sigma_before
            elif player_obj == match.team2_player1:
                return match.team2_player1_trueskill_mu_before, match.team2_player1_trueskill_sigma_before
            elif player_obj == match.team2_player2:
                return match.team2_player2_trueskill_mu_before, match.team2_player2_trueskill_sigma_before
            return None, None

        for i, match in enumerate(all_matches_chrono):
            mu_before, sigma_before = get_before_ratings(match, player)
            
            mu_after, sigma_after = (None, None)
            if i + 1 < len(all_matches_chrono):
                next_match = all_matches_chrono[i+1]
                mu_after, sigma_after = get_before_ratings(next_match, player)
            else:
                # For the last match, the "after" is the player's current TrueSkill
                mu_after, sigma_after = player.trueskill_mu, player.effective_trueskill_sigma

            if mu_before is not None and sigma_before is not None and mu_after is not None and sigma_after is not None:
                score_before = mu_before - 3 * sigma_before
                score_after = mu_after - 3 * sigma_after
                change = score_after - score_before
                trueskill_change_map[match.id] = change

        # Annotate the original (desc ordered) match list
        annotated_matches = []
        for match in matches:
            match.trueskill_change = trueskill_change_map.get(match.id)
            annotated_matches.append(match)
            
        return annotated_matches

    def generate_trueskill_history(self, player):
        """Generate historical TrueSkill progression for chart display"""
        # Get all matches involving this player in chronological order
        matches = Match.objects.filter(
            Q(team1_player1=player) | Q(team1_player2=player) | 
            Q(team2_player1=player) | Q(team2_player2=player)
        ).distinct().order_by('date_played')
        
        if not matches.exists():
            return []

        history = []

        def get_before_ratings(match, player_obj):
            if player_obj == match.team1_player1:
                return match.team1_player1_trueskill_mu_before, match.team1_player1_trueskill_sigma_before
            elif player_obj == match.team1_player2:
                return match.team1_player2_trueskill_mu_before, match.team1_player2_trueskill_sigma_before
            elif player_obj == match.team2_player1:
                return match.team2_player1_trueskill_mu_before, match.team2_player1_trueskill_sigma_before
            elif player_obj == match.team2_player2:
                return match.team2_player2_trueskill_mu_before, match.team2_player2_trueskill_sigma_before
            return None, None

        # Add starting point from the first match
        first_match = matches.first()
        start_mu, start_sigma = get_before_ratings(first_match, player)

        # The very first point in history is the state *before* the first match.
        history.append({
            'date': first_match.date_played.strftime('%Y-%m-%d'),
            'mu': start_mu,
            'sigma': start_sigma,
            'match_id': None,
            'won': None,
            'is_starting_point': True
        })

        # Process each match to build TrueSkill progression
        for i, match in enumerate(matches):
            mu_after, sigma_after = (None, None)
            if i + 1 < len(matches):
                next_match = matches[i+1]
                mu_after, sigma_after = get_before_ratings(next_match, player)
            else:
                mu_after, sigma_after = player.trueskill_mu, player.effective_trueskill_sigma

            player_won = (
                (player in [match.team1_player1, match.team1_player2] and match.result == 'team1_win') or
                (player in [match.team2_player1, match.team2_player2] and match.result == 'team2_win')
            )

            history.append({
                'date': match.date_played.strftime('%Y-%m-%d'),
                'mu': mu_after,
                'sigma': sigma_after,
                'match_id': match.id,
                'won': player_won,
                'is_starting_point': False
            })

        return history


class PlayerCreateView(LoginRequiredMixin, CreateView):
    model = Player
    form_class = PlayerForm
    template_name = 'core/player_form.html'
    success_url = reverse_lazy('player-list') # Redirect to player list after creation
    
    def form_valid(self, form):
        messages.success(self.request, f"Player {form.instance.name} created successfully.")
        return super().form_valid(form)

class PlayerUpdateView(LoginRequiredMixin, UpdateView):
    model = Player
    form_class = PlayerForm
    template_name = 'core/player_form.html'
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
    template_name = 'core/match_list.html'
    context_object_name = 'matches'
    ordering = ['-date_played'] # Show most recent matches first

class MatchDetailView(DetailView):
    model = Match
    template_name = 'core/match_detail.html'
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
    template_name = 'core/match_form.html'
    success_url = reverse_lazy('match-list') # Redirect to match list after creation
    
    def get_initial(self):
        """Pre-populate form with the same players and teams from the last match"""
        initial = super().get_initial()
        
        # Get the most recent match
        last_match = Match.objects.order_by('-date_played').first()
        
        if last_match:
            initial.update({
                'team1_player1': last_match.team1_player1,
                'team1_player2': last_match.team1_player2,
                'team2_player1': last_match.team2_player1,
                'team2_player2': last_match.team2_player2,
            })
        
        return initial
    
    def form_valid(self, form):
        # The Match model's save() method handles ELO calculation and player stat updates.
        # MatchForm should validate that a player is not selected more than once.
        response = super().form_valid(form)
        messages.success(self.request, "Match recorded successfully and ELO & TrueSkill ratings updated.")
        return response

class RankingListView(ListView):
    model = Player
    template_name = 'core/ranking_list.html' # Template to display player rankings
    context_object_name = 'players'
    
    def get_queryset(self):
        sort_by = self.request.GET.get('sort', 'trueskill_score') # Default sort: trueskill_score
        direction = self.request.GET.get('direction', 'desc') # Default direction: descending
        
        # Handle sorting by properties (win_percentage, trueskill_score)
        if sort_by in ['win_percentage', 'trueskill_score']:
            # For properties, we need to use Python sorting since they're computed properties
            return Player.objects.all()
        
        order_by_field = f"{'-' if direction == 'desc' else ''}{sort_by}"
        return Player.objects.all().order_by(order_by_field)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort_by = self.request.GET.get('sort', 'trueskill_score')
        direction = self.request.GET.get('direction', 'desc')
        
        # Handle property-based sorting in context
        if sort_by == 'win_percentage':
            players = list(Player.objects.all())
            players.sort(key=lambda p: p.win_percentage, reverse=(direction == 'desc'))
            context['players'] = players
        elif sort_by == 'trueskill_score':
            players = list(Player.objects.all())
            players.sort(key=lambda p: p.trueskill_score, reverse=(direction == 'desc'))
            context['players'] = players
        
        context['current_sort'] = sort_by
        context['current_direction'] = direction
        
        # Add archive-related context
        current_year = timezone.now().year
        context['current_year'] = current_year
        
        # Get archived years
        context['archived_years'] = YearArchive.objects.all()[:5]  # Show up to 5 most recent archives
        
        # Check if there are matches from previous years that can be archived
        # Show archive button only if we're in a new year and there are unarchived matches from previous year
        previous_year = current_year - 1
        unarchived_matches = Match.objects.filter(year=previous_year).exists()
        already_archived = YearArchive.objects.filter(year=previous_year).exists()
        
        context['show_archive_button'] = unarchived_matches and not already_archived
        context['year_to_archive'] = previous_year if context['show_archive_button'] else None
        
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
    """Admin-only view to recompute all ELO ratings from scratch for the current year"""
    
    def post(self, request, *args, **kwargs):
        current_year = timezone.now().year
        
        try:
            with transaction.atomic():
                # Reset all players to default ELO, TrueSkill, and stats
                Player.objects.all().update(
                    elo_rating=1000,
                    trueskill_mu=TRUESKILL_DEFAULT_MU,
                    trueskill_sigma=TRUESKILL_DEFAULT_SIGMA,
                    matches_played=0,
                    matches_won=0,
                    matches_lost=0,
                    last_match_date=None
                )
                
                # Reset match ELO changes and snapshots for current year only
                Match.objects.filter(year=current_year).update(
                    elo_change=0,
                    team1_player1_elo_before=0,
                    team1_player2_elo_before=0,
                    team2_player1_elo_before=0,
                    team2_player2_elo_before=0,
                    team1_player1_trueskill_mu_before=TRUESKILL_DEFAULT_MU,
                    team1_player1_trueskill_sigma_before=TRUESKILL_DEFAULT_SIGMA,
                    team1_player2_trueskill_mu_before=TRUESKILL_DEFAULT_MU,
                    team1_player2_trueskill_sigma_before=TRUESKILL_DEFAULT_SIGMA,
                    team2_player1_trueskill_mu_before=TRUESKILL_DEFAULT_MU,
                    team2_player1_trueskill_sigma_before=TRUESKILL_DEFAULT_SIGMA,
                    team2_player2_trueskill_mu_before=TRUESKILL_DEFAULT_MU,
                    team2_player2_trueskill_sigma_before=TRUESKILL_DEFAULT_SIGMA,
                )
                
                # Process only current year matches in chronological order
                matches = Match.objects.filter(year=current_year).order_by('date_played')
                
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
                                            'team2_player2_elo_before', 'team1_player1_trueskill_mu_before',
                                            'team1_player1_trueskill_sigma_before', 'team1_player2_trueskill_mu_before',
                                            'team1_player2_trueskill_sigma_before', 'team2_player1_trueskill_mu_before',
                                            'team2_player1_trueskill_sigma_before', 'team2_player2_trueskill_mu_before',
                                            'team2_player2_trueskill_sigma_before'])
                
                messages.success(request, f"ELO and TrueSkill ratings for {current_year} have been recomputed successfully. Processed {matches.count()} matches.")
        except Exception as e:
            messages.error(request, f"Error recomputing ELO and TrueSkill ratings: {str(e)}")
        
        return redirect('rankings')
    
    def get(self, request, *args, **kwargs):
        current_year = timezone.now().year
        # Show confirmation page
        return render(request, 'core/elo_recompute_confirm.html', {
            'total_matches': Match.objects.filter(year=current_year).count(),
            'total_players': Player.objects.count(),
            'current_year': current_year,
        })
"""
Archive functionality views - to be added to views.py
"""

@method_decorator(user_passes_test(lambda u: u.is_superuser), name='dispatch')
class ArchiveYearView(View):
    """Admin-only view to archive a year's data"""
    
    def post(self, request, *args, **kwargs):
        year_to_archive = int(request.POST.get('year'))
        current_year = timezone.now().year
        
        # Validation
        if year_to_archive >= current_year:
            messages.error(request, f"Cannot archive the current year ({current_year}). Only past years can be archived.")
            return redirect('rankings')
        
        if YearArchive.objects.filter(year=year_to_archive).exists():
            messages.error(request, f"Year {year_to_archive} has already been archived.")
            return redirect('rankings')
        
        try:
            with transaction.atomic():
                # Create the archive record
                archive = YearArchive.objects.create(
                    year=year_to_archive
                )
                
                # Get all matches from that year
                year_matches = Match.objects.filter(year=year_to_archive)
                archive.total_matches = year_matches.count()
                
                # Calculate statistics before archiving
                statistics = self.calculate_year_statistics(year_to_archive, year_matches)
                archive.statistics = statistics
                
                # Get all players who played in that year
                player_ids = set()
                for match in year_matches:
                    player_ids.add(match.team1_player1.id)
                    player_ids.add(match.team1_player2.id)
                    player_ids.add(match.team2_player1.id)
                    player_ids.add(match.team2_player2.id)
                
                players = Player.objects.filter(id__in=player_ids)
                archive.total_players = players.count()
                
                # Archive player statistics
                for player in players:
                    ArchivedPlayerStats.objects.create(
                        archive=archive,
                        player_name=player.name,
                        player_email=player.email,
                        elo_rating=player.elo_rating,
                        trueskill_mu=player.trueskill_mu,
                        trueskill_sigma=player.trueskill_sigma,
                        matches_played=player.matches_played,
                        matches_won=player.matches_won,
                        matches_lost=player.matches_lost,
                    )
                
                # Reset all players' stats for the new year
                Player.objects.all().update(
                    elo_rating=1000,
                    trueskill_mu=TRUESKILL_DEFAULT_MU,
                    trueskill_sigma=TRUESKILL_DEFAULT_SIGMA,
                    matches_played=0,
                    matches_won=0,
                    matches_lost=0,
                    last_match_date=None,
                    current_year=current_year
                )
                
                # Update all future year matches to current year
                Match.objects.filter(year__gt=year_to_archive).update(year=current_year)
                
                archive.save()
                
                messages.success(
                    request, 
                    f"Year {year_to_archive} has been archived successfully! "
                    f"Archived {archive.total_players} players and {archive.total_matches} matches. "
                    f"All player ratings have been reset for {current_year}."
                )
        except Exception as e:
            messages.error(request, f"Error archiving year: {str(e)}")
        
        return redirect('rankings')
    
    def get(self, request, *args, **kwargs):
        year = int(request.GET.get('year', timezone.now().year - 1))
        current_year = timezone.now().year
        
        # Check if there are any matches from previous years that haven't been archived
        unarchived_years = Match.objects.filter(
            year__lt=current_year
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        # Check if this year is already archived
        already_archived = YearArchive.objects.filter(year=year).exists()
        
        # Get match count for the year
        match_count = Match.objects.filter(year=year).count()
        
        return render(request, 'core/archive_year_confirm.html', {
            'year': year,
            'current_year': current_year,
            'match_count': match_count,
            'already_archived': already_archived,
            'unarchived_years': list(unarchived_years),
        })
    
    def calculate_year_statistics(self, year, matches):
        """Calculate comprehensive statistics for the year"""
        from collections import defaultdict
        from datetime import datetime
        
        stats = {
            'total_matches': matches.count(),
            'matches_by_month': defaultdict(int),
            'matches_by_day': defaultdict(int),
            'player_partnerships': defaultdict(int),
            'longest_winning_streak': {},
            'most_matches_in_day': {'date': None, 'count': 0},
        }
        
        # Calculate matches by month and day
        for match in matches:
            month_key = match.date_played.strftime('%Y-%m')
            stats['matches_by_month'][month_key] += 1
            
            day_key = match.date_played.strftime('%Y-%m-%d')
            stats['matches_by_day'][day_key] += 1
        
        # Find day with most matches
        if stats['matches_by_day']:
            max_day = max(stats['matches_by_day'].items(), key=lambda x: x[1])
            stats['most_matches_in_day'] = {'date': max_day[0], 'count': max_day[1]}
        
        # Convert defaultdicts to regular dicts for JSON serialization
        stats['matches_by_month'] = dict(stats['matches_by_month'])
        stats['matches_by_day'] = dict(stats['matches_by_day'])
        stats['player_partnerships'] = dict(stats['player_partnerships'])
        
        return stats


class ArchivedYearDetailView(DetailView):
    """View to show archived year statistics and rankings"""
    model = YearArchive
    template_name = 'core/archived_year_detail.html'
    context_object_name = 'archive'
    slug_field = 'year'
    slug_url_kwarg = 'year'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        archive = self.get_object()
        
        # Get archived player stats sorted by TrueSkill
        player_stats = list(archive.player_stats.all())
        player_stats.sort(key=lambda p: p.trueskill_score, reverse=True)
        
        context['player_stats'] = player_stats
        context['statistics'] = archive.statistics
        
        # Prepare data for charts
        context['chart_data'] = self.prepare_chart_data(archive, player_stats)
        
        return context
    
    def prepare_chart_data(self, archive, player_stats):
        """Prepare data for visualization charts"""
        import json
        
        # Top 10 players by TrueSkill
        top_players = player_stats[:10]
        
        chart_data = {
            'top_players': {
                'labels': [p.player_name for p in top_players],
                'trueskill_scores': [round(p.trueskill_score, 2) for p in top_players],
                'elo_ratings': [p.elo_rating for p in top_players],
                'matches_played': [p.matches_played for p in top_players],
            },
            'matches_by_month': archive.statistics.get('matches_by_month', {}),
            'most_matches_in_day': archive.statistics.get('most_matches_in_day', {}),
        }
        
        return json.dumps(chart_data)


class ArchivedYearsListView(ListView):
    """View to list all archived years"""
    model = YearArchive
    template_name = 'core/archived_years_list.html'
    context_object_name = 'archives'
    ordering = ['-year']
