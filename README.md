
# Resume Generator

A modern web application that helps users create professional resumes with a clean LaTeX template. The application provides a RESTful API for managing resume content and generating PDF documents.

## Features

- **User Authentication**
  - Email/password registration and login
  - OAuth integration with Google and GitHub
  - JWT-based authentication

- **Resume Management**
  - Create and organize resume sections (Education, Experience, Skills, etc.)
  - Add, update, and delete content blocks within sections
  - Reorder sections and blocks to customize resume layout
  - Toggle visibility of sections and blocks

- **PDF Generation**
  - Generate professional-looking resumes using LaTeX templates
  - Download resume as PDF
  - View LaTeX source code

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Python
- **Database**: SQLite (can be easily switched to PostgreSQL or other databases)
- **Authentication**: JWT, OAuth (Google, GitHub)
- **PDF Generation**: LaTeX

## Installation

### Prerequisites

- Python 3.8+
- LaTeX distribution (e.g., TeX Live, MiKTeX)
- pdflatex command-line tool

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/resume-generator.git
   cd resume-generator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with the following variables:
   ```
   SECRET_KEY=your_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   
   # OAuth credentials
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GITHUB_CLIENT_ID=your_github_client_id
   GITHUB_CLIENT_SECRET=your_github_client_secret
   ```

5. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

6. Access the API documentation at http://localhost:8000/docs

## API Documentation

### Authentication

#### Register a new user
```
POST /auth/register
```
Request body:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "username": "username",
  "name": "Full Name",
  "phone": "+1234567890",
  "linkedin": "linkedin.com/in/username",
  "github": "github.com/username"
}
```

#### Login with email/password
```
POST /auth/login
```
Form data:
- `username`: Email address
- `password`: Password

#### OAuth Authentication
- Google: `GET /auth/google`
- GitHub: `GET /auth/github`

### User Management

#### Get current user
```
GET /users/me
```

#### Update username
```
PUT /users/me/username
```
Request body:
```json
{
  "username": "new_username"
}
```

#### Get user by username
```
GET /users/{username}
```

### Sections

#### Create a section
```
POST /sections/
```
Request body:
```json
{
  "title": "Education",
  "blocks": [
    {
      "header": "University Name",
      "location": "City, Country",
      "subheader": "Bachelor of Science in Computer Science",
      "dates": "2018-2022",
      "description": "• GPA: 3.8/4.0\n• Relevant coursework: Data Structures, Algorithms, Database Systems"
    }
  ]
}
```

#### Get a section
```
GET /sections/{section_id}
```

#### Update a section
```
PUT /sections/{section_id}
```
Request body:
```json
{
  "title": "Updated Title",
  "is_active": true,
  "order": 1
}
```

#### Delete a section
```
DELETE /sections/{section_id}
```

#### Toggle section visibility
```
PATCH /sections/{section_id}/activate?is_active=true
```

#### Reorder sections
```
PATCH /sections/order
```
Request body:
```json
[1, 3, 2, 4]
```

### Blocks

#### Create a block
```
POST /sections/{section_id}/blocks/
```
Request body:
```json
{
  "header": "Company Name",
  "location": "City, Country",
  "subheader": "Software Engineer",
  "dates": "2022-Present",
  "description": "• Developed and maintained web applications\n• Collaborated with cross-functional teams"
}
```

#### Update a block
```
PUT /blocks/{block_id}
```
Request body:
```json
{
  "header": "Updated Company Name",
  "description": "• Updated description"
}
```

#### Delete a block
```
DELETE /blocks/{block_id}
```

#### Toggle block visibility
```
PATCH /blocks/{block_id}/activate?is_active=true
```

#### Reorder blocks
```
PATCH /blocks/order
```
Request body:
```json
{
  "section_id": 1,
  "order": [3, 1, 2]
}
```

### Resume Generation

#### Get LaTeX source
```
GET /resume/latex
```

#### Generate and download PDF
```
GET /resume/pdf
```

## Project Structure

```
resume-generator/
├── main.py              # FastAPI application and endpoints
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas for request/response validation
├── database.py          # Database connection setup
├── latex_template.py    # LaTeX template generation
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
