.PHONY: setup api web gen test check

SCHEMA := $(CURDIR)/web/node_modules/.tmp/openapi.json

setup:
	cd api && uv sync
	cd web && pnpm install

api:
	cd api && uv run fastapi dev

web:
	cd web && pnpm exec vp dev

# openapi-typescript needs the TypeScript compiler API, which TS 7 doesn't ship,
# so it runs in an isolated dlx context with TS 5 (its declared peer).
gen:
	mkdir -p $(dir $(SCHEMA))
	cd api && uv run python -c 'import json; from golinks_api.main import app; print(json.dumps(app.openapi()))' > $(SCHEMA)
	pnpm dlx --package=openapi-typescript@7.13.0 --package=typescript@5.9.3 openapi-typescript $(SCHEMA) -o web/src/api/schema.d.ts
	cd web && pnpm exec vp fmt src/api/schema.d.ts
	rm -f $(SCHEMA)

test:
	cd api && uv run pytest

check:
	cd api && uv run ruff check . && uv run ruff format --check . && uv run pyrefly check
	cd web && pnpm exec vp check
