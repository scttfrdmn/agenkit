# Agenkit Documentation Site

This directory contains the source for the Agenkit documentation website, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Local Development

### Prerequisites

```bash
pip install mkdocs-material
```

### Build and Serve Locally

```bash
# From the project root
mkdocs serve
```

Visit `http://127.0.0.1:8000` to view the documentation.

### Build Static Site

```bash
mkdocs build
```

This generates the static site in `site/` directory.

## Deployment to GitHub Pages

### Option 1: Manual Deployment

```bash
mkdocs gh-deploy
```

This builds and pushes the site to the `gh-pages` branch.

### Option 2: GitHub Actions (Recommended)

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - 'docs-site/**'
      - 'mkdocs.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: 3.x
      - run: pip install mkdocs-material
      - run: mkdocs gh-deploy --force
```

## Custom Domain Setup (agenkit.dev)

1. **DNS Configuration** (at your domain registrar):
   ```
   Type: A
   Name: @
   Value: 185.199.108.153
   Value: 185.199.109.153
   Value: 185.199.110.153
   Value: 185.199.111.153
   
   Type: CNAME
   Name: www
   Value: scttfrdmn.github.io
   ```

2. **GitHub Repository Settings**:
   - Go to Settings → Pages
   - Set custom domain to: `agenkit.dev`
   - Enable "Enforce HTTPS"

3. **CNAME File** (already created):
   - File: `docs-site/CNAME`
   - Content: `agenkit.dev`

## Directory Structure

```
docs-site/
├── index.md                    # Homepage
├── getting-started/            # Getting started guides
├── core-concepts/              # Architecture and concepts
├── features/                   # Feature documentation
├── guides/                     # Language-specific guides
├── examples/                   # Code examples
├── api/                        # API reference
├── performance/                # Benchmarks
├── deployment/                 # Deployment guides
└── contributing.md             # Contribution guidelines
```

## Updating Documentation

1. Edit markdown files in `docs-site/`
2. Test locally with `mkdocs serve`
3. Commit and push to `main` branch
4. GitHub Actions deploys automatically (if configured)
   OR run `mkdocs gh-deploy` manually

## Configuration

See `mkdocs.yml` in the project root for site configuration including:
- Theme settings
- Navigation structure
- Plugins
- Extensions
