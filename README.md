# ZipLeague

A Django application to track 2v2 matches of any sport and rank players using ELO.

## Prerequisites

*   Docker
*   Docker Compose (recommended for local development and multi-container setups)
*   Git

## Local Development & Deployment

1.  **Clone the Repository**:
    ```bash
    git clone <your-repository-url>
    cd ZipLeague
    ```

2.  **Configure Environment Variables**:
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit `.env` and provide your actual values for:
        *   `DJANGO_SECRET_KEY` (generate a new strong key for production)
        *   `DJANGO_DEBUG` (set to `False` for production)
        *   `DJANGO_ALLOWED_HOSTS` (e.g., `yourdomain.com www.yourdomain.com localhost 127.0.0.1`)
        *   Database settings (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) if not using the default Docker Compose setup.

3.  **Build the Docker Image**:
    ```bash
    docker build -t zipleague-app .
    ```

4.  **Run the Application**:

    *   **Using Docker Compose (Recommended)**:
        This will start the Django application and a PostgreSQL database.
        ```bash
        docker compose up -d --build
        ```

    *   **Using `docker run` (Standalone, if managing DB separately)**:
        ```bash
        docker run -d -p 8000:8000 \
          --env-file .env \
          --name zipleague-web \
          zipleague-app
        ```

5.  **Database Migrations**:
    After the application container is running, execute migrations:

    *   If using Docker Compose:
        ```bash
        docker compose exec web python manage.py migrate
        ```
    *   If using `docker run`:
        ```bash
        docker exec -it zipleague-web python manage.py migrate
        ```

6.  **Create Superuser (Optional)**:
    *   If using Docker Compose:
        ```bash
        docker compose exec web python manage.py createsuperuser
        ```
    *   If using `docker run`:
        ```bash
        docker exec -it zipleague-web python manage.py createsuperuser
        ```

7.  **Access the Application**:
    Open your browser and go to `http://localhost:8000` (or your configured domain).

## Project Structure

*   `zip_league/`: Django project configuration.
*   `core/`: Django app for rankings, matches, and players.
*   `Dockerfile`: Defines the Docker image for the application.
*   `docker compose.yml`: Defines services for Docker Compose (web app and database).
*   `requirements.txt`: Python dependencies.
*   `.env.example`: Template for environment variables.
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore.

## Main Technologies

*   Python / Django
*   PostgreSQL (with Docker Compose)
*   Gunicorn (WSGI server)
*   Whitenoise (Static file serving)
*   Docker
