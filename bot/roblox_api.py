import requests
import logging
import re
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('roblox-api')

# Roblox API endpoints
USERS_ENDPOINT = "https://users.roblox.com/v1/users/{}"
USERNAME_ENDPOINT = "https://users.roblox.com/v1/users/search?keyword={}&limit=10"
INVENTORY_ENDPOINT = "https://inventory.roblox.com/v1/users/{}/assets/collectibles?limit=10"
AVATAR_ENDPOINT = "https://avatar.roblox.com/v1/users/{}/avatar"
GAMEPASS_OWNERSHIP_ENDPOINT = "https://inventory.roblox.com/v1/users/{}/items/GamePass/{}"
GAMEPASS_INFO_ENDPOINT = "https://apis.roblox.com/marketplace-items/v1/items/details"
GAMEPASS_INVENTORY_ENDPOINT = "https://inventory.roblox.com/v1/users/{}/items/gamepass?sortOrder=Asc&limit=100"
CATALOG_SEARCH_ENDPOINT = "https://catalog.roblox.com/v1/search/items"

# Function to extract gamepass ID from link
def extract_gamepass_id(gamepass_url: str) -> Optional[str]:
    if not gamepass_url:
        return None
    
    # Pattern for gamepass URLs
    patterns = [
        r'roblox\.com/game-pass/(\d+)',
        r'roblox\.com/game-pass/.*[?&]id=(\d+)',
        r'roblox\.com/catalog/(\d+)',
        r'roblox\.com/catalog/.*[?&]id=(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, gamepass_url)
        if match:
            return match.group(1)
    
    # If no pattern matches, check if the input is just a numeric ID
    if gamepass_url.isdigit():
        return gamepass_url
    
    return None

# Get a Roblox user by username
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(USERNAME_ENDPOINT.format(username))
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                for user in data['data']:
                    if user['name'].lower() == username.lower():
                        return {
                            'id': user['id'],
                            'name': user['name'],
                            'displayName': user.get('displayName', user['name'])
                        }
                
                # If exact match not found, return first result
                user = data['data'][0]
                return {
                    'id': user['id'],
                    'name': user['name'],
                    'displayName': user.get('displayName', user['name'])
                }
        
        logger.warning(f"Could not find user with username: {username}")
        return None
    except Exception as e:
        logger.error(f"Error getting Roblox user by username: {e}")
        return None

# Get a Roblox user by ID
def get_user_by_id(user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(USERS_ENDPOINT.format(user_id))
        
        if response.status_code == 200:
            data = response.json()
            return {
                'id': data['id'],
                'name': data['name'],
                'displayName': data.get('displayName', data['name'])
            }
        
        logger.warning(f"Could not find user with ID: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting Roblox user by ID: {e}")
        return None

# Get gamepass information
def get_gamepass_info(gamepass_id: Union[str, int]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            GAMEPASS_INFO_ENDPOINT,
            params={
                'itemIds': gamepass_id,
                'itemType': 'GamePass'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data and len(data) > 0:
                gamepass = data[0]
                return {
                    'id': gamepass_id,
                    'name': gamepass.get('name', 'Unknown Gamepass'),
                    'price': gamepass.get('price', 0)
                }
        
        logger.warning(f"Could not find gamepass with ID: {gamepass_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting gamepass info: {e}")
        return None

# Check if a user's inventory is public
def is_inventory_public(user_id: Union[str, int]) -> bool:
    try:
        # Try to access inventory endpoint
        response = requests.get(INVENTORY_ENDPOINT.format(user_id))
        
        # Check if the response indicates a privacy error
        if response.status_code == 403:
            error_data = response.json()
            if 'errors' in error_data and len(error_data['errors']) > 0:
                error = error_data['errors'][0]
                if error.get('message', '').lower().find('inventory not available') != -1:
                    return False
        
        # Try the avatar endpoint as a fallback check
        avatar_response = requests.get(AVATAR_ENDPOINT.format(user_id))
        if avatar_response.status_code == 403:
            error_data = avatar_response.json()
            if 'errors' in error_data and len(error_data['errors']) > 0:
                error = error_data['errors'][0]
                if error.get('message', '').lower().find('not available') != -1:
                    return False
        
        # If we can access the gamepass inventory, it's definitely public
        gamepass_response = requests.get(GAMEPASS_INVENTORY_ENDPOINT.format(user_id))
        return gamepass_response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error checking if inventory is public: {e}")
        # In case of error, assume the inventory is private to be safe
        return False

# Check if a user owns a specific gamepass
def user_owns_gamepass(user_id: Union[str, int], gamepass_id: Union[str, int]) -> bool:
    try:
        # Check the specific gamepass ownership
        response = requests.get(GAMEPASS_OWNERSHIP_ENDPOINT.format(user_id, gamepass_id))
        
        if response.status_code == 200:
            data = response.json()
            # If the response has data, the user owns the gamepass
            return data.get('data', []) != []
        
        # If the inventory is private, we can't determine ownership
        if response.status_code == 403:
            logger.warning(f"Cannot check gamepass ownership for user {user_id} - inventory is private")
            return False
        
        # Also try the gamepass inventory endpoint
        gamepass_response = requests.get(GAMEPASS_INVENTORY_ENDPOINT.format(user_id))
        
        if gamepass_response.status_code == 200:
            data = gamepass_response.json()
            for item in data.get('data', []):
                if str(item.get('id')) == str(gamepass_id):
                    return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking if user owns gamepass: {e}")
        return False

# Check if a verification code is in a user's profile description
def check_profile_for_code(user_id: Union[str, int], code: str) -> bool:
    try:
        response = requests.get(USERS_ENDPOINT.format(user_id))
        
        if response.status_code == 200:
            data = response.json()
            description = data.get('description', '')
            
            # Check if the code is in the description
            return code in description
        
        return False
    except Exception as e:
        logger.error(f"Error checking profile for code: {e}")
        return False