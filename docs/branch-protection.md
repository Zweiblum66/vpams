# Branch Protection Rules

This document outlines the branch protection rules for the MAMS project. These settings should be configured in your GitHub/GitLab repository settings.

## Protected Branches

### `main` (Production)

**Protection Rules:**
- ✅ Require pull request reviews before merging
  - Required approving reviews: 2
  - Dismiss stale pull request approvals when new commits are pushed
  - Require review from CODEOWNERS
- ✅ Require status checks to pass before merging
  - Require branches to be up to date before merging
  - Required status checks:
    - `CI / lint-python`
    - `CI / test-python`
    - `CI / lint-frontend`
    - `CI / test-frontend`
    - `CI / security-scan`
- ✅ Require conversation resolution before merging
- ✅ Require signed commits
- ✅ Include administrators
- ✅ Restrict who can push to matching branches
  - Only allow: `mams-admins` team
- ❌ Do not allow force pushes
- ❌ Do not allow deletions

### `develop` (Development)

**Protection Rules:**
- ✅ Require pull request reviews before merging
  - Required approving reviews: 1
  - Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
  - Required status checks:
    - `CI / lint-python`
    - `CI / test-python`
    - `CI / lint-frontend`
    - `CI / test-frontend`
- ✅ Require conversation resolution before merging
- ✅ Include administrators
- ❌ Do not allow force pushes
- ❌ Do not allow deletions

## Branch Naming Conventions

### Feature Branches
```
feature/SERVICE-STORY_ID-description
```
Example: `feature/API-M2-001-jwt-authentication`

### Bug Fix Branches
```
fix/SERVICE-issue-description
```
Example: `fix/USER-001-password-reset-error`

### Release Branches
```
release/VERSION
```
Example: `release/1.0.0`

### Hotfix Branches
```
hotfix/VERSION-description
```
Example: `hotfix/1.0.1-security-patch`

## Git Flow Process

### 1. Starting a New Feature
```bash
git checkout develop
git pull origin develop
git checkout -b feature/SERVICE-STORY_ID-description
```

### 2. Working on a Feature
```bash
# Make changes
git add .
git commit -m "feat(service): add new capability"
git push origin feature/SERVICE-STORY_ID-description
```

### 3. Creating a Pull Request
1. Push your branch to origin
2. Create PR from feature branch to `develop`
3. Fill in the PR template
4. Request reviews from team members
5. Address review feedback
6. Ensure all CI checks pass

### 4. Merging Strategy
- **Feature → Develop**: Squash and merge
- **Develop → Main**: Create a merge commit
- **Hotfix → Main**: Create a merge commit
- **Hotfix → Develop**: Create a merge commit

### 5. Release Process
```bash
# Start release
git checkout -b release/1.0.0 develop

# Finish release
git checkout main
git merge --no-ff release/1.0.0
git tag -a v1.0.0 -m "Release version 1.0.0"
git checkout develop
git merge --no-ff release/1.0.0
```

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body

footer
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```
feat(api-gateway): add rate limiting middleware

Implement token bucket algorithm for API rate limiting.
Default limits: 100 requests per minute per user.

Closes #123
```

## Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Closes #(issue)

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
Add screenshots to help explain your changes.
```

## CODEOWNERS

Create `.github/CODEOWNERS`:

```
# Global owners
* @mams-admins

# Service-specific owners
/services/api-gateway/ @api-team
/services/user-management/ @auth-team
/services/asset-management/ @core-team
/frontend/ @frontend-team

# Documentation
/docs/ @docs-team
*.md @docs-team

# Infrastructure
/infrastructure/ @devops-team
/docker-compose.yml @devops-team
Dockerfile* @devops-team
```

## Automated Workflows

### Auto-label PRs
Based on:
- Files changed
- PR title
- Branch name

### Auto-assign Reviewers
Based on:
- CODEOWNERS
- Round-robin assignment
- Expertise areas

### Stale PR Management
- Mark as stale after 14 days of inactivity
- Close after 30 days of inactivity
- Exempt PRs with `keep-open` label