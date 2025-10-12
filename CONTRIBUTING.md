# Contributing to French Novel Tool

Thank you for your interest in contributing to the French Novel Tool! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Show empathy towards others
- Accept responsibility and apologize for mistakes

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Git
- Google Cloud account with Gemini and Drive/Sheets APIs enabled

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/french-novel-tool.git
   cd french-novel-tool
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/french-novel-tool.git
   ```

## Development Setup

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run the development server
flask --app run.py run
```

### Frontend Setup

```bash
cd frontend
npm install

# Copy and configure environment variables
cp .env.example .env.local
# Edit .env.local with your API URL

# Run the development server
npm run dev
```

### Docker Setup (Optional)

```bash
# From project root
docker-compose up --build
```

## Making Changes

### Branching Strategy

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes in logical, focused commits
3. Keep commits atomic and well-described

### Commit Messages

Follow the conventional commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(backend): add rate limiting to API endpoints

Implemented Flask-Limiter to add rate limiting protection
to all API endpoints. Configurable via environment variables.

Closes #123
```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable and function names
- Add docstrings to all functions and classes

**Example:**
```python
def process_sentences(text: str, max_length: int = 8) -> List[str]:
    """
    Process text and split into sentences with maximum length.
    
    Args:
        text: The input text to process
        max_length: Maximum word count per sentence
        
    Returns:
        List of processed sentences
        
    Raises:
        ValueError: If text is empty or max_length is invalid
    """
    # Implementation
```

### TypeScript (Frontend)

- Follow the project's ESLint configuration
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use meaningful component and variable names
- Add JSDoc comments for complex functions

**Example:**
```typescript
/**
 * Uploads a PDF file and processes it using the backend API
 * @param file - The PDF file to upload
 * @returns Promise resolving to array of processed sentences
 * @throws Error if upload fails or file is invalid
 */
async function processPdf(file: File): Promise<string[]> {
  // Implementation
}
```

### Code Formatting

We use automated code formatters:

- **Python**: Black
- **TypeScript/JavaScript**: ESLint with auto-fix

Install pre-commit hooks to format automatically:

```bash
pip install pre-commit
pre-commit install
```

Now your code will be automatically formatted before each commit.

## Testing

### Backend Tests

```bash
cd backend
pytest
pytest --cov=app --cov-report=html  # With coverage
```

Write tests for:
- New features
- Bug fixes
- Edge cases
- API endpoints
- Service layer functions

**Example:**
```python
def test_process_pdf_success(client, mock_gemini):
    """Test successful PDF processing"""
    data = {'pdf_file': (io.BytesIO(b'test pdf'), 'test.pdf')}
    response = client.post('/api/v1/process-pdf', data=data)
    assert response.status_code == 200
    assert 'sentences' in response.json
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:coverage  # With coverage
```

### Manual Testing

Before submitting a PR:
1. Test the feature manually in the browser
2. Test error cases
3. Test on different screen sizes (responsive design)
4. Check console for errors or warnings

## Submitting Changes

### Before Submitting

1. **Update documentation** if you've changed functionality
2. **Add tests** for new features or bug fixes
3. **Run linters** and fix any issues:
   ```bash
   # Backend
   cd backend
   black .
   flake8
   
   # Frontend
   cd frontend
   npm run lint
   ```
4. **Run tests** and ensure they pass:
   ```bash
   # Backend
   cd backend
   pytest
   
   # Frontend
   cd frontend
   npm test
   ```
5. **Update CHANGELOG** (if applicable)
6. **Rebase on latest main**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Creating a Pull Request

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Go to the original repository and create a Pull Request

3. Fill out the PR template with:
   - **Description**: What does this PR do?
   - **Motivation**: Why is this change needed?
   - **Testing**: How was this tested?
   - **Screenshots**: If UI changes, include before/after screenshots
   - **Related Issues**: Link to related issues

4. Request review from maintainers

### PR Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged
- Your contribution will be credited in the release notes

## Reporting Issues

### Bug Reports

When reporting bugs, include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Numbered steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python/Node version, browser
- **Screenshots**: If applicable
- **Logs**: Relevant error messages or logs

### Feature Requests

When requesting features, include:

- **Problem**: What problem does this solve?
- **Solution**: Proposed solution
- **Alternatives**: Alternative solutions considered
- **Additional Context**: Any other relevant information

### Security Issues

**DO NOT** open public issues for security vulnerabilities. Instead:
- Email the maintainers directly
- Provide detailed information about the vulnerability
- Allow time for the issue to be fixed before disclosure

## Questions?

If you have questions about contributing:
- Check existing issues and PRs
- Ask in discussions
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to French Novel Tool! 🎉


