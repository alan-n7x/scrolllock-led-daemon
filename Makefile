.PHONY: test test-verbose lint install uninstall clean help

test:
	python -m pytest tests/ -v

test-verbose:
	python -m pytest tests/ -v --tb=long -s

lint:
	python -m py_compile src/scrolllock_led_daemon.py

install:
	sudo ./scripts/install.sh

uninstall:
	sudo ./scripts/uninstall.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete

help:
	@echo "Targets:"
	@echo "  test          Run tests with pytest"
	@echo "  lint          Check syntax with py_compile"
	@echo "  install       Install the daemon (requires sudo)"
	@echo "  uninstall     Uninstall the daemon (requires sudo)"
	@echo "  clean         Remove __pycache__ directories"
	@echo "  help          Show this message"
