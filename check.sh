#!/bin/bash
set -e

echo
echo "========== RUFF =========="
venv/bin/python -m ruff check .

echo
echo "========== COMPILE =========="
venv/bin/python -m compileall app bot.py

echo
echo "========== IMPORT =========="
venv/bin/python -m app.utils.import_check

echo
echo "========== ARCHITECTURE =========="
venv/bin/python -m app.utils.architecture_check

echo
echo "========== PYTEST =========="
venv/bin/python -m pytest tests -q

echo
echo
echo "✓ ALL CHECKS PASSED"
