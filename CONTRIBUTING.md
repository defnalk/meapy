# Contributing to meapy

Thank you for considering a contribution! meapy welcomes bug reports, feature requests,
documentation improvements, and pull requests of all sizes.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Reporting Issues](#reporting-issues)
3. [Development Setup](#development-setup)
4. [Coding Standards](#coding-standards)
5. [Writing Tests](#writing-tests)
6. [Submitting a Pull Request](#submitting-a-pull-request)
7. [Commit Message Convention](#commit-message-convention)

---

## Code of Conduct

Be respectful and constructive. This project follows the
[Contributor Covenant](https://www.contributor-covenant.org/) v2.1.

---

## Reporting Issues

Search [existing issues](https://github.com/defnalk/meapy/issues) first. When opening a
new one, include:

- meapy version (`python -c "import meapy; print(meapy.__version__)"`)
- Python version and OS
- A minimal reproducible example
- The full traceback if reporting a bug

---

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/meapy.git
cd meapy

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev extras
pip install -e ".[dev]"

# 4. Verify the test suite passes
make test
```

---

## Coding Standards

| Tool | Purpose | Command |
|---|---|---|
| **ruff** | Lint + format | `make lint` |
| **mypy** | Type checking | `mypy src/meapy` |
| **pytest** | Tests + coverage | `make test` |

Rules to follow:

- **Full type hints** on every public function and class, including return types.
- **Google-style docstrings** with `Args:`, `Returns:`, `Raises:`, and `Example::` sections.
- **`__all__`** must be defined in every module.
- **No magic numbers** — add any new constant to `constants.py` with a source citation.
- **Logging** (`logger.debug / .info / .warning`) instead of `print`.
- All public functions must handle edge cases with informative `ValueError` or
  `RuntimeError` messages that explain _why_ the input is invalid, not just that it is.

---

## Writing Tests

- New functions → new unit tests in `tests/unit/test_<module>.py`.
- New end-to-end flows → integration tests in `tests/integration/`.
- Use `pytest.mark.parametrize` for input variations.
- Aim to keep unit tests fast (< 1 s each); mark slow tests with `@pytest.mark.slow`.
- Coverage must remain ≥ 90 % after your change (`make test` enforces this).

Fixtures shared across test files belong in `tests/conftest.py`.

---

## Submitting a Pull Request

1. Create a feature branch:
   ```bash
   git checkout -b feat/packed-column-flooding
   ```
2. Make your changes, keeping commits small and focused.
3. Run the full check suite locally:
   ```bash
   make lint && make test
   ```
4. Push and open a PR against `main`.
5. Fill in the PR template — explain _what_ and _why_, and link any related issue.
6. A maintainer will review within a few days. Please address review comments by adding
   new commits (do not force-push during review).

---

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`

Examples:
```
feat(mass_transfer): add Billet–Schultes K_OGa correlation
fix(pump): handle negative flowrate extrapolation gracefully
docs(README): add packed-column diagram to quick-start section
test(heat_transfer): parametrize LMTD tests for co-current cases
```
