#!/usr/bin/env python3
"""
Database setup script for PostgreSQL + pgvector
Following DEVELOPMENT_RULES.md and DATABASE_ENGINEERING_SPEC.md
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
    def check_postgresql_running(self):
        """Check if PostgreSQL is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'postgresql'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip() == 'active':
                logger.info("✅ PostgreSQL service is running")
                return True
            else:
                logger.error("❌ PostgreSQL service is not active")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking PostgreSQL status: {e}")
            return False
    
    def check_pgvector_extension(self):
        """Check if pgvector extension is available"""
        try:
            # Check if pgvector is installed system-wide
            result = subprocess.run(
                ['find', '/usr', '-name', '*vector*', '-type', 'f'],
                capture_output=True,
                text=True
            )
            
            if 'vector' in result.stdout:
                logger.info("✅ pgvector extension files found")
                return True
            else:
                logger.warning("⚠️  pgvector extension not found - will install via SQL")
                return False
        except Exception as e:
            logger.warning(f"⚠️  Could not verify pgvector: {e}")
            return False
    
    def create_database_and_user(self):
        """Create database and user using SQL commands"""
        
        # SQL commands to execute
        setup_commands = [
            # Create database
            f"CREATE DATABASE hormozi_rag;",
            
            # Create user (if not exists)
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'rag_user') THEN CREATE USER rag_user WITH PASSWORD 'rag_password123'; END IF; END $$;",
            
            # Grant privileges
            f"GRANT ALL PRIVILEGES ON DATABASE hormozi_rag TO rag_user;",
            f"ALTER USER rag_user CREATEDB;",
        ]
        
        logger.info("🔧 Creating database and user...")
        
        for command in setup_commands:
            try:
                # Try different connection methods
                connection_methods = [
                    # Method 1: Direct connection as postgres user (peer authentication)
                    ['sudo', '-u', 'postgres', 'psql', '-c', command],
                    
                    # Method 2: Connection via socket
                    ['psql', 'postgres', '-c', command],
                ]
                
                success = False
                for method in connection_methods:
                    try:
                        result = subprocess.run(
                            method,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if result.returncode == 0:
                            logger.info(f"✅ Executed: {command[:50]}...")
                            success = True
                            break
                        else:
                            logger.debug(f"Method failed: {method[0]} - {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Timeout with method: {method[0]}")
                        continue
                    except Exception as e:
                        logger.debug(f"Exception with method {method[0]}: {e}")
                        continue
                
                if not success:
                    logger.error(f"❌ Failed to execute: {command}")
                    # Don't fail completely, continue with next command
                    
            except Exception as e:
                logger.error(f"❌ Error executing command: {e}")
                continue
    
    def test_connection(self):
        """Test database connection"""
        try:
            import psycopg2
            
            # Test connection parameters
            connection_params = {
                'host': 'localhost',
                'port': 5432,
                'database': 'hormozi_rag',
                'user': 'rag_user',
                'password': 'rag_password123'
            }
            
            logger.info("🔍 Testing database connection...")
            
            conn = psycopg2.connect(**connection_params)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"✅ Connected to: {version}")
            
            cursor.close()
            conn.close()
            
            # Update .env file with working credentials
            self.update_env_file(connection_params)
            return True
            
        except ImportError:
            logger.error("❌ psycopg2 not installed")
            return False
        except Exception as e:
            logger.warning(f"⚠️  Connection test failed: {e}")
            # Try alternative connection
            return self.try_alternative_connection()
    
    def try_alternative_connection(self):
        """Try alternative connection methods"""
        logger.info("🔄 Trying alternative connection methods...")
        
        # Alternative 1: Default postgres user
        alt_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        try:
            import psycopg2
            conn = psycopg2.connect(**alt_params)
            cursor = conn.cursor()
            cursor.execute("SELECT current_user;")
            user = cursor.fetchone()[0]
            logger.info(f"✅ Alternative connection successful as: {user}")
            
            cursor.close()
            conn.close()
            
            # Update .env with working credentials
            self.update_env_file(alt_params)
            return True
            
        except Exception as e:
            logger.error(f"❌ Alternative connection failed: {e}")
            return False
    
    def update_env_file(self, connection_params):
        """Update .env file with working connection parameters"""
        env_file = self.project_root / '.env'
        
        try:
            # Read current .env file
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update PostgreSQL configuration
            updated_lines = []
            for line in lines:
                if line.startswith('POSTGRES_HOST='):
                    updated_lines.append(f"POSTGRES_HOST={connection_params['host']}\n")
                elif line.startswith('POSTGRES_PORT='):
                    updated_lines.append(f"POSTGRES_PORT={connection_params['port']}\n")
                elif line.startswith('POSTGRES_DB='):
                    updated_lines.append(f"POSTGRES_DB={connection_params['database']}\n")
                elif line.startswith('POSTGRES_USER='):
                    updated_lines.append(f"POSTGRES_USER={connection_params['user']}\n")
                elif line.startswith('POSTGRES_PASSWORD='):
                    updated_lines.append(f"POSTGRES_PASSWORD={connection_params['password']}\n")
                else:
                    updated_lines.append(line)
            
            # Write updated .env file
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            logger.info(f"✅ Updated .env file with working credentials")
            
        except Exception as e:
            logger.error(f"❌ Failed to update .env file: {e}")
    
    def setup(self):
        """Main setup process"""
        logger.info("🚀 Starting PostgreSQL + pgvector setup...")
        
        # Step 1: Check PostgreSQL is running
        if not self.check_postgresql_running():
            logger.error("❌ PostgreSQL not running. Please start it first.")
            return False
        
        # Step 2: Check pgvector extension
        self.check_pgvector_extension()
        
        # Step 3: Create database and user
        self.create_database_and_user()
        
        # Step 4: Test connection
        if self.test_connection():
            logger.info("✅ Database setup completed successfully!")
            return True
        else:
            logger.error("❌ Database setup failed")
            return False

if __name__ == "__main__":
    setup = DatabaseSetup()
    success = setup.setup()
    
    if success:
        print("\n🎉 Database setup complete!")
        print("Next steps:")
        print("1. Run schema creation: python scripts/create_schema.py")
        print("2. Run data migration: python scripts/migrate_data.py")
    else:
        print("\n❌ Database setup failed. Check logs above.")
        sys.exit(1)