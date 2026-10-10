# Contributing

Bug reports, device support and pull requests are welcome. Router guides for the [DNAT setup](docs/dnat.md) are especially appreciated.

## Reporting issues

Use the [issue templates](https://github.com/nyffchanium/argoclima-integration/issues/new/choose) and include debug logs:

```yaml
logger:
  logs:
    custom_components.argoclima: debug
```

## Development

Requires Python 3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
scripts/setup          # install Home Assistant, test and lint dependencies
scripts/develop        # run a local Home Assistant on http://localhost:8123 with this integration
```

Before opening a pull request:

```bash
scripts/lint           # ruff check --fix and ruff format
pytest                 # run the test suite
```

The same checks, plus hassfest and HACS validation, run on every pull request.

Optionally, install the [pre-commit](https://pre-commit.com/) hooks with `pre-commit install`.

## Pull requests

1. Fork the repository and branch off `master`.
2. Add or update tests for your change.
3. Update the README if behavior or setup changes.

Contributions are licensed under the [MIT License](LICENSE). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
