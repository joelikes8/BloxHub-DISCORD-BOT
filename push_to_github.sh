#!/bin/bash
set -e  # Exit on error

# Use the GitHub token securely
git push -u "https://${GITHUB_TOKEN}@github.com/joelikes8/BloxHub-DISCORD-BOT.git" main

echo "Success! The Python version of BloxHub Discord Bot has been pushed to GitHub."
