# Contributing to Personal MCP Server

Thank you for your interest in contributing to Personal MCP Server! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- Basic understanding of FastAPI and MCP protocol

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/personal-mcp-server.git
   cd personal-mcp-server
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install development dependencies
   ```

4. **Run Tests**
   ```bash
   pytest
   ```

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Write docstrings for all public functions and classes
- Keep line length under 88 characters (Black formatter standard)

### Code Formatting
We use Black for code formatting:
```bash
black .
```

### Linting
We use flake8 for linting:
```bash
flake8 .
```

### Type Checking
We use mypy for type checking:
```bash
mypy .
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_specific.py
```

### Writing Tests
- Write tests for all new features
- Maintain or improve test coverage
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

Example test structure:
```python
def test_add_context_success():
    # Arrange
    context_item = ContextItem(id="test", content="test content")
    
    # Act
    result = context_store.add_context(context_item)
    
    # Assert
    assert result["status"] == "added"
    assert result["id"] == "test"
```

## 📝 Commit Guidelines

### Commit Message Format
Use conventional commits format:
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add new context search endpoint
fix(git): resolve repository detection issue
docs(readme): update installation instructions
```

### Commit Best Practices
- Make atomic commits (one logical change per commit)
- Write clear, descriptive commit messages
- Reference issues when applicable (`fixes #123`)

## 🔄 Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following our guidelines
   - Add tests for new functionality
   - Update documentation if needed

3. **Test Your Changes**
   ```bash
   pytest
   black .
   flake8 .
   mypy .
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

### PR Requirements
- [ ] All tests pass
- [ ] Code is properly formatted (Black)
- [ ] No linting errors (flake8)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format

## 🐛 Bug Reports

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages (if any)

Use the bug report template when creating issues.

## 💡 Feature Requests

When requesting features:
- Describe the problem you're trying to solve
- Explain why this feature would be useful
- Provide examples of how it would work
- Consider implementation complexity

## 📚 Documentation

### API Documentation
- All endpoints must have proper docstrings
- Include request/response examples
- Document error cases

### Code Documentation
- Use clear, descriptive variable names
- Add comments for complex logic
- Keep docstrings up to date

## 🏗️ Architecture Guidelines

### MCP Protocol
- Follow MCP specification strictly
- Maintain backward compatibility
- Document any protocol extensions

### FastAPI Best Practices
- Use Pydantic models for request/response validation
- Implement proper error handling
- Use dependency injection where appropriate

### Code Organization
```
personal-mcp-server/
├── mcp_server.py           # MCP mode entry point
├── unified_mcp_server.py   # Main server implementation
├── tests/                  # Test files
├── docs/                   # Documentation
└── examples/               # Usage examples
```

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Provide constructive feedback
- Follow the code of conduct

## 📞 Getting Help

- Check existing issues and documentation
- Ask questions in GitHub Discussions
- Join our community chat (if available)
- Tag maintainers for urgent issues

## 🎉 Recognition

Contributors will be:
- Listed in the README
- Mentioned in release notes
- Invited to join the contributors team (for regular contributors)

Thank you for contributing to Personal MCP Server! 🚀
