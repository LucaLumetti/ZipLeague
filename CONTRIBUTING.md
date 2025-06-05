# Contributing to ZipLeague

Thank you for your interest in contributing to ZipLeague! We welcome contributions from everyone.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/ZipLeague.git
   cd ZipLeague
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Run migrations and start the development server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

## How to Contribute

### Reporting Issues

- Use the [GitHub Issues](https://github.com/LucaLumetti/ZipLeague/issues) page
- Search existing issues before creating a new one
- Provide clear steps to reproduce the issue
- Include relevant system information (OS, Python version, etc.)

### Submitting Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes following our coding standards
3. Test your changes thoroughly
4. Commit your changes with a clear commit message:
   ```bash
   git commit -m "Add feature: brief description of changes"
   ```
5. Push to your fork and submit a pull request

### Coding Standards

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions small and focused
- Write tests for new features when applicable

### Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass
- Keep pull requests focused on a single feature or fix
- Update documentation if necessary

## Development Setup

### Running Tests

```bash
python manage.py test
```

### Database Setup

The project uses PostgreSQL for both development and production. When using Docker Compose, the database is automatically configured. To reset the database:

```bash
docker compose down -v  # Remove volumes to delete database data
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

For local development without Docker, ensure you have PostgreSQL installed and configure the database settings in your `.env` file based on `.env.example`.

### Docker Development

Alternatively, you can use Docker:

```bash
docker-compose up
```

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a professional tone in all interactions

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the "question" label
- Contact the maintainer: [Luca Lumetti](https://github.com/LucaLumetti)

## License

By contributing to ZipLeague, you agree that your contributions will be licensed under the MIT License.
