import os
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

# Initialize Flask app
app = Flask(__name__, static_folder='client/dist')

# Initialize Discord bot in a separate thread
bot_thread = threading.Thread(target=initialize_bot)
bot_thread.daemon = True
bot_thread.start()

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