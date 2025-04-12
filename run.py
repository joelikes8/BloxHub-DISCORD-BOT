#!/usr/bin/env python3
"""
BloxHub Discord Bot Runner

This script starts the main application, which includes:
1. The Flask web server
2. The Discord bot
"""

import os
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)