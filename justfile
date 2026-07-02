import year="2025":
    uv run reimport --year {{year}}

reimport year="2025":
    uv run reimport --year {{year}}

fava:
    uv run fava main.beancount

queries:
    ./scripts/run-demo-queries.sh main.beancount

regen-demo-data:
    uv run python scripts/generate_demo_data.py

test:
    uv run --no-editable pytest
