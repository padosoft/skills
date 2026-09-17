.PHONY: help catalog validate test lint-email all

EMAIL_SKILL ?= skills/padosoft-email-html-builder
EMAIL       ?= $(EMAIL_SKILL)/templates/reference-welcome-dark.html
SUBJECT     ?= Il tuo account e' pronto: inizia da qui

help:            ## Mostra questo aiuto
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

catalog:         ## Rigenera CATALOG.md, profiles.json e il catalogo dentro la skill router
	python3 scripts/build_catalog.py

validate:        ## Valida ogni SKILL.md e la coerenza del catalogo
	@for d in skills/*/; do python3 $(EMAIL_SKILL)/scripts/validate_skill.py "$$d" || exit 1; done
	python3 scripts/build_catalog.py --check
	python3 scripts/validate_plugins.py

test:            ## Esegue tutti i test
	python3 -m unittest discover -s tests -v

lint-email:      ## Lint di una email: make lint-email EMAIL=path/to/email.html
	python3 $(EMAIL_SKILL)/scripts/lint_email.py $(EMAIL) --subject "$(SUBJECT)"

all: validate test lint-email ## Tutti i controlli (come in CI)
