#!/usr/bin/env python3
"""
Script to clean up duplicate job_ids in the database.
This should be run once after applying the unique constraint.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://admin:admin123@localhost:27017/pcap_reporter?authSource=admin")
DATABASE_NAME = "pcap_reporter"

async def cleanup_duplicates():
    """Remove duplicate job_ids, keeping only the latest entry."""
    client = AsyncIOMotorClient(DATABASE_URL)
    db = client[DATABASE_NAME]
    collection = db["reports"]
    
    print("🔍 Searching for duplicate job_ids...")
    
    # Find all job_ids with their counts
    pipeline = [
        {"$group": {"_id": "$job_id", "count": {"$sum": 1}, "docs": {"$push": {"id": "$_id", "created_at": "$created_at"}}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicates = await collection.aggregate(pipeline).to_list(None)
    
    if not duplicates:
        print("✅ No duplicate job_ids found!")
        return
    
    print(f"📋 Found {len(duplicates)} duplicate job_ids")
    
    removed_count = 0
    for duplicate in duplicates:
        job_id = duplicate["_id"]
        docs = duplicate["docs"]
        count = duplicate["count"]
        
        print(f"🔧 Processing job_id: {job_id} ({count} duplicates)")
        
        # Sort by created_at to keep the latest one
        docs.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Remove all but the latest
        for doc in docs[1:]:  # Skip the first (latest) one
            result = await collection.delete_one({"_id": doc["id"]})
            if result.deleted_count > 0:
                removed_count += 1
                print(f"  ❌ Removed duplicate: {doc['id']}")
    
    print(f"🎉 Cleanup complete! Removed {removed_count} duplicate entries.")
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())