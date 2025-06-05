# ZipLeague

A simple but effective ranking system designed to track Spikeball matches and tournament results within the <a href="https://aimagelab.ing.unimore.it/" target="_blank" rel="noopener noreferrer" class="text-zipleague text-decoration-none fw-semibold">AImageLab</a> team at the University of Modena and Reggio Emilia. Built with Django and powered by the ELO rating system, ZipLeague brings competitive fun to our research group's recreational activities.

## Features

- **Player Management**: Create and manage player profiles with ELO ratings
- **Match Tracking**: Record 2v2 matches with automatic ELO calculations
- **Live Rankings**: Real-time player rankings based on ELO ratings
- **Match History**: Detailed match records with scores and ELO changes
- **Admin Dashboard**: Complete administrative interface for league management
- **Token-based Registration**: Secure user registration system with invitation tokens
- **ELO Recomputation**: Admin tool to recalculate all ELO ratings from scratch

## Quick Start

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/LucaLumetti/ZipLeague.git
   cd ZipLeague
   cp .env.example .env
   ```

2. **Run with Docker**:
   ```bash
   docker compose up -d --build
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

## Technologies

- **Backend**: Django 5.2, PostgreSQL
- **Frontend**: Bootstrap 5, Django Templates
- **Deployment**: Docker, Gunicorn, Whitenoise
- **Authentication**: Django Auth with custom registration tokens

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and contribution guidelines.
