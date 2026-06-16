# Contributing

Thanks for improving `action-pin-check`.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m unittest discover -s tests
```

## Good contributions

- Add workflow fixtures that represent real GitHub Actions patterns.
- Improve finding messages without making them alarmist.
- Add output formats that help CI and review tooling.
- Keep the default scanner dependency-free and deterministic.

## Pull request checklist

- Add or update tests for behavior changes.
- Run `python -m unittest discover -s tests`.
- Run `action-pin-check examples/workflows --fail-on never`.
- Keep README commands accurate.

## Project direction

This project should stay narrow. It checks action refs; it should not become a full CI security scanner.
