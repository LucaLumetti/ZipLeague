from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Player, Match
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
        context['matches'] = Match.objects.filter(
            Q(team1_player1=player) | Q(team1_player2=player) | 
            Q(team2_player1=player) | Q(team2_player2=player)
        ).distinct().order_by('-date_played') # Ensure distinct matches and order by date
        return context

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
        
        order_by_field = f"{'-' if direction == 'desc' else ''}{sort_by}"
        
        # Handle sorting by win_percentage (a model property)
        if sort_by == 'win_percentage':
            queryset = Player.objects.all()
            # Python's sorted() is used for properties not directly sortable by database
            return sorted(queryset, key=lambda p: p.win_percentage, reverse=(direction == 'desc'))
        
        return Player.objects.all().order_by(order_by_field)

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