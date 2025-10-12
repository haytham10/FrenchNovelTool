<div align="center">
  <img src="https://raw.githubusercontent.com/haytham10/FrenchNovelTool/master/frontend/public/logo.png" alt="French Novel Tool Logo" width="120">
  <h1>French Novel Tool</h1>
  <p>
    <strong>An AI-powered web application to process French novel PDFs, normalize sentence length using Google Gemini, and export results directly to Google Sheets.</strong>
  </p>
  <p>
    <a href="#-features">Features</a> •
    <a href="#-architecture">Architecture</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-getting-started">Getting Started</a> •
    <a href="#-api-overview">API Overview</a> •
    <a href="#-contributing">Contributing</a>
  </p>
</div>

---

This full-stack application provides a seamless workflow for literary analysis, featuring a sophisticated credit system, robust job tracking, and a polished, responsive user interface built with Next.js and Material-UI.

## ✨ Features

### Core Functionality
- 📄 **PDF Text Extraction**: Upload PDF files and extract raw text content on the server.
- 🤖 **AI-Powered Normalization**: Utilizes Google Gemini to intelligently split long sentences while preserving their original meaning and context.
- 📊 **Google Sheets Export**: Export processed sentences directly to a new Google Sheet, with automatic header formatting.
- 📁 **Google Drive Integration**: Organize exported spreadsheets into user-specified folders in Google Drive.
- 📚 **Vocabulary Coverage Tool** *(New)*: Analyze sentences based on high-frequency vocabulary lists for optimized language learning:
    - **Filter Mode**: Find sentences with ≥95% common words (4-8 words) for drilling - perfect for rapid vocabulary acquisition
    - **Coverage Mode**: Select minimal sentence set covering all target words for comprehensive learning
    - **Word List Management**: Upload/manage custom word lists (CSV), with French 2K global default
    - **spaCy NLP**: Intelligent lemmatization handles plurals, conjugations, and elisions (l', d')

### Credit & Job Tracking System
- 💳 **Monthly Credit Allocation**: Users receive a monthly grant of credits for processing documents.
- 📈 **Usage-Based Pricing**: A pay-per-use model where credits are consumed based on the number of tokens processed and the AI model selected.
- 🔄 **Two-Phase Commit Accounting**:
    1. **Preflight Estimate**: Get a cost estimate before committing to a job.
    2. **Credit Reservation**: Credits are "soft-reserved" when a job is confirmed.
    3. **Finalization**: After processing, the actual credit cost is calculated, and the user's balance is adjusted.
- 🗂️ **Job Tracking & History**: A complete audit trail of all processing jobs, including status, cost, and links to results.
- 💰 **Transparent Ledger**: A detailed credit ledger provides a full history of all transactions (grants, reservations, final costs, and refunds).

### Authentication & Security
- 🔐 **JWT Authentication**: Secure, stateless authentication using JSON Web Tokens with automated token refresh.
- 🔑 **Google OAuth 2.0**: Seamless and secure user login via Google accounts, requesting necessary permissions for Google Sheets and Drive.
- 🛡️ **API Rate Limiting**: Per-endpoint rate limiting to prevent abuse and ensure fair usage.
- ⚙️ **CORS Protection**: Whitelist-based Cross-Origin Resource Sharing to secure the API.
- 📝 **Schema Validation**: All incoming API requests are validated against Marshmallow schemas to prevent invalid data.

### User Experience & Interface
- 🎨 **Modern UI**: A clean, responsive interface built with Next.js 15 and Material-UI v7.
- 🌓 **Light/Dark Mode**: Switch between themes for user comfort.
- ✏️ **Inline Editing**: Directly edit normalized sentences in the results table before exporting.
- 🔍 **Debounced Search & Filtering**: Fast, responsive filtering in the processing history table.
- 🔔 **Real-Time Notifications**: Toast notifications for all major actions (success, error, info).
- ⏳ **Context-Aware Loading**: Full-page overlays and granular loading indicators provide clear feedback during authentication, file processing, and data fetching.
- ♿ **Accessibility**: Designed with accessibility in mind, including semantic HTML and ARIA attributes.

## 🏗️ Architecture

The project follows a modern, decoupled architecture with a service-oriented backend and a reactive frontend.

- **Backend (Flask)**: A robust API built with a service layer that encapsulates all business logic (e.g., `CreditService`, `JobService`, `PDFService`). This promotes separation of concerns and makes the codebase modular and testable. Flask Blueprints are used to organize routes by functionality (auth, credits, main).

- **Frontend (Next.js)**: A server-side rendered (SSR) React application using the App Router. It communicates with the backend via a centralized API client (axios) that handles automatic JWT token refresh. Global state is managed with Zustand, while server state and data fetching are handled by TanStack Query.

- **Database (PostgreSQL)**: A relational database managed by SQLAlchemy and Flask-Migrate. The schema is designed to support the credit system, job tracking, and user data.

- **Authentication Flow**:
  1. Frontend initiates Google OAuth 2.0 login.
  2. Backend receives the Google auth code, validates it, and creates a user record.
  3. Backend generates a JWT access token and a refresh token.
  4. Frontend stores the tokens, using the access token for API requests. An axios interceptor automatically uses the refresh token to get a new access token when it expires.

## 🛠️ Tech Stack

| Category | Technology | Description |
| --- | --- | --- |
| **Backend** | Flask 3.0 | Core web framework with a service-oriented architecture. |
| | Flask-JWT-Extended | For handling JSON Web Token authentication. |
| | SQLAlchemy | ORM for interacting with the PostgreSQL database. |
| | Flask-Migrate | For handling database schema migrations. |
| | Marshmallow | For request/response validation and serialization. |
| | Google Gemini AI | AI model for sentence normalization. |
| | Gunicorn | Production-ready WSGI server. |
| **Frontend** | Next.js 15 | React framework with App Router for SSR and routing. |
| | React 19 | Core UI library. |
| | TypeScript | For type safety and improved developer experience. |
| | Material-UI v7 | Component library for a polished and responsive UI. |
| | TanStack Query v5 | For managing server state, caching, and data fetching. |
| | Zustand | For minimal and efficient client state management. |
| | Axios | For making API requests with a token-refresh interceptor. |
| **Database** | PostgreSQL | Relational database for storing all application data. |
| | Redis | Used for rate limiting in production environments. |
| **DevOps** | Docker & Docker Compose | For containerizing the application for easy setup and deployment. |
| | Vercel | Optimized for serverless deployment of both frontend and backend. |
| | Pytest | For backend testing with comprehensive coverage reports. |
| | Pre-commit Hooks | For automated code formatting and linting (Black, Flake8, ESLint). |

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- A Google Cloud project with **Gemini, Google Drive, and Google Sheets APIs** enabled.
- OAuth 2.0 Credentials (Client ID & Secret).

### 1. Docker Quick Start (Recommended)
This is the fastest way to get the entire application running.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/haytham10/FrenchNovelTool.git
    cd FrenchNovelTool
    ```

2.  **Set up environment files:**
    ```bash
    # For the backend
    cp backend/.env.example backend/.env

    # For the frontend
    cp frontend/.env.example frontend/.env.local
    ```

3.  **Configure environment variables:**
    - Edit `backend/.env` and `frontend/.env.local` to add your Google Client ID, Client Secret, Gemini API Key, and a database URL.

4.  **Run the application:**
    ```bash
    docker-compose up --build
    ```
    The application will be available at `http://localhost:3000`.

### 2. Manual Setup
Follow these steps to run the frontend and backend services separately.

<details>
<summary><strong>Backend Manual Setup</strong></summary>

```bash
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt # For development

# Set up and configure your .env file
cp .env.example .env
# Edit .env with your credentials

# Initialize and upgrade the database
flask db upgrade

# Run the development server
flask run
```
The API will be available at `http://localhost:5000`.
</details>

<details>
<summary><strong>Frontend Manual Setup</strong></summary>

```bash
cd frontend
npm install

# Set up and configure your .env.local file
cp .env.example .env.local
# Edit .env.local with your Google Client ID and API URL

# Run the development server
npm run dev
```
The frontend will be available at `http://localhost:3000`.
</details>


## 📡 API Overview

The backend exposes a versioned REST API at `/api/v1`.

| Group | Endpoint | Method | Description |
| --- | --- | --- | --- |
| **Auth** | `/auth/google` | `POST` | Exchange a Google auth code for a JWT. |
| | `/auth/refresh` | `POST` | Refresh an expired access token. |
| | `/auth/me` | `GET` | Get the currently authenticated user's profile. |
| **Processing** | `/process-pdf` | `POST` | Upload and process a PDF file. |
| | `/export-to-sheet`| `POST` | Export processed sentences to Google Sheets. |
| **Credits** | `/me/credits` | `GET` | Get the user's current credit balance. |
| | `/credits/ledger` | `GET` | Get the user's transaction history. |
| **Jobs** | `/estimate` | `POST` | Estimate the credit cost for processing text. |
| | `/jobs/confirm` | `POST` | Confirm a job and reserve credits. |
| | `/jobs/{id}/finalize`|`POST` | Finalize a job with actual token usage. |
| | `/jobs` | `GET` | Get a list of the user's past jobs. |
| **Data** | `/history` | `GET` | Get the user's processing history. |
| | `/settings` | `GET/POST` | Get or update user settings. |

For more details, see the [API Documentation](backend/API_DOCUMENTATION.md).

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development standards, testing procedures, and the pull request process.

## 📝 License

This project is licensed under the MIT License.