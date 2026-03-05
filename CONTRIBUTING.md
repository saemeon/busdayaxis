# Contributing

Bug reports, feature requests, and pull requests are welcome on [GitHub](https://github.com/saemeon/busdayaxis/issues).

## Development setup

```bash
git clone https://github.com/saemeon/busdayaxis
cd busdayaxis
pip install -e ".[dev]"
```

Pre-commit hooks are managed with [prek](https://github.com/saemeon/prek). They run automatically on `git commit` once you have installed the dev dependencies.

## Running tests

```bash
pytest
```

## Building docs

```bash
pip install -e ".[doc]"
mkdocs serve
```
