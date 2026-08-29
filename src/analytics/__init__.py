"""Analytics helpers for Smart Spend AI."""

# Import the persistence adapter at application package startup so every
# SQLAlchemy Transaction write goes through the V2 intelligence decision layer.
from src.intelligence.persistence import install as install_transaction_intelligence

install_transaction_intelligence()
