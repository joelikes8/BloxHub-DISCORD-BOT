import os
import sys
import time
import asyncio
import logging
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
import threading

# Import bot modules
from bot.discord_bot import initialize_bot
from bot.storage import storage
from bot.roblox_api import (
    get_user_by_username,
    get_user_by_id,
    get_gamepass_info,
    is_inventory_public,
    user_owns_gamepass,
    check_profile_for_code,
    extract_gamepass_id
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

# Initialize Flask app
app = Flask(__name__, static_folder='client/dist')

# Log startup information
logger.info("Starting BloxHub Discord Bot application")
logger.info(f"DISCORD_BOT_TOKEN present: {bool(os.environ.get('DISCORD_BOT_TOKEN'))}")
logger.info(f"DATABASE_URL present: {bool(os.environ.get('DATABASE_URL'))}")

# Initialize Discord bot in a separate thread
async def start_bot():
    """
    Start the Discord bot and ensure it's properly logged in
    """
    try:
        logger = logging.getLogger('discord-bot')
        logger.info("Starting Discord bot...")
        # Create and start bot thread
        bot_future = asyncio.ensure_future(initialize_bot())
        return bot_future
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return None

# Watchdog function to monitor bot health
def create_bot_watchdog():
    """
    Creates a watchdog timer to check if the bot is running properly
    and restart it if necessary.
    """
    def check_bot_health():
        """Watchdog function that checks bot health every minute"""
        global bot_thread, loop
        
        while True:
            # Sleep for a minute
            time.sleep(60)
            
            # Check if bot thread is alive
            if not bot_thread.is_alive():
                logger.critical("Bot thread is not alive! Restarting bot...")
                # Create a new thread
                start_bot_with_watchdog()
            else:
                logger.debug("Bot watchdog: Bot thread is alive")

    # Create and start watchdog thread
    watchdog_thread = threading.Thread(target=check_bot_health)
    watchdog_thread.daemon = True
    watchdog_thread.start()
    logger.info("Bot watchdog started")

# Function to start the bot with all necessary setup
def start_bot_with_watchdog():
    """Start the bot with watchdog monitoring"""
    global bot_thread, loop
    
    if not os.environ.get('DISCORD_BOT_TOKEN'):
        logger.warning("DISCORD_BOT_TOKEN not set. Bot will not start.")
        return
        
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start the bot
    bot_future = loop.run_until_complete(start_bot())
    
    # Define the loop runner
    def run_bot_loop():
        try:
            loop.run_forever()
        except Exception as e:
            logger.error(f"Bot loop error: {e}")
            # Don't close the loop here as we want the watchdog to restart
        
    # Create and start the bot thread
    bot_thread = threading.Thread(target=run_bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("Discord bot started in background thread")

# Set up global variables
bot_thread = None
loop = None

# Start the bot if TOKEN is set
if os.environ.get('DISCORD_BOT_TOKEN'):
    # Start the bot
    start_bot_with_watchdog()
    
    # Start the watchdog after a delay to ensure bot had time to connect
    threading.Timer(10, create_bot_watchdog).start()
else:
    print("WARNING: DISCORD_BOT_TOKEN not set. Bot will not start.")

# API routes
@app.route('/api/products', methods=['GET'])
def get_products():
    products = storage.get_all_products()
    return jsonify(products)

@app.route('/api/commands/verify', methods=['POST'])
def verify_command():
    data = request.json
    from bot.discord_bot import handle_verify
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    result = handle_verify(user)
    return jsonify(result)

@app.route('/api/commands/confirm-verification', methods=['POST'])
def confirm_verification_command():
    data = request.json
    from bot.discord_bot import confirm_verification
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    roblox_username = data.get('robloxUsername')
    
    result = confirm_verification(user, roblox_username)
    return jsonify(result)

@app.route('/api/commands/reverify', methods=['POST'])
def reverify_command():
    data = request.json
    from bot.discord_bot import handle_reverify
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    result = handle_reverify(user)
    return jsonify(result)

@app.route('/api/commands/buy', methods=['POST'])
def buy_command():
    data = request.json
    from bot.discord_bot import handle_buy
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    product_name = data.get('productName')
    
    result = handle_buy(user, product_name)
    return jsonify(result)

@app.route('/api/commands/redeem', methods=['POST'])
def redeem_command():
    data = request.json
    from bot.discord_bot import handle_redeem
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    gamepass_link = data.get('gamepassLink')
    product_name = data.get('productName', '')
    
    result = handle_redeem(user, product_name, gamepass_link)
    return jsonify(result)

@app.route('/api/commands/add', methods=['POST'])
def add_command():
    data = request.json
    from bot.discord_bot import handle_add_product
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    product_name = data.get('productName')
    gamepass_link = data.get('gamepassLink')
    description = data.get('description')
    bot_invite_link = data.get('botInviteLink')
    
    result = handle_add_product(user, product_name, gamepass_link, description, bot_invite_link)
    return jsonify(result)

@app.route('/api/commands/setprivatechannels', methods=['POST'])
def set_private_channels_command():
    data = request.json
    from bot.discord_bot import handle_set_private_channels
    
    user = {
        'id': data.get('discordId'),
        'username': data.get('username'),
        'tag': data.get('tag', '')
    }
    
    channel = {
        'id': data.get('channelId'),
        'name': data.get('channelName')
    }
    
    gamepass_link = data.get('gamepassLink')
    
    result = handle_set_private_channels(user, channel, gamepass_link)
    return jsonify(result)

@app.route('/api/verification/<discord_id>', methods=['GET'])
def get_verification(discord_id):
    verification = storage.get_verified_user_by_discord_id(discord_id)
    if verification:
        return jsonify(verification)
    return jsonify({"error": "User not found"}), 404

@app.route('/api/purchases/<discord_id>', methods=['GET'])
def get_purchases(discord_id):
    purchases = storage.get_purchases_by_discord_id(discord_id)
    return jsonify(purchases)

@app.route('/api/commands/adduser', methods=['POST'])
def add_user_command():
    data = request.json
    # Import the function here to avoid circular imports
    from bot.discord_bot import has_access
    
    admin_user = {
        'id': data.get('adminId'),
        'username': data.get('adminUsername'),
        'tag': data.get('adminTag', '')
    }
    
    discord_user_id = data.get('discordUserId')
    bot_id = data.get('botId')
    
    # Check if admin user has permission (simplified check for API)
    is_admin = True  # Assume the caller is admin for API calls
    
    # Grant access
    try:
        if not is_admin:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to use this command.'
            }), 403
        
        access_data = {
            'botId': bot_id,
            'userId': discord_user_id,
            'grantedBy': admin_user['id']
        }
        
        access = storage.grant_bot_access(access_data)
        
        return jsonify({
            'success': True,
            'message': f'User {discord_user_id} now has access to bot {bot_id}.',
            'data': access
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error granting bot access: {str(e)}'
        }), 500

@app.route('/api/bot-access/check', methods=['POST'])
def check_bot_access():
    data = request.json
    from bot.discord_bot import has_access
    
    user_id = data.get('userId')
    bot_id = data.get('botId')
    is_admin = data.get('isAdmin', False)
    
    if not user_id or not bot_id:
        return jsonify({
            'success': False,
            'message': 'Missing required parameters: userId and botId.'
        }), 400
    
    has_bot_access = has_access(user_id, bot_id, is_admin)
    
    return jsonify({
        'success': True,
        'hasAccess': has_bot_access
    })

@app.route('/api/bot-access/users/<bot_id>', methods=['GET'])
def get_bot_users(bot_id):
    users = storage.get_bot_users(bot_id)
    return jsonify(users)

@app.route('/api/bot-access/bots/<user_id>', methods=['GET'])
def get_user_bots(user_id):
    bots = storage.get_user_bots(user_id)
    return jsonify(bots)

# Serve static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)