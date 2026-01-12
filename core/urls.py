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
    path('matches/<int:pk>/', views.MatchDetailView.as_view(), name='match-detail'),
    path('matches/new/', views.MatchCreateView.as_view(), name='match-create'),
    
    # Ranking URL
    path('rankings/', views.RankingListView.as_view(), name='rankings'),
    
    # Archive URLs
    path('archives/', views.ArchivedYearsListView.as_view(), name='archived-years-list'),
    path('archives/<int:year>/', views.ArchivedYearDetailView.as_view(), name='archived-year-detail'),
    path('archive-year/', views.ArchiveYearView.as_view(), name='archive-year'),
    
    # ELO Recomputation (admin only) - changed from admin/elo-recompute/ to avoid conflict
    path('elo-recompute/', views.EloRecomputeView.as_view(), name='elo-recompute'),
    
    # User registration (admin only)
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    
    # Registration token management (admin only)
    path('create-registration-token/', views.CreateRegistrationTokenView.as_view(), name='create-registration-token'),
    path('register-with-token/<uuid:token>/', views.TokenBasedRegistrationView.as_view(), name='token-registration'),
]