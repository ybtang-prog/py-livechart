# Release Guide for py-livechart

## Pre-release Checklist

1. **Version consistency**: Ensure `pyproject.toml` and `src/py_livechart/__init__.py` both have the same version number (currently `1.2.0`).

2. **Tests pass**: Run `pytest` locally to ensure all tests pass.

3. **Documentation**: Verify README.md and docs/ are up to date.

4. **Git status**: Commit all changes and ensure the repository is clean.

## Release Steps

### Step 1: Prepare the Release

```bash
# Ensure all changes are committed
git add .
git commit -m "Prepare release v1.2.0"

# Push to remote
git push origin main
```

### Step 2: Configure PyPI API Token (One-time setup)

1. Go to https://pypi.org/account/register/ and create an account (if not already done).
2. Generate an API token:
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Name it (e.g., "py-livechart-release")
   - Copy the token (starts with `pypi-`)
3. Add the token to GitHub Secrets:
   - Go to your GitHub repository: https://github.com/ybtang-prog/py-livechart
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Paste your PyPI API token
   - Click "Add secret"

### Step 3: Create and Push Version Tag

```bash
# Create the version tag
git tag v1.2.0

# Push the tag to trigger the GitHub Actions workflow
git push origin v1.2.0
```

### Step 4: Monitor the Release

1. Go to https://github.com/ybtang-prog/py-livechart/actions
2. You should see a workflow run triggered by the tag push
3. The workflow will:
   - Run tests
   - Build wheel and source distribution
   - Upload to PyPI (if tests pass)

### Step 5: Verify Release

After the workflow completes successfully:

1. Check PyPI: https://pypi.org/project/py-livechart/
2. Verify installation:
   ```bash
   pip install py-livechart
   ```
3. Test the installed package:
   ```bash
   python -c "from py_livechart import LiveChartClient; print(LiveChartClient.__module__)"
   ```

## Manual Release (Alternative)

If you prefer to release manually without GitHub Actions:

```bash
# Install build tools
pip install build twine

# Build distributions
python -m build

# Upload to PyPI (requires PyPI credentials)
twine upload dist/*
```

## Post-release

1. Update the version number in `pyproject.toml` and `src/py_livechart/__init__.py` for the next development cycle.
2. Create a GitHub release with release notes.
3. Announce the release (if applicable).

