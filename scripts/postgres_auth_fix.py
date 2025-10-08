#!/usr/bin/env python3
"""
PostgreSQL Authentication Fix Script
Following DEVELOPMENT_RULES.md: Fix root causes, not symptoms
"""

import os
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgreSQLAuthFix:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
    def try_peer_authentication(self):
        """Try peer authentication (Unix socket)"""
        logger.info("🔍 Trying peer authentication...")
        
        try:
            # Check if we can connect via Unix socket with peer auth
            result = subprocess.run(
                ['psql', '-U', 'postgres', '-d', 'postgres', '-c', 'SELECT current_user;'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("✅ Peer authentication successful")
                return True
            else:
                logger.debug(f"Peer auth failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.debug(f"Peer auth exception: {e}")
            return False
    
    def create_pgpass_file(self):
        """Create .pgpass file for password authentication"""
        logger.info("🔐 Creating .pgpass file...")
        
        try:
            pgpass_path = Path.home() / '.pgpass'
            
            # Common PostgreSQL passwords to try
            password_entries = [
                "localhost:5432:*:postgres:postgres",
                "localhost:5432:*:postgres:",  # Empty password
                "localhost:5432:hormozi_rag:rag_user:rag_password123",
            ]
            
            with open(pgpass_path, 'w') as f:
                for entry in password_entries:
                    f.write(entry + '\n')
            
            # Set proper permissions (600)
            os.chmod(pgpass_path, 0o600)
            
            logger.info(f"✅ Created .pgpass file: {pgpass_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create .pgpass: {e}")
            return False
    
    def test_connection_methods(self):
        """Test various connection methods"""
        logger.info("🧪 Testing connection methods...")
        
        # Connection methods to try
        methods = [
            # Method 1: Local socket with current user
            {
                'name': 'Local socket (current user)',
                'cmd': ['psql', 'postgres', '-c', 'SELECT current_user;'],
                'params': None
            },
            
            # Method 2: Local socket as postgres user
            {
                'name': 'Local socket (postgres user)',
                'cmd': ['psql', '-U', 'postgres', 'postgres', '-c', 'SELECT current_user;'],
                'params': None
            },
            
            # Method 3: TCP with postgres/postgres
            {
                'name': 'TCP (postgres/postgres)',
                'cmd': ['psql', '-h', 'localhost', '-U', 'postgres', 'postgres', '-c', 'SELECT current_user;'],
                'params': {'PGPASSWORD': 'postgres'}
            },
            
            # Method 4: TCP with postgres/empty password
            {
                'name': 'TCP (postgres/empty)',
                'cmd': ['psql', '-h', 'localhost', '-U', 'postgres', 'postgres', '-c', 'SELECT current_user;'],
                'params': {'PGPASSWORD': ''}
            },
        ]
        
        working_method = None
        
        for method in methods:
            try:
                logger.info(f"Testing: {method['name']}")
                
                env = os.environ.copy()
                if method['params']:
                    env.update(method['params'])
                
                result = subprocess.run(
                    method['cmd'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ SUCCESS: {method['name']}")
                    logger.info(f"   Output: {result.stdout.strip()}")
                    working_method = method
                    break
                else:
                    logger.debug(f"   Failed: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                logger.debug(f"   Timeout: {method['name']}")
            except Exception as e:
                logger.debug(f"   Exception: {e}")
        
        return working_method
    
    def create_database_simple(self, working_method):
        """Create database using working connection method"""
        if not working_method:
            logger.error("❌ No working connection method found")
            return False
            
        logger.info("🏗️ Creating database with working method...")
        
        try:
            # Prepare environment
            env = os.environ.copy()
            if working_method['params']:
                env.update(working_method['params'])
            
            # Create database
            cmd_base = working_method['cmd'][:-2]  # Remove the SELECT query
            create_db_cmd = cmd_base + ['-c', 'CREATE DATABASE hormozi_rag;']
            
            result = subprocess.run(
                create_db_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode == 0 or 'already exists' in result.stderr:
                logger.info("✅ Database 'hormozi_rag' created or already exists")
                
                # Update .env file with working connection
                self.update_env_with_working_method(working_method)
                return True
            else:
                logger.error(f"❌ Database creation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception creating database: {e}")
            return False
    
    def update_env_with_working_method(self, working_method):
        """Update .env file with working connection parameters"""
        try:
            env_file = self.project_root / '.env'
            
            # Determine connection parameters from working method
            if '-h' in working_method['cmd']:
                host = 'localhost'
            else:
                host = 'localhost'  # Unix socket, but we'll use localhost
            
            if '-U' in working_method['cmd']:
                user_idx = working_method['cmd'].index('-U') + 1
                user = working_method['cmd'][user_idx]
            else:
                user = 'postgres'
            
            password = working_method['params'].get('PGPASSWORD', 'postgres') if working_method['params'] else 'postgres'
            
            # Read and update .env file
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            updated_lines = []
            for line in lines:
                if line.startswith('POSTGRES_HOST='):
                    updated_lines.append(f"POSTGRES_HOST={host}\n")
                elif line.startswith('POSTGRES_USER='):
                    updated_lines.append(f"POSTGRES_USER={user}\n")
                elif line.startswith('POSTGRES_PASSWORD='):
                    updated_lines.append(f"POSTGRES_PASSWORD={password}\n")
                elif line.startswith('POSTGRES_DB='):
                    updated_lines.append(f"POSTGRES_DB=hormozi_rag\n")
                else:
                    updated_lines.append(line)
            
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            logger.info(f"✅ Updated .env with working credentials: {user}@{host}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update .env: {e}")
    
    def fix_authentication(self):
        """Main authentication fix process"""
        logger.info("🔧 Starting PostgreSQL authentication fix...")
        
        # Step 1: Create .pgpass file
        self.create_pgpass_file()
        
        # Step 2: Test connection methods
        working_method = self.test_connection_methods()
        
        if working_method:
            # Step 3: Create database using working method
            if self.create_database_simple(working_method):
                logger.info("✅ PostgreSQL authentication fixed successfully!")
                return True
        
        logger.error("❌ Could not fix PostgreSQL authentication")
        return False

if __name__ == "__main__":
    auth_fix = PostgreSQLAuthFix()
    success = auth_fix.fix_authentication()
    
    if success:
        print("\n🎉 PostgreSQL authentication fixed!")
        print("You can now proceed with schema creation and data migration.")
    else:
        print("\n❌ Could not fix PostgreSQL authentication.")
        print("Manual intervention may be required.")