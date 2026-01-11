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
    # According to crawl4ai docs: https://docs.crawl4ai.com/basic/installation/
    # 1. Install: pip install crawl4ai (already done)
    # 2. Setup: crawl4ai-setup (installs Playwright browsers)
    # 3. Verify: crawl4ai-doctor (optional)
    echo "Running crawl4ai-setup to install Playwright browsers..."
    if command -v crawl4ai-setup &> /dev/null; then
        if crawl4ai-setup; then
            echo "✓ Crawl4AI setup completed successfully"
        else
            echo "⚠️  crawl4ai-setup failed, trying fallback method..."
            # Fallback: install Playwright browsers directly
            # From docs: python -m playwright install --with-deps chromium
            python -m playwright install --with-deps chromium || echo "Warning: Playwright browser installation failed"
        fi
    else
        # Fallback: try running via python module or direct playwright install
        echo "crawl4ai-setup command not found, trying direct Playwright installation..."
        python -m playwright install --with-deps chromium || echo "Warning: Playwright browser installation failed"
    fi
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
            if crawl4ai-setup; then
                echo "✓ Crawl4AI setup completed successfully"
            else
                echo "⚠️  crawl4ai-setup failed, trying fallback method..."
                # Fallback: install Playwright browsers directly
                python -m playwright install --with-deps chromium || echo "Warning: Playwright browser installation failed"
            fi
        else
            # Fallback: try direct Playwright installation
            echo "crawl4ai-setup command not found, trying direct Playwright installation..."
            python -m playwright install --with-deps chromium || echo "Warning: Playwright browser installation failed"
        fi
    else
        echo "✓ Playwright browsers already installed"
    fi
fi

# Ensure PATH includes venv
export PATH="/opt/venv/bin:$PATH"

# Run the application with explicit PATH
# This ensures uvicorn and other commands are found
exec env PATH="/opt/venv/bin:$PATH" "$@"

