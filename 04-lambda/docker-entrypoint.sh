#!/bin/bash
set -e

# Check if venv exists, if not create it and install packages
if [ ! -f "/opt/venv/bin/python" ]; then
    echo "Python venv not found. Creating venv and installing packages..."
    
    # Install uv if not available
    if ! command -v uv &> /dev/null; then
        pip install --no-cache-dir uv
    fi
    
    # Create venv
    uv venv /opt/venv
    
    # Activate and install packages
    source /opt/venv/bin/activate
    
    # Install from pyproject.toml if it exists
    if [ -f "/app/pyproject.toml" ]; then
        uv pip install -e /app
    else
        # Fallback: install from copied pyproject.toml
        cd /app && uv pip install -e .
    fi
    
    echo "✓ Python packages installed and persisted to volume"
    
    # Run crawl4ai-setup after package installation
    echo "Running crawl4ai-setup to install Playwright browsers..."
    if command -v crawl4ai-setup &> /dev/null; then
        crawl4ai-setup || echo "Warning: crawl4ai-setup failed, but continuing..."
    else
        # Fallback: try running via python module
        python -m crawl4ai.setup || echo "Warning: crawl4ai setup failed, but continuing..."
    fi
    echo "✓ Crawl4AI setup completed"
else
    echo "✓ Using existing Python packages from volume"
    # Always activate venv if it exists
    source /opt/venv/bin/activate
    
    # Check if Playwright browsers are installed, if not run setup
    # Playwright installs to ~/.cache/ms-playwright, check if it exists
    PLAYWRIGHT_CACHE="${HOME:-/root}/.cache/ms-playwright"
    if [ ! -d "$PLAYWRIGHT_CACHE" ] || [ -z "$(ls -A "$PLAYWRIGHT_CACHE" 2>/dev/null)" ]; then
        echo "Playwright browsers not found. Running crawl4ai-setup..."
        if command -v crawl4ai-setup &> /dev/null; then
            crawl4ai-setup || echo "Warning: crawl4ai-setup failed, but continuing..."
        else
            # Fallback: try running via python module
            python -m crawl4ai.setup || echo "Warning: crawl4ai setup failed, but continuing..."
        fi
        echo "✓ Crawl4AI setup completed"
    else
        echo "✓ Playwright browsers already installed"
    fi
fi

# Ensure PATH includes venv
export PATH="/opt/venv/bin:$PATH"

# Run the application with explicit PATH
# This ensures uvicorn and other commands are found
exec env PATH="/opt/venv/bin:$PATH" "$@"

