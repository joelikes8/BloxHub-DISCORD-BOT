import os
import logging
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import datetime
from typing import Dict, Any, List, Optional, Union

# Local imports
from .storage import storage
from .roblox_api import (
    get_user_by_username,
    get_user_by_id,
    get_gamepass_info,
    is_inventory_public,
    user_owns_gamepass,
    check_profile_for_code,
    extract_gamepass_id
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord-bot')

# Get environment variables
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '')
GUILD_ID = os.getenv('DISCORD_GUILD_ID', '')
BUYER_ROLE_NAME = 'Bot Buyer 💵'

# Bot client
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# Command result type
class CommandResult:
    def __init__(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}
    
    def to_dict(self):
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data
        }

# Discord user type
class DiscordUser:
    def __init__(self, id: str, username: str, tag: str = ''):
        self.id = id
        self.username = username
        self.tag = tag

# Discord channel type
class DiscordChannel:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

# Initialize bot
async def initialize_bot():
    logger.info("Initializing Discord bot...")
    
    @bot.event
    async def on_ready():
        logger.info(f'Logged in as {bot.user}!')
        await register_commands()
        check_pending_purchases.start()
        
    await bot.start(DISCORD_BOT_TOKEN)

# Register slash commands
async def register_commands():
    try:
        # Define commands using discord.py's newer approach
        @bot.tree.command(name="verify", description="Link your Discord account to your Roblox profile")
        async def verify(interaction: discord.Interaction, username: str):
            await handle_verify_command(interaction, username)
        
        @bot.tree.command(name="confirm", description="Confirm your verification with your Roblox username")
        async def confirm(interaction: discord.Interaction, username: str):
            await handle_confirm_verify_command(interaction, username)
        
        @bot.tree.command(name="reverify", description="Re-link your Discord account to a different Roblox profile")
        async def reverify(interaction: discord.Interaction):
            await handle_reverify_command(interaction)
        
        @bot.tree.command(name="buy", description="Purchase a product with a gamepass")
        async def buy(interaction: discord.Interaction, product: str):
            await handle_buy_command(interaction, product)
        
        @bot.tree.command(name="redeem", description="Redeem a gamepass you already own")
        async def redeem(interaction: discord.Interaction, gamepass: str, product: str = None):
            await handle_redeem_command(interaction, gamepass, product)
        
        @bot.tree.command(name="add", description="Add a new product (Admin only)")
        @app_commands.default_permissions(administrator=True)
        async def add(interaction: discord.Interaction, name: str, gamepass: str, description: str = None, botinvite: str = None):
            await handle_add_command(interaction, name, gamepass, description, botinvite)
        
        @bot.tree.command(name="setprivatechannels", description="Set a channel as private with access via gamepass link (Admin only)")
        @app_commands.default_permissions(administrator=True)
        async def setprivatechannels(interaction: discord.Interaction, channel: discord.TextChannel, gamepass: str):
            await handle_set_private_channels_command(interaction, channel, gamepass)
        
        # Sync commands
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        
        logger.info('Successfully registered application commands')
    except Exception as e:
        logger.error(f'Error registering commands: {e}')
        logger.error("This usually happens when the bot doesn't have permission to create slash commands.")
        logger.error('Please ensure the bot has the "applications.commands" scope when added to the server.')
        logger.error('You may need to re-invite the bot with the proper permissions.')

# Command handlers
async def handle_verify_command(interaction: discord.Interaction, username: str):
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    # Get verification code
    result = handle_verify(user)
    
    if result.success:
        # Create verify button
        verify_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Verify",
            custom_id=f"verify_{user.id}_{username}"
        )
        
        # Create action row with button
        view = discord.ui.View()
        view.add_item(verify_button)
        
        # Create embed
        embed = discord.Embed(
            title="Verification Code",
            description=result.message,
            color=discord.Color.blue()
        )
        embed.add_field(name="Code", value=f"`{result.data['code']}`")
        embed.set_footer(text="Copy this code to your Roblox profile, then click the Verify button below")
        
        await interaction.response.send_message(embeds=[embed], view=view, ephemeral=True)
    else:
        await interaction.response.send_message(content=result.message, ephemeral=True)

async def handle_confirm_verify_command(interaction: discord.Interaction, username: str):
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    await interaction.response.defer(ephemeral=True)
    
    # Confirm verification
    result = confirm_verification(user, username)
    
    if result.success:
        embed = discord.Embed(
            title="Verification Successful",
            description=result.message,
            color=discord.Color.green()
        )
        embed.add_field(name="Roblox Username", value=result.data['robloxUsername'])
        
        await interaction.followup.send(embeds=[embed], ephemeral=True)
    else:
        await interaction.followup.send(content=result.message, ephemeral=True)

async def handle_reverify_command(interaction: discord.Interaction):
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    # Ask for the username interactively
    await interaction.response.send_message(
        content="Please enter your Roblox username to reverify:",
        ephemeral=True
    )
    
    # We can't directly collect messages in slash commands.
    # Instead, instruct the user to use /confirm command
    await asyncio.sleep(2)
    await interaction.followup.send(
        content="To continue the reverification process, use the `/confirm username:YourRobloxUsername` command.",
        ephemeral=True
    )

async def handle_buy_command(interaction: discord.Interaction, product: str):
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    await interaction.response.defer(ephemeral=True)
    
    # Process purchase
    result = handle_buy(user, product)
    
    if result.success:
        embed = discord.Embed(
            title=f"Purchase: {result.data['product']['name']}",
            description=result.message,
            color=discord.Color.green()
        )
        embed.add_field(name="Price", value=f"R$ {result.data['product']['price']}")
        embed.add_field(name="Purchase Link", value=result.data.get('gamepassLink', 'Already owned'))
        
        await interaction.followup.send(embeds=[embed], ephemeral=True)
    else:
        await interaction.followup.send(content=result.message, ephemeral=True)

async def handle_redeem_command(interaction: discord.Interaction, gamepass: str, product: Optional[str] = None):
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    await interaction.response.defer(ephemeral=True)
    
    # Process redemption
    result = handle_redeem(user, product or '', gamepass)
    
    if result.success:
        embed = discord.Embed(
            title=f"Redeemed: {result.data['product']['name']}",
            description=result.message,
            color=discord.Color.green()
        )
        embed.add_field(name="Price", value=f"R$ {result.data['product']['price']}")
        embed.add_field(name="Gamepass ID", value=result.data['product']['gamepassId'])
        
        await interaction.followup.send(embeds=[embed], ephemeral=True)
    else:
        await interaction.followup.send(content=result.message, ephemeral=True)

async def handle_add_command(interaction: discord.Interaction, name: str, gamepass: str, description: Optional[str] = None, botinvite: Optional[str] = None):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            content="You do not have permission to use this command.",
            ephemeral=True
        )
        return
    
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    await interaction.response.defer(ephemeral=True)
    
    # Add product
    result = handle_add_product(user, name, gamepass, description, botinvite)
    
    if result.success:
        embed = discord.Embed(
            title=f"Added Product: {result.data['product']['name']}",
            description=result.message,
            color=discord.Color.green()
        )
        embed.add_field(name="Description", value=result.data['product']['description'])
        embed.add_field(name="Price", value=f"R$ {result.data['product']['price']}")
        embed.add_field(name="Gamepass ID", value=result.data['product']['gamepassId'])
        
        if result.data['product'].get('botInviteLink'):
            embed.add_field(name="Bot Invite Link", value=result.data['product']['botInviteLink'])
        
        await interaction.followup.send(embeds=[embed], ephemeral=True)
    else:
        await interaction.followup.send(content=result.message, ephemeral=True)

async def handle_set_private_channels_command(interaction: discord.Interaction, channel: discord.TextChannel, gamepass: str):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            content="You do not have permission to use this command.",
            ephemeral=True
        )
        return
    
    user = DiscordUser(
        id=str(interaction.user.id),
        username=interaction.user.name,
        tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
    )
    
    discord_channel = DiscordChannel(
        id=str(channel.id),
        name=channel.name
    )
    
    await interaction.response.defer(ephemeral=True)
    
    # Set up private channel
    result = handle_set_private_channels(user, discord_channel, gamepass)
    
    if result.success:
        embed = discord.Embed(
            title="Private Channel Setup",
            description=result.message,
            color=discord.Color.green()
        )
        embed.add_field(name="Channel", value=f"<#{channel.id}>")
        embed.add_field(name="Gamepass Link", value=gamepass)
        
        await interaction.followup.send(embeds=[embed], ephemeral=True)
    else:
        await interaction.followup.send(content=result.message, ephemeral=True)

# Button interactions handler
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        # Handle button clicks
        if interaction.data.get('custom_id', '').startswith('verify_'):
            custom_id = interaction.data['custom_id']
            _, discord_id, roblox_username = custom_id.split('_')
            
            user = DiscordUser(
                id=discord_id,
                username=interaction.user.name,
                tag=f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != '0' else interaction.user.name
            )
            
            await interaction.response.defer(ephemeral=True)
            
            # Confirm verification
            result = confirm_verification(user, roblox_username)
            
            if result.success:
                embed = discord.Embed(
                    title="Verification Successful",
                    description=result.message,
                    color=discord.Color.green()
                )
                embed.add_field(name="Roblox Username", value=result.data['robloxUsername'])
                
                await interaction.followup.send(embeds=[embed], ephemeral=True)
            else:
                await interaction.followup.send(content=result.message, ephemeral=True)

# Check pending purchases task
@tasks.loop(seconds=30)
async def check_pending_purchases():
    try:
        pending_purchases = storage.get_pending_purchases()
        
        if not pending_purchases:
            return
        
        logger.info(f"Checking {len(pending_purchases)} pending purchases...")
        
        for purchase in pending_purchases:
            product = storage.get_product(purchase['productId'])
            if not product:
                # Fix: No need to await synchronous method
                storage.update_purchase(purchase['id'], {'status': 'failed'})
                continue
            
            # Convert to async call with await
            owned = await asyncio.to_thread(user_owns_gamepass, purchase['robloxId'], product['gamepassId'])
            
            if owned:
                # Fix: No need to await synchronous method
                storage.update_purchase(
                    purchase['id'], 
                    {
                        'status': 'completed',
                        'purchasedAt': datetime.datetime.now()
                    }
                )
                
                logger.info(f"Purchase {purchase['id']} completed for user {purchase['discordId']}")
                
                # Assign the Bot Buyer role
                try:
                    guild = bot.get_guild(int(GUILD_ID))
                    if guild:
                        buyer_role = discord.utils.get(guild.roles, name=BUYER_ROLE_NAME)
                        
                        if buyer_role:
                            member = await guild.fetch_member(int(purchase['discordId']))
                            if member:
                                await member.add_roles(buyer_role)
                                logger.info(f"Successfully added {BUYER_ROLE_NAME} role to Discord user {purchase['discordId']}")
                                
                                # Send invite link if available
                                if product.get('botInviteLink'):
                                    try:
                                        embed = discord.Embed(
                                            title=f"🎉 Thank you for purchasing {product['name']}!",
                                            description=f"Here's your bot invite link:\n{product['botInviteLink']}",
                                            color=discord.Color.green()
                                        )
                                        
                                        await member.send(embed=embed)
                                        logger.info(f"Successfully sent invite link to user {purchase['discordId']}")
                                    except Exception as dm_error:
                                        logger.error(f"Error sending bot invite link to user {purchase['discordId']}: {dm_error}")
                            else:
                                logger.error(f"Could not find member {purchase['discordId']} in guild")
                        else:
                            logger.error(f"Could not find role '{BUYER_ROLE_NAME}' in guild, please create this role manually")
                    else:
                        logger.error(f"Could not find guild with ID {GUILD_ID}")
                except Exception as role_error:
                    logger.error(f"Error giving role to user: {role_error}")
    except Exception as e:
        logger.error(f"Error checking purchases: {e}")

# Command handlers for API integration
def handle_verify(user: Union[DiscordUser, Dict[str, str]]) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    try:
        # Check if user is already verified
        existing_verification = storage.get_verified_user_by_discord_id(user.id)
        
        if existing_verification and existing_verification.get('verified'):
            return CommandResult(
                success=False,
                message='You are already verified. Use /reverify if you want to verify with a different account.'
            )
        
        # Generate verification code
        verification_code = generate_verification_code()
        
        if existing_verification:
            # Update existing verification
            storage.update_verified_user(
                existing_verification['id'],
                {
                    'verificationCode': verification_code,
                    'verified': False,
                    'verifiedAt': None
                }
            )
        else:
            # Create new verification
            storage.create_verified_user({
                'discordId': user.id,
                'robloxUsername': '',
                'robloxId': '',
                'verificationCode': verification_code,
                'verified': False
            })
        
        return CommandResult(
            success=True,
            message='Please add this code to your Roblox profile "About Me" section and then confirm verification. Note: Make sure your Roblox inventory is set to public for verification to work properly.',
            data={'code': verification_code}
        )
    except Exception as e:
        logger.error(f"Error in verify command: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while generating your verification code. Please try again later.'
        )

def confirm_verification(user: Union[DiscordUser, Dict[str, str]], roblox_username: str) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    try:
        # Get verification record
        verification = storage.get_verified_user_by_discord_id(user.id)
        
        if not verification:
            return CommandResult(
                success=False,
                message='You have not started the verification process. Please use /verify first.'
            )
        
        # Get Roblox user info
        roblox_user = get_user_by_username(roblox_username)
        
        if not roblox_user:
            return CommandResult(
                success=False,
                message=f'Could not find a Roblox user with the username "{roblox_username}". Please check the spelling and try again.'
            )
        
        # Check if inventory is public
        inventory_is_public = is_inventory_public(roblox_user['id'])
        
        if not inventory_is_public:
            return CommandResult(
                success=False,
                message=f'Your Roblox inventory is currently private. Please make it public for verification and purchases to work properly. Once public, try verifying again.'
            )
        
        # Check for verification code in profile
        code_found = check_profile_for_code(roblox_user['id'], verification['verificationCode'])
        
        if not code_found:
            return CommandResult(
                success=False,
                message=f'Verification code not found in your Roblox profile. Please make sure you\'ve added the code "{verification["verificationCode"]}" to your About Me section and try again.'
            )
        
        # Update verification record
        storage.update_verified_user(
            verification['id'],
            {
                'robloxUsername': roblox_user['name'],
                'robloxId': str(roblox_user['id']),
                'verified': True,
                'verifiedAt': datetime.datetime.now()
            }
        )
        
        return CommandResult(
            success=True,
            message=f'Successfully verified! Your Discord account is now linked to Roblox user {roblox_user["name"]}.',
            data={
                'robloxUsername': roblox_user['name'],
                'robloxId': roblox_user['id']
            }
        )
    except Exception as e:
        logger.error(f"Error in confirm verification: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while confirming your verification. Please try again later.'
        )

def handle_reverify(user: Union[DiscordUser, Dict[str, str]]) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    try:
        verification = storage.get_verified_user_by_discord_id(user.id)
        
        if not verification:
            return handle_verify(user)
        
        # Generate new verification code
        verification_code = generate_verification_code()
        
        # Update existing verification
        storage.update_verified_user(
            verification['id'],
            {
                'verificationCode': verification_code,
                'verified': False,
                'verifiedAt': None,
                'robloxUsername': '',
                'robloxId': ''
            }
        )
        
        return CommandResult(
            success=True,
            message='Please add this code to your Roblox profile "About Me" section and then confirm verification. Note: Make sure your Roblox inventory is set to public for verification to work properly.',
            data={'code': verification_code}
        )
    except Exception as e:
        logger.error(f"Error in reverify command: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while generating your reverification code. Please try again later.'
        )

def handle_buy(user: Union[DiscordUser, Dict[str, str]], product_name: str) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    try:
        # Check if user is verified
        verification = storage.get_verified_user_by_discord_id(user.id)
        
        if not verification or not verification.get('verified'):
            return CommandResult(
                success=False,
                message='You need to verify your Roblox account first. Use /verify to get started.'
            )
        
        # Get product
        product = storage.get_product_by_name(product_name)
        
        if not product:
            return CommandResult(
                success=False,
                message=f'Product "{product_name}" not found. Please check the spelling or contact an administrator.'
            )
        
        # Check if user already owns the gamepass
        owned = user_owns_gamepass(verification['robloxId'], product['gamepassId'])
        
        if owned:
            # Create/update purchase record
            existing_purchase = storage.get_purchase_by_discord_id_and_product_id(user.id, product['id'])
            
            if existing_purchase:
                if existing_purchase.get('status') == 'completed':
                    return CommandResult(
                        success=True,
                        message=f'You already own this product. Enjoy!',
                        data={'product': product}
                    )
                else:
                    # Update existing purchase to completed
                    storage.update_purchase(
                        existing_purchase['id'],
                        {
                            'status': 'completed',
                            'purchasedAt': datetime.datetime.now()
                        }
                    )
            else:
                # Create new purchase record
                storage.create_purchase({
                    'discordId': user.id,
                    'robloxId': verification['robloxId'],
                    'productId': product['id'],
                    'status': 'completed',
                    'purchasedAt': datetime.datetime.now()
                })
            
            # Success response
            return CommandResult(
                success=True,
                message=f'You already own this gamepass. Your purchase has been processed successfully.',
                data={'product': product}
            )
        else:
            # Create pending purchase record
            existing_purchase = storage.get_purchase_by_discord_id_and_product_id(user.id, product['id'])
            
            if not existing_purchase:
                storage.create_purchase({
                    'discordId': user.id,
                    'robloxId': verification['robloxId'],
                    'productId': product['id'],
                    'status': 'pending'
                })
            elif existing_purchase.get('status') != 'completed':
                # Update existing purchase to pending if not completed
                storage.update_purchase(
                    existing_purchase['id'],
                    {'status': 'pending'}
                )
            
            # Construct gamepass link
            gamepass_link = f"https://www.roblox.com/game-pass/{product['gamepassId']}"
            
            # Return response with purchase link
            return CommandResult(
                success=True,
                message=f'Please click the purchase link below to buy the gamepass for {product["name"]}. Once purchased, your purchase will be automatically detected and processed.',
                data={
                    'product': product,
                    'gamepassLink': gamepass_link
                }
            )
    except Exception as e:
        logger.error(f"Error in buy command: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while processing your purchase. Please try again later.'
        )

def handle_redeem(user: Union[DiscordUser, Dict[str, str]], product_name: str, gamepass_link: str) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    try:
        # Check if user is verified
        verification = storage.get_verified_user_by_discord_id(user.id)
        
        if not verification or not verification.get('verified'):
            return CommandResult(
                success=False,
                message='You need to verify your Roblox account first. Use /verify to get started.'
            )
        
        # Extract gamepass ID from link
        gamepass_id = extract_gamepass_id(gamepass_link)
        
        if not gamepass_id:
            return CommandResult(
                success=False,
                message='Invalid gamepass link. Please provide a valid Roblox gamepass link.'
            )
        
        # Get the product by gamepass ID or name
        product = None
        
        if product_name:
            product = storage.get_product_by_name(product_name)
            
            if not product:
                return CommandResult(
                    success=False,
                    message=f'Product "{product_name}" not found. Please check the spelling or contact an administrator.'
                )
            
            # Verify that the provided gamepass matches the product
            if product['gamepassId'] != gamepass_id:
                return CommandResult(
                    success=False,
                    message=f'The provided gamepass link does not match the gamepass for product "{product_name}".'
                )
        else:
            # Try to find product by gamepass ID
            product = storage.get_product_by_gamepass_id(gamepass_id)
            
            if not product:
                return CommandResult(
                    success=False,
                    message=f'No product found for this gamepass. Please contact an administrator.'
                )
        
        # Check if user owns the gamepass
        owned = user_owns_gamepass(verification['robloxId'], gamepass_id)
        
        if not owned:
            return CommandResult(
                success=False,
                message=f'You do not own this gamepass. Please purchase it before attempting to redeem.'
            )
        
        # Check if user already has a completed purchase
        existing_purchase = storage.get_purchase_by_discord_id_and_product_id(user.id, product['id'])
        
        if existing_purchase and existing_purchase.get('status') == 'completed':
            return CommandResult(
                success=True,
                message=f'You have already redeemed this product. Enjoy!',
                data={'product': product}
            )
        
        # Create or update purchase record
        if existing_purchase:
            storage.update_purchase(
                existing_purchase['id'],
                {
                    'status': 'completed',
                    'purchasedAt': datetime.datetime.now()
                }
            )
        else:
            storage.create_purchase({
                'discordId': user.id,
                'robloxId': verification['robloxId'],
                'productId': product['id'],
                'status': 'completed',
                'purchasedAt': datetime.datetime.now()
            })
        
        # Success response
        return CommandResult(
            success=True,
            message=f'Successfully redeemed {product["name"]}! Thank you for your purchase.',
            data={'product': product}
        )
    except Exception as e:
        logger.error(f"Error in redeem command: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while processing your redemption. Please try again later.'
        )

def handle_add_product(
    user: Union[DiscordUser, Dict[str, str]], 
    product_name: str, 
    gamepass_link: str, 
    description: Optional[str] = None, 
    bot_invite_link: Optional[str] = None
) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    try:
        # Extract gamepass ID
        gamepass_id = extract_gamepass_id(gamepass_link)
        
        if not gamepass_id:
            return CommandResult(
                success=False,
                message='Invalid gamepass link. Please provide a valid Roblox gamepass link.'
            )
        
        # Check if product with this name already exists
        existing_product = storage.get_product_by_name(product_name)
        
        if existing_product:
            return CommandResult(
                success=False,
                message=f'A product with the name "{product_name}" already exists. Please choose a different name.'
            )
        
        # Check if product with this gamepass ID already exists
        existing_product_by_gamepass = storage.get_product_by_gamepass_id(gamepass_id)
        
        if existing_product_by_gamepass:
            return CommandResult(
                success=False,
                message=f'A product for this gamepass already exists with name "{existing_product_by_gamepass["name"]}".'
            )
        
        # Get gamepass info from Roblox
        gamepass_info = get_gamepass_info(gamepass_id)
        
        if not gamepass_info:
            return CommandResult(
                success=False,
                message='Could not retrieve information for this gamepass. Please check the link and try again.'
            )
        
        # Create product
        product = storage.create_product({
            'name': product_name,
            'description': description or f'Gamepass for {product_name}',
            'price': gamepass_info['price'],
            'gamepassId': gamepass_id,
            'botInviteLink': bot_invite_link or '',
            'createdAt': datetime.datetime.now()
        })
        
        # Success response
        return CommandResult(
            success=True,
            message=f'Successfully added product {product_name}.',
            data={'product': product}
        )
    except Exception as e:
        logger.error(f"Error in add product command: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while adding the product. Please try again later.'
        )

def handle_set_private_channels(
    user: Union[DiscordUser, Dict[str, str]], 
    channel: Union[DiscordChannel, Dict[str, str]], 
    gamepass_link: str
) -> CommandResult:
    if isinstance(user, dict):
        user = DiscordUser(id=user['id'], username=user['username'], tag=user.get('tag', ''))
    
    if isinstance(channel, dict):
        channel = DiscordChannel(id=channel['id'], name=channel['name'])
    
    try:
        # Extract gamepass ID
        gamepass_id = extract_gamepass_id(gamepass_link)
        
        if not gamepass_id:
            return CommandResult(
                success=False,
                message='Invalid gamepass link. Please provide a valid Roblox gamepass link.'
            )
        
        # Check if this channel is already private
        existing_channel = storage.get_private_channel_by_channel_id(channel.id)
        
        if existing_channel:
            # Update existing private channel
            storage.update_private_channel(
                existing_channel['id'],
                {'gamepassId': gamepass_id}
            )
            
            return CommandResult(
                success=True,
                message=f'Updated private channel settings for <#{channel.id}>.',
                data={'channel': channel, 'gamepassId': gamepass_id}
            )
        
        # Create new private channel entry
        private_channel = storage.create_private_channel({
            'channelId': channel.id,
            'channelName': channel.name,
            'gamepassId': gamepass_id
        })
        
        # Success response
        return CommandResult(
            success=True,
            message=f'Successfully set up <#{channel.id}> as a private channel.',
            data={'channel': channel, 'gamepassId': gamepass_id}
        )
    except Exception as e:
        logger.error(f"Error in set private channels command: {e}")
        return CommandResult(
            success=False,
            message='An error occurred while setting up the private channel. Please try again later.'
        )

# Helper function to generate verification code
def generate_verification_code() -> str:
    prefix = 'DISC-VFY-'
    characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    code = ''.join(random.choice(characters) for _ in range(4))
    return prefix + code