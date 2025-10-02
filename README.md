# French Novel Tool

Process French novel PDFs, normalize sentence length with Google Gemini AI, and export the results to Google Sheets through a polished web interface.

## ✨ Features

- 📄 **PDF Processing**: Upload French novel PDFs and extract text
- 🤖 **AI-Powered Normalization**: Uses Google Gemini to split long sentences while preserving meaning
- 📊 **Google Sheets Export**: Export processed sentences with formatted headers
- 📁 **Drive Integration**: Organize exports in specific Google Drive folders
- 📜 **History Tracking**: Keep track of all processed documents
- ⚙️ **Configurable Settings**: Adjust sentence length limits
- 🔒 **Rate Limiting**: Built-in API rate limiting for security
- 🐳 **Docker Support**: Easy deployment with Docker and docker-compose
- 📝 **Comprehensive API**: RESTful API with versioning and validation

## Project Structure

```
backend/   Flask API (v1.0) with Gemini + Google Sheets integrations
frontend/  Next.js 15 UI with Material-UI and TypeScript
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional, for containerized deployment)
- Google Cloud project with Gemini and Drive/Sheets APIs enabled
- Redis (optional, for rate limiting in production)

## Quick Start with Docker

The easiest way to run the entire stack:

```bash
# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Edit .env files with your API keys
# At minimum, set GEMINI_API_KEY in backend/.env

# Start all services
docker-compose up --build
```

Visit [http://localhost:3000](http://localhost:3000) to use the app.

## Manual Setup

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# On Unix: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For development, also install:
pip install -r requirements-dev.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run the development server
flask --app run.py run
```

The API listens on `http://localhost:5000/api/v1` by default.

### 2. Frontend Setup

```bash
cd frontend
npm install

# Copy and configure environment
cp .env.example .env.local
# Edit .env.local with your API URL

# Run the development server
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to use the app.

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest                                    # Run all tests
pytest --cov=app --cov-report=html       # With coverage report
```

### Frontend Linting
```bash
cd frontend
npm run lint
```

### Pre-commit Hooks
```bash
# Install pre-commit (from backend directory)
cd backend
pip install pre-commit
pre-commit install

# Now your code will be automatically formatted before commits
```

## 📚 Documentation

- [API Documentation](backend/API_DOCUMENTATION.md) - Complete API reference
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [TODO](TODO.md) - Planned improvements and features

## 🔧 Configuration

### Backend Environment Variables

Key variables in `backend/.env`:

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key
SECRET_KEY=your-secret-key

# Optional (with defaults)
GEMINI_MODEL=gemini-2.5-flash
MAX_FILE_SIZE=52428800  # 50MB
RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=100 per hour
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

See `backend/.env.example` for all available options.

### Frontend Environment Variables

In `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:5000/api/v1
```

## 🐳 Docker Deployment

The project includes complete Docker support:

- `backend/Dockerfile` - Backend container with gunicorn
- `frontend/Dockerfile` - Frontend container with Next.js
- `docker-compose.yml` - Complete stack with Redis

Health checks are configured for all services.

## 🔒 Security Features

- ✅ Rate limiting (configurable per endpoint)
- ✅ Input validation and sanitization
- ✅ File size limits and extension validation
- ✅ CORS whitelist configuration
- ✅ Request/response schema validation
- ✅ Structured logging

## 🚀 API Endpoints

- `GET /api/v1/health` - Health check
- `POST /api/v1/process-pdf` - Process PDF (rate limit: 10/hour)
- `POST /api/v1/export-to-sheet` - Export to Google Sheets (rate limit: 20/hour)
- `GET /api/v1/history` - Get processing history
- `GET /api/v1/settings` - Get user settings
- `POST /api/v1/settings` - Update user settings

See [API Documentation](backend/API_DOCUMENTATION.md) for detailed information.

## 📊 Tech Stack

### Backend
- Flask 3.0 with Blueprint architecture
- Flask-Migrate for database migrations
- Flask-Limiter for rate limiting
- Marshmallow for validation
- Google Gemini AI
- Google Sheets & Drive APIs
- SQLAlchemy ORM
- Tenacity for retry logic

### Frontend
- Next.js 15 (App Router)
- React 19
- TypeScript (strict mode)
- Material-UI v7
- Tailwind CSS v4
- Axios for API calls
- React Dropzone

### DevOps
- Docker & Docker Compose
- Redis for rate limiting
- Pre-commit hooks (Black, Flake8, ESLint, Bandit)
- pytest for testing

## 🛠️ Google Configuration

1. Create a Google Cloud project (or reuse an existing one).
2. Enable the **Gemini API**, **Google Sheets API**, and **Google Drive API** for the project.
3. Configure the OAuth consent screen and add the following scopes:
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive.file`
4. Create OAuth 2.0 credentials of type **Web application**:
   - Authorized JavaScript origins: add `http://localhost:3000` (and your production domain when deploying).
   - Authorized redirect URIs: add `http://localhost:3000` (and production equivalents). The frontend uses the Google Identity Services popup with the `postmessage` flow.
   - Copy the generated **Client ID** and **Client Secret**.
5. Update environment files:
   - `backend/.env`: set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to the values obtained above.
   - `frontend/.env.local`: set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to the same Client ID.
6. Restart the backend and frontend. The first login will prompt each user to grant Sheets/Drive access; tokens are stored per user in the database for subsequent requests.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Coding standards
- Testing requirements
- Pull request process

## 📝 License

MIT

## 🙏 Acknowledgments

- Google Gemini for AI processing
- Material-UI for beautiful components
- All contributors to this project

## 📮 Support

For issues, questions, or feature requests, please open a GitHub issue.