.PHONY: test test-verbose lint install uninstall clean help

PREFIX ?= /usr
DESTDIR ?=

test:
	PYTHONPATH=src python -m pytest tests/ -v

test-verbose:
	PYTHONPATH=src python -m pytest tests/ -v --tb=long -s

lint:
	python -m py_compile src/scrolllock_led_daemon.py

install:
	install -Dm755 src/scrolllock_led_daemon.py $(DESTDIR)$(PREFIX)/bin/scrolllock-led-daemon
	install -Dm644 systemd/scrolllock-led-daemon.service $(DESTDIR)/lib/systemd/system/scrolllock-led-daemon.service
	install -Dm644 README.md $(DESTDIR)$(PREFIX)/share/doc/scrolllock-led-daemon/README.md

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/scrolllock-led-daemon
	rm -f $(DESTDIR)/lib/systemd/system/scrolllock-led-daemon.service

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete

help:
	@echo "Targets:"
	@echo "  test          Run tests with pytest"
	@echo "  lint          Check syntax with py_compile"
	@echo "  install       Install into DESTDIR/PREFIX"
	@echo "  uninstall     Remove installed files"
	@echo "  clean         Remove __pycache__ directories"
	@echo "  help          Show this message"