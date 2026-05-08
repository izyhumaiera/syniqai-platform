"""
Connector Package
=================
Database and data source connectors for SYINIQ data lakehouse.

Available Connectors:
- PostgresConnector: PostgreSQL database connector
- MariaDBConnector: MariaDB database connector  
- MongoDBConnector: MongoDB database connector
- S3Connector: AWS S3 file connector
"""

from .base_connector import BaseConnector
from .postgres_connector import PostgresConnector

__all__ = [
    'BaseConnector',
    'PostgresConnector',
]
