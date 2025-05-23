from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    
    # Player URLs
    path('players/', views.PlayerListView.as_view(), name='player-list'),
    path('players/<int:pk>/', views.PlayerDetailView.as_view(), name='player-detail'),
    path('players/new/', views.PlayerCreateView.as_view(), name='player-create'),
    path('players/<int:pk>/edit/', views.PlayerUpdateView.as_view(), name='player-update'),
    
    # Match URLs
    path('matches/', views.MatchListView.as_view(), name='match-list'),
    path('matches/new/', views.MatchCreateView.as_view(), name='match-create'),
    
    # Ranking URL
    path('rankings/', views.RankingListView.as_view(), name='rankings'),
    
    # User registration (admin only)
    path('register/', views.UserRegistrationView.as_view(), name='register'),
]