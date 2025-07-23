# Contributing to MAMS

Thank you for considering contributing to MAMS! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept feedback gracefully

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/MyVideoMAM.git
   cd MyVideoMAM
   ```
3. Set up the development environment:
   ```bash
   make dev-install
   make up
   ```

## Development Workflow

### Branch Naming

- Feature branches: `feature/SERVICE-STORY_ID-description`
- Bug fixes: `fix/SERVICE-issue-description`
- Documentation: `docs/description`
- Refactoring: `refactor/SERVICE-description`

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat(api-gateway): add rate limiting middleware
fix(user-management): resolve password reset issue
docs(readme): update installation instructions
```

### Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes following our coding standards
3. Write or update tests as needed
4. Ensure all tests pass: `make test`
5. Run linting: `make lint`
6. Update documentation if needed
7. Submit a pull request to `develop`

### PR Requirements

- Clear description of changes
- Reference related issues
- All CI checks passing
- Code review approval from at least one maintainer
- No merge conflicts

## Coding Standards

### Python

- Follow PEP 8
- Use Black for formatting
- Use Ruff for linting
- Type hints required for all functions
- Docstrings for all public functions/classes
- Minimum 90% test coverage

Example:
```python
from typing import Optional, List
from pydantic import BaseModel

class AssetCreate(BaseModel):
    """Schema for creating a new asset."""
    
    name: str
    file_path: str
    tags: Optional[List[str]] = None
    
async def create_asset(
    asset_data: AssetCreate,
    user_id: str
) -> Asset:
    """
    Create a new asset in the system.
    
    Args:
        asset_data: The asset creation data
        user_id: ID of the user creating the asset
        
    Returns:
        The created asset object
        
    Raises:
        DuplicateError: If asset already exists
    """
    # Implementation
    pass
```

### TypeScript/React

- Use TypeScript strict mode
- Functional components with hooks
- ESLint and Prettier for formatting
- Interface over type when possible
- Props interfaces for all components

Example:
```typescript
interface AssetCardProps {
  asset: Asset;
  onSelect?: (asset: Asset) => void;
  className?: string;
}

export const AssetCard: React.FC<AssetCardProps> = ({
  asset,
  onSelect,
  className
}) => {
  return (
    <Card className={className} onClick={() => onSelect?.(asset)}>
      <CardContent>
        <Typography variant="h6">{asset.name}</Typography>
      </CardContent>
    </Card>
  );
};
```

## Testing

### Python Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_asset(
    client: AsyncClient,
    auth_headers: dict
):
    """Test asset creation endpoint."""
    response = await client.post(
        "/api/v1/assets",
        json={"name": "test.mp4", "file_path": "/test.mp4"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "test.mp4"
```

### React Tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { AssetCard } from './AssetCard';

describe('AssetCard', () => {
  it('renders asset name', () => {
    const asset = { id: '1', name: 'Test Asset' };
    render(<AssetCard asset={asset} />);
    expect(screen.getByText('Test Asset')).toBeInTheDocument();
  });
});
```

## Documentation

- Update README.md for significant changes
- Add docstrings to all public APIs
- Update OpenAPI specs for API changes
- Include examples in documentation
- Keep architecture diagrams current

## Performance Guidelines

- Use async/await for I/O operations
- Implement proper database indexing
- Cache frequently accessed data
- Paginate large result sets
- Profile code for bottlenecks

## Security Guidelines

- Never commit secrets or credentials
- Validate all user input
- Use parameterized queries
- Implement proper authentication/authorization
- Keep dependencies updated

## Questions?

- Check existing issues and PRs
- Join our Discord server
- Email: dev@mams-project.com

Thank you for contributing to MAMS!