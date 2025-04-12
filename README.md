# BloxHub Discord Bot

A Discord bot designed to streamline Roblox user verification, gamepass tracking, and role assignment with enhanced security and user experience features.

## Key Features

- **Discord Integration**: Seamlessly integrates with Discord servers via slash commands
- **Roblox User Verification**: Secure verification process to link Discord and Roblox accounts
- **Gamepass Purchase Tracking**: Automatically tracks and validates Roblox gamepass purchases
- **Automated Role Management**: Assigns roles based on verification status and purchases
- **Secure Verification Process**: Uses profile code validation to ensure account ownership
- **Private Channel Management**: Controls access to Discord channels based on gamepass ownership

## Commands

- `/verify [username]` - Link your Discord account to your Roblox profile
- `/confirm [username]` - Confirm your verification with your Roblox username
- `/reverify` - Re-link your Discord account to a different Roblox profile
- `/buy [product]` - Purchase a product with a gamepass
- `/redeem [gamepass] [product]` - Redeem a gamepass you already own
- `/add [name] [gamepass] [description] [botinvite]` - Add a new product (Admin only)
- `/setprivatechannels [channel] [gamepass]` - Set a channel as private with access via gamepass link (Admin only)

## Installation

1. Clone this repository
2. Install dependencies with `pip install -r requirements.txt`
3. Set up the required environment variables (see below)
4. Run with `python app.py`

## Environment Variables

Create a `.env` file with the following variables:

```
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_GUILD_ID=your_discord_guild_id
DATABASE_URL=your_database_url
```

## Deployment

This application is designed to be deployed on render.com. Use the provided `requirements-render.txt` and `Procfile` for deployment.