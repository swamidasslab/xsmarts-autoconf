PYTHON ?= python
SITE   ?= _site
PORT   ?= 8000

.PHONY: site serve test check

# Static comparison website from the stored rules and configs.
site:
	$(PYTHON) -m xsmarts_autoconf.site --out $(SITE)

# Build, then serve at http://localhost:$(PORT) (Ctrl-C to stop).
serve: site
	$(PYTHON) -m http.server $(PORT) -d $(SITE)

test:
	$(PYTHON) -m pytest -q

check:
	$(PYTHON) -m xsmarts_autoconf check
