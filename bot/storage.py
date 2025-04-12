import os
import logging
import datetime
import json
from typing import Dict, List, Any, Optional, Union
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('storage')

# Get database URL from environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bloxhub.db')

# Create database engine
engine = create_engine(DATABASE_URL)

# Create base model
Base = declarative_base()

# Define database models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

class VerifiedUser(Base):
    __tablename__ = 'verified_users'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(255), unique=True, nullable=False)
    roblox_username = Column(String(255), nullable=True)
    roblox_id = Column(String(255), nullable=True)
    verification_code = Column(String(255), nullable=False)
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    purchases = relationship("Purchase", back_populates="verified_user")
    
    def to_dict(self):
        return {
            'id': self.id,
            'discordId': self.discord_id,
            'robloxUsername': self.roblox_username,
            'robloxId': self.roblox_id,
            'verificationCode': self.verification_code,
            'verified': self.verified,
            'verifiedAt': self.verified_at.isoformat() if self.verified_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, default=0)
    gamepass_id = Column(String(255), unique=True, nullable=False)
    bot_invite_link = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    purchases = relationship("Purchase", back_populates="product")
    private_channels = relationship("PrivateChannel", back_populates="product")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'gamepassId': self.gamepass_id,
            'botInviteLink': self.bot_invite_link,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

class Purchase(Base):
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(255), nullable=False)
    roblox_id = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    status = Column(String(50), default='pending')  # pending, completed, failed
    purchased_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="purchases")
    verified_user = relationship("VerifiedUser", back_populates="purchases", 
                                foreign_keys=[discord_id], 
                                primaryjoin="Purchase.discord_id == VerifiedUser.discord_id",
                                viewonly=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'discordId': self.discord_id,
            'robloxId': self.roblox_id,
            'productId': self.product_id,
            'status': self.status,
            'purchasedAt': self.purchased_at.isoformat() if self.purchased_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

class PrivateChannel(Base):
    __tablename__ = 'private_channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(255), unique=True, nullable=False)
    channel_name = Column(String(255), nullable=False)
    gamepass_id = Column(String(255), ForeignKey('products.gamepass_id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="private_channels")
    
    def to_dict(self):
        return {
            'id': self.id,
            'channelId': self.channel_id,
            'channelName': self.channel_name,
            'gamepassId': self.gamepass_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

# Create database tables
Base.metadata.create_all(engine)

# Create session factory
SessionFactory = sessionmaker(bind=engine)

# Storage interface
class Storage:
    def __init__(self):
        self.session = SessionFactory()
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.session.is_active:
            self.session = SessionFactory()
        return self.session
    
    # User methods
    def get_user(self, id: int) -> Optional[Dict[str, Any]]:
        """Get a user by ID."""
        session = self.get_session()
        user = session.query(User).filter(User.id == id).first()
        return user.to_dict() if user else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a user by username."""
        session = self.get_session()
        user = session.query(User).filter(User.username == username).first()
        return user.to_dict() if user else None
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        session = self.get_session()
        user = User(
            username=user_data.get('username'),
            email=user_data.get('email')
        )
        session.add(user)
        session.commit()
        return user.to_dict()
    
    # Verified User methods
    def get_verified_user(self, id: int) -> Optional[Dict[str, Any]]:
        """Get a verified user by ID."""
        session = self.get_session()
        user = session.query(VerifiedUser).filter(VerifiedUser.id == id).first()
        return user.to_dict() if user else None
    
    def get_verified_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Get a verified user by Discord ID."""
        session = self.get_session()
        user = session.query(VerifiedUser).filter(VerifiedUser.discord_id == discord_id).first()
        return user.to_dict() if user else None
    
    def get_verified_user_by_roblox_id(self, roblox_id: str) -> Optional[Dict[str, Any]]:
        """Get a verified user by Roblox ID."""
        session = self.get_session()
        user = session.query(VerifiedUser).filter(VerifiedUser.roblox_id == roblox_id).first()
        return user.to_dict() if user else None
    
    def create_verified_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new verified user."""
        session = self.get_session()
        user = VerifiedUser(
            discord_id=user_data.get('discordId'),
            roblox_username=user_data.get('robloxUsername', ''),
            roblox_id=user_data.get('robloxId', ''),
            verification_code=user_data.get('verificationCode'),
            verified=user_data.get('verified', False),
            verified_at=user_data.get('verifiedAt')
        )
        session.add(user)
        session.commit()
        return user.to_dict()
    
    def update_verified_user(self, id: int, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a verified user."""
        session = self.get_session()
        user = session.query(VerifiedUser).filter(VerifiedUser.id == id).first()
        
        if not user:
            return None
        
        # Update fields
        if 'robloxUsername' in user_data:
            user.roblox_username = user_data['robloxUsername']
        if 'robloxId' in user_data:
            user.roblox_id = user_data['robloxId']
        if 'verificationCode' in user_data:
            user.verification_code = user_data['verificationCode']
        if 'verified' in user_data:
            user.verified = user_data['verified']
        if 'verifiedAt' in user_data:
            user.verified_at = user_data['verifiedAt']
        
        session.commit()
        return user.to_dict()
    
    # Product methods
    def get_product(self, id: int) -> Optional[Dict[str, Any]]:
        """Get a product by ID."""
        session = self.get_session()
        product = session.query(Product).filter(Product.id == id).first()
        return product.to_dict() if product else None
    
    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a product by name."""
        session = self.get_session()
        product = session.query(Product).filter(Product.name == name).first()
        return product.to_dict() if product else None
    
    def get_product_by_gamepass_id(self, gamepass_id: str) -> Optional[Dict[str, Any]]:
        """Get a product by gamepass ID."""
        session = self.get_session()
        product = session.query(Product).filter(Product.gamepass_id == gamepass_id).first()
        return product.to_dict() if product else None
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products."""
        session = self.get_session()
        products = session.query(Product).all()
        return [p.to_dict() for p in products]
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product."""
        session = self.get_session()
        product = Product(
            name=product_data.get('name'),
            description=product_data.get('description', ''),
            price=product_data.get('price', 0),
            gamepass_id=product_data.get('gamepassId'),
            bot_invite_link=product_data.get('botInviteLink', '')
        )
        session.add(product)
        session.commit()
        return product.to_dict()
    
    def update_product(self, id: int, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a product."""
        session = self.get_session()
        product = session.query(Product).filter(Product.id == id).first()
        
        if not product:
            return None
        
        # Update fields
        if 'name' in product_data:
            product.name = product_data['name']
        if 'description' in product_data:
            product.description = product_data['description']
        if 'price' in product_data:
            product.price = product_data['price']
        if 'gamepassId' in product_data:
            product.gamepass_id = product_data['gamepassId']
        if 'botInviteLink' in product_data:
            product.bot_invite_link = product_data['botInviteLink']
        
        session.commit()
        return product.to_dict()
    
    def delete_product(self, id: int) -> bool:
        """Delete a product."""
        session = self.get_session()
        product = session.query(Product).filter(Product.id == id).first()
        
        if not product:
            return False
        
        session.delete(product)
        session.commit()
        return True
    
    # Purchase methods
    def get_purchase(self, id: int) -> Optional[Dict[str, Any]]:
        """Get a purchase by ID."""
        session = self.get_session()
        purchase = session.query(Purchase).filter(Purchase.id == id).first()
        return purchase.to_dict() if purchase else None
    
    def get_purchases_by_discord_id(self, discord_id: str) -> List[Dict[str, Any]]:
        """Get purchases by Discord ID."""
        session = self.get_session()
        purchases = session.query(Purchase).filter(Purchase.discord_id == discord_id).all()
        return [p.to_dict() for p in purchases]
    
    def get_purchase_by_discord_id_and_product_id(self, discord_id: str, product_id: int) -> Optional[Dict[str, Any]]:
        """Get a purchase by Discord ID and product ID."""
        session = self.get_session()
        purchase = session.query(Purchase).filter(
            Purchase.discord_id == discord_id,
            Purchase.product_id == product_id
        ).first()
        return purchase.to_dict() if purchase else None
    
    def get_pending_purchases(self) -> List[Dict[str, Any]]:
        """Get all pending purchases."""
        session = self.get_session()
        purchases = session.query(Purchase).filter(Purchase.status == 'pending').all()
        return [p.to_dict() for p in purchases]
    
    def get_all_purchases(self) -> List[Dict[str, Any]]:
        """Get all purchases."""
        session = self.get_session()
        purchases = session.query(Purchase).all()
        return [p.to_dict() for p in purchases]
    
    def create_purchase(self, purchase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new purchase."""
        session = self.get_session()
        purchase = Purchase(
            discord_id=purchase_data.get('discordId'),
            roblox_id=purchase_data.get('robloxId'),
            product_id=purchase_data.get('productId'),
            status=purchase_data.get('status', 'pending'),
            purchased_at=purchase_data.get('purchasedAt')
        )
        session.add(purchase)
        session.commit()
        return purchase.to_dict()
    
    def update_purchase(self, id: int, purchase_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a purchase."""
        session = self.get_session()
        purchase = session.query(Purchase).filter(Purchase.id == id).first()
        
        if not purchase:
            return None
        
        # Update fields
        if 'status' in purchase_data:
            purchase.status = purchase_data['status']
        if 'purchasedAt' in purchase_data:
            purchase.purchased_at = purchase_data['purchasedAt']
        
        session.commit()
        return purchase.to_dict()
    
    # Private Channel methods
    def get_private_channel(self, id: int) -> Optional[Dict[str, Any]]:
        """Get a private channel by ID."""
        session = self.get_session()
        channel = session.query(PrivateChannel).filter(PrivateChannel.id == id).first()
        return channel.to_dict() if channel else None
    
    def get_private_channel_by_channel_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get a private channel by channel ID."""
        session = self.get_session()
        channel = session.query(PrivateChannel).filter(PrivateChannel.channel_id == channel_id).first()
        return channel.to_dict() if channel else None
    
    def get_all_private_channels(self) -> List[Dict[str, Any]]:
        """Get all private channels."""
        session = self.get_session()
        channels = session.query(PrivateChannel).all()
        return [c.to_dict() for c in channels]
    
    def create_private_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new private channel."""
        session = self.get_session()
        channel = PrivateChannel(
            channel_id=channel_data.get('channelId'),
            channel_name=channel_data.get('channelName'),
            gamepass_id=channel_data.get('gamepassId')
        )
        session.add(channel)
        session.commit()
        return channel.to_dict()
    
    def update_private_channel(self, id: int, channel_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a private channel."""
        session = self.get_session()
        channel = session.query(PrivateChannel).filter(PrivateChannel.id == id).first()
        
        if not channel:
            return None
        
        # Update fields
        if 'channelName' in channel_data:
            channel.channel_name = channel_data['channelName']
        if 'gamepassId' in channel_data:
            channel.gamepass_id = channel_data['gamepassId']
        
        session.commit()
        return channel.to_dict()
    
    def delete_private_channel(self, id: int) -> bool:
        """Delete a private channel."""
        session = self.get_session()
        channel = session.query(PrivateChannel).filter(PrivateChannel.id == id).first()
        
        if not channel:
            return False
        
        session.delete(channel)
        session.commit()
        return True

# Create a global storage instance
storage = Storage()