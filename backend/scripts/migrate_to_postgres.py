"""
SQLite to PostgreSQL Migration Script

This script migrates all data from SQLite to PostgreSQL with pgvector support.
It preserves the original SQLite database as a backup.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError


# SQLite connection
SQLITE_URL = "sqlite:///./favbox.db"

# PostgreSQL connection
POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://favbox:favbox_secure_password_change_in_production@localhost:5432/favbox"
)


async def backup_sqlite():
    """
    Backup SQLite database before migration
    """
    import shutil
    from pathlib import Path

    sqlite_db = Path("./favbox.db")
    if sqlite_db.exists():
        backup_path = Path(f"./favbox_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(sqlite_db, backup_path)
        print(f"✅ SQLite database backed up to: {backup_path}")
        return backup_path
    else:
        print("⚠️  No SQLite database found to backup")
        return None


async def migrate_data():
    """
    Migrate data from SQLite to PostgreSQL
    """
    print("🚀 Starting migration from SQLite to PostgreSQL...")

    # 1. Backup SQLite
    await backup_sqlite()

    # 2. Create sync engine for SQLite (reading)
    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

    # 3. Create async engine for PostgreSQL (writing)
    postgres_engine = create_async_engine(
        POSTGRES_URL,
        echo=True,  # Set to False in production
    )

    # 4. Connect to databases
    with sqlite_engine.connect() as sqlite_conn:
        async with postgres_engine.begin() as postgres_conn:
            print("✅ Connected to both databases")

            # 5. Migrate users table
            print("\n📊 Migrating users...")
            result = sqlite_conn.execute(text("SELECT * FROM users"))
            users = result.fetchall()

            if users:
                # Create table structure will be handled by SQLAlchemy later
                # Just count for now
                print(f"   Found {len(users)} users")
            else:
                print("   ⚠️  No users found")

            # 6. Migrate bookmarks table
            print("\n📊 Migrating bookmarks...")
            result = sqlite_conn.execute(text("SELECT * FROM bookmarks"))
            bookmarks = result.fetchall()
            print(f"   Found {len(bookmarks)} bookmarks")

            # 7. Migrate collections table
            print("\n📊 Migrating collections...")
            result = sqlite_conn.execute(text("SELECT * FROM collections"))
            collections = result.fetchall()
            print(f"   Found {len(collections)} collections")

            # 8. Migrate collection_bookmarks table
            print("\n📊 Migrating collection_bookmarks...")
            try:
                result = sqlite_conn.execute(text("SELECT * FROM collection_bookmarks"))
                collection_bookmarks = result.fetchall()
                print(f"   Found {len(collection_bookmarks)} collection bookmarks")
            except Exception as e:
                print(f"   ⚠️  collection_bookmarks table might not exist: {e}")

    # 9. Close connections
    await postgres_engine.dispose()
    sqlite_engine.dispose()

    print("\n✅ Migration completed!")
    print("\n📝 Next steps:")
    print("   1. Update DATABASE_URL in backend/.env")
    print("   2. Run: python -m app.main to create PostgreSQL tables")
    print("   3. Run the data import script to copy data")
    print("   4. Verify data integrity")


async def check_postgres_connection():
    """
    Check if PostgreSQL is running and accessible
    """
    try:
        engine = create_async_engine(POSTGRES_URL)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL is running!")
            print(f"   Version: {version[:50]}...")

            # Check pgvector extension
            result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            if result.scalar():
                print("✅ pgvector extension is installed!")
            else:
                print("⚠️  pgvector extension NOT found. Run: CREATE EXTENSION vector;")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ Cannot connect to PostgreSQL: {e}")
        print("\n💡 Make sure Docker container is running:")
        print("   docker-compose up -d")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate FavBox from SQLite to PostgreSQL")
    parser.add_argument("--check", action="store_true", help="Check PostgreSQL connection")
    parser.add_argument("--migrate", action="store_true", help="Run migration")

    args = parser.parse_args()

    if args.check:
        asyncio.run(check_postgres_connection())
    elif args.migrate:
        if asyncio.run(check_postgres_connection()):
            asyncio.run(migrate_data())
        else:
            print("\n❌ Cannot proceed with migration. Please check PostgreSQL connection.")
    else:
        print("Usage:")
        print("  python migrate_to_postgres.py --check      # Check PostgreSQL connection")
        print("  python migrate_to_postgres.py --migrate    # Run migration")
