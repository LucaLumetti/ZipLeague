import os
import django
import random
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zip_league.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Player, Match

fake = Faker()

def create_players(num_players=20):
    players = []
    for _ in range(num_players):
        player = Player.objects.create(
            name=fake.unique.name(),
            email=fake.unique.email(),
        )
        players.append(player)
    print(f'{num_players} players created.')
    return players

def create_matches(players, num_matches=1000):
    for _ in range(num_matches):
        # Ensure 4 unique players are selected for a match
        team_players = random.sample(players, 4)
        
        team1_player1 = team_players[0]
        team1_player2 = team_players[1]
        team2_player1 = team_players[2]
        team2_player2 = team_players[3]

        # Random scores
        team1_score = random.randint(0, 10)
        team2_score = random.randint(0, 10)

        # Ensure scores are not tied
        while team1_score == team2_score:
            team2_score = random.randint(0, 10)

        Match.objects.create(
            team1_player1=team1_player1,
            team1_player2=team1_player2,
            team2_player1=team2_player1,
            team2_player2=team2_player2,
            team1_score=team1_score,
            team2_score=team2_score,
            date_played=fake.date_time_this_year()
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
    players = create_players()
    create_matches(players)
    print('Database seeded successfully!')

if __name__ == '__main__':
    main()
