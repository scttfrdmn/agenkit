# PyPI Publication Guide for Agenkit v0.9.0

## ✅ Completed Steps

1. **Package Configuration** - pyproject.toml configured correctly
2. **URL Fixes** - Updated to correct GitHub repo (scttfrdmn/agenkit) and website (agenkit.dev)
3. **Build** - Successfully built distribution packages:
   - `dist/agenkit-0.9.0.tar.gz` (source distribution)
   - `dist/agenkit-0.9.0-py3-none-any.whl` (wheel)

## 📋 Next Steps - Manual Action Required

### Step 1: Create PyPI Account (if needed)

1. Go to https://pypi.org/account/register/
2. Create account with your email
3. Verify email address

### Step 2: Configure PyPI API Token

1. Log in to https://pypi.org
2. Go to Account Settings → API tokens
3. Click "Add API token"
4. **Scope:** "Entire account" (or specific to agenkit after first upload)
5. **Token name:** "Agenkit CLI Upload"
6. Copy the token (starts with `pypi-`)

**Important:** Save this token securely - it's only shown once!

### Step 3: Configure ~/.pypirc

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE
```

**Security Note:** Make sure this file has restrictive permissions:
```bash
chmod 600 ~/.pypirc
```

### Step 4: Test Upload to TestPyPI (Recommended)

1. Create TestPyPI account at https://test.pypi.org/account/register/
2. Generate API token on TestPyPI
3. Update `~/.pypirc` with TestPyPI token
4. Upload to TestPyPI:

```bash
cd /Users/scttfrdmn/src/agenkit

# Install twine if needed
uv pip install twine

# Upload to TestPyPI
uv run python -m twine upload --repository testpypi dist/*
```

5. Verify on TestPyPI: https://test.pypi.org/project/agenkit/
6. Test installation:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agenkit
python -c "import agenkit; print(agenkit.__version__)"
```

### Step 5: Upload to Production PyPI

Once TestPyPI upload is verified:

```bash
cd /Users/scttfrdmn/src/agenkit

# Upload to production PyPI
uv run python -m twine upload dist/*
```

**Output should show:**
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading agenkit-0.9.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ XX.X/XX.X kB • XX:XX • X.X MB/s
Uploading agenkit-0.9.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ XX.X/XX.X MB • XX:XX • X.X MB/s

View at:
https://pypi.org/project/agenkit/0.9.0/
```

### Step 6: Verify Production Upload

1. **Check PyPI page:** https://pypi.org/project/agenkit/
2. **Verify metadata** (description, links, classifiers)
3. **Test installation:**

```bash
# In a new virtualenv or clean environment
pip install agenkit
python -c "import agenkit; print(agenkit.__version__)"
# Should print: 0.9.0
```

4. **Test basic functionality:**

```python
from agenkit import Agent, Message

class TestAgent(Agent):
    @property
    def name(self) -> str:
        return "test"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")

# Should work without errors
import asyncio
agent = TestAgent()
result = asyncio.run(agent.process(Message(role="user", content="Hello")))
print(result.content)  # Should print: Echo: Hello
```

### Step 7: Update Documentation

After successful PyPI publication:

1. **Add PyPI badge to README.md:**
```markdown
[![PyPI version](https://badge.fury.io/py/agenkit.svg)](https://pypi.org/project/agenkit/)
[![Downloads](https://pepy.tech/badge/agenkit)](https://pepy.tech/project/agenkit)
```

2. **Update installation instructions** in README.md (already correct):
```bash
pip install agenkit
```

3. **Announce on:**
   - GitHub Discussions
   - Twitter/X (if applicable)
   - Reddit r/MachineLearning, r/Python
   - Hacker News (Show HN)

## 🚨 Common Issues and Solutions

### Issue: "File already exists"
**Cause:** Version already published to PyPI (can't overwrite)
**Solution:** Increment version number in pyproject.toml and rebuild

### Issue: "Invalid or non-existent authentication"
**Cause:** Wrong API token or username
**Solution:** Verify `~/.pypirc` has correct token starting with `pypi-`

### Issue: "Package name already taken"
**Cause:** Someone else registered the package name
**Solution:** Shouldn't happen - agenkit should be available

### Issue: Import fails after install
**Cause:** Missing dependencies
**Solution:** Check pyproject.toml dependencies are correct

## 📊 Post-Publication Monitoring

After publication, monitor:

1. **PyPI Stats:**
   - https://pypi.org/project/agenkit/#data
   - Downloads per day/week/month

2. **Installation Issues:**
   - Watch GitHub issues for installation problems
   - Test on different platforms (Linux, macOS, Windows)

3. **Dependency Conflicts:**
   - Monitor for conflicts with popular packages
   - Test with different Python versions (3.10, 3.11, 3.12)

## 🔄 Future Releases

For future releases (0.9.1, 0.10.0, etc.):

1. Set the version once: `scripts/version.py set X.Y.Z` (writes the root `VERSION`
   file and propagates it to `pyproject.toml` and 18 other declarations — #842).
   Do not hand-edit `pyproject.toml`; `make check-version` and CI will reject it.
2. `agenkit/__init__.py` needs no edit — `__version__` is read from installed
   distribution metadata, so it follows `pyproject.toml` automatically.
3. Update CHANGELOG.md
4. Git commit and tag
5. Rebuild package: `rm -rf dist/ && uv run python -m build`
6. Upload: `uv run python -m twine upload dist/*`

## ✅ Success Criteria

- [ ] Package visible at https://pypi.org/project/agenkit/
- [ ] `pip install agenkit` works
- [ ] Version shows as 0.9.0
- [ ] All metadata correct (description, URLs, author)
- [ ] Basic imports work
- [ ] Dependencies install correctly

## 📝 Notes

- **Package size:** ~195KB (wheel), ~11MB (source with examples/docs/tests)
- **Python requirement:** >=3.10
- **License:** Apache 2.0
- **Development Status:** Beta
