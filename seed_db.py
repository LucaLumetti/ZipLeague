from datetime import datetime
import os
import django
import random
from faker import Faker
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zip_league.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Player, Match

fake = Faker()

def create_players(num_players=10):
    players = []
    player_strengths = {}
    for _ in range(num_players):
        # Strength is normally distributed from 0 to 10, most players are average, a few are very strong/weak
        strength = random.gauss(50, 10) 
        player = Player.objects.create(
            name=fake.unique.name(),
            email=fake.unique.email(),
        )
        player_strengths[player.pk] = strength
        players.append(player)
    print(f'{num_players} players created.')
    return players, player_strengths

def create_matches(players, player_strengths, num_matches=200):
    from datetime import timedelta, date
    # Create matches throughout 2025
    year_2025_start = date(2025, 1, 1)
    year_2025_end = date(2025, 12, 31)
    total_days = (year_2025_end - year_2025_start).days
    
    for i in range(num_matches):
        # Grouping logic: strong players are more likely to be grouped together
        sorted_players = sorted(players, key=lambda p: player_strengths[p.pk], reverse=True)
        # Pick 2 strong and 2 random (sometimes strong, sometimes weak)
        split_point = len(sorted_players) * 2 // 3  # Use integer division
        team1 = random.sample(sorted_players[:split_point], 2)
        team2 = random.sample(sorted_players[split_point:], 2)
        match_players = team1 + team2
        random.shuffle(match_players)
        team1_player1 = Player.objects.get(pk=match_players[0].id)
        team1_player2 = Player.objects.get(pk=match_players[1].id)
        team2_player1 = Player.objects.get(pk=match_players[2].id)
        team2_player2 = Player.objects.get(pk=match_players[3].id)
        team1_strength = player_strengths[team1_player1.pk] + player_strengths[team1_player2.pk]
        team2_strength = player_strengths[team2_player1.pk] + player_strengths[team2_player2.pk]
        # Probabilistic outcome: strong teams win more often, but not always
        prob_team1_wins = team1_strength / (team1_strength + team2_strength)
        team1_wins = random.random() < prob_team1_wins
        if team1_wins:
            team1_score = random.randint(6, 10)
            team2_score = random.randint(0, team1_score - 1)
        else:
            team2_score = random.randint(6, 10)
            team1_score = random.randint(0, team2_score - 1)
        # Distribute match dates evenly across 2025
        day_offset = i % total_days
        match_date = year_2025_start + timedelta(days=day_offset)
        aware_date = timezone.make_aware(datetime.combine(match_date, datetime.min.time()))
        Match.objects.create(
            team1_player1=team1_player1,
            team1_player2=team1_player2,
            team2_player1=team2_player1,
            team2_player2=team2_player2,
            team1_score=team1_score,
            team2_score=team2_score,
            date_played=aware_date
        )
    print(f'{num_matches} matches created.')

def create_admin_user():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print('Admin user created.')
    else:
        print('Admin user already exists.')

def main():
    print('Seeding database...')
    Player.objects.all().delete()
    Match.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    
    create_admin_user()
    players, player_strengths = create_players()
    create_matches(players, player_strengths)
    print('Database seeded successfully!')

if __name__ == '__main__':
    main()
