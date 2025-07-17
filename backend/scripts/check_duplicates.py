#!/usr/bin/env python3
"""
Script to check for duplicate job_ids in the database.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://admin:admin123@localhost:27017/pcap_reporter?authSource=admin")
DATABASE_NAME = "pcap_reporter"

async def check_duplicates():
    """Check for duplicate job_ids."""
    client = AsyncIOMotorClient(DATABASE_URL)
    db = client[DATABASE_NAME]
    collection = db["reports"]
    
    print("🔍 Checking for duplicate job_ids...")
    
    # Get all documents
    cursor = collection.find({})
    job_ids = defaultdict(list)
    
    async for doc in cursor:
        job_id = doc.get("job_id")
        if job_id:
            job_ids[job_id].append({
                "id": doc["_id"],
                "created_at": doc.get("created_at"),
                "status": doc.get("status")
            })
    
    # Find duplicates
    duplicates = {job_id: docs for job_id, docs in job_ids.items() if len(docs) > 1}
    
    if duplicates:
        print(f"📋 Found {len(duplicates)} duplicate job_ids:")
        for job_id, docs in duplicates.items():
            print(f"  🔄 {job_id}: {len(docs)} entries")
            for doc in docs:
                print(f"    - {doc['id']} ({doc.get('status', 'unknown')}) - {doc.get('created_at', 'no date')}")
    else:
        print("✅ No duplicates found!")
    
    print(f"📊 Total unique job_ids: {len(job_ids)}")
    print(f"📊 Total documents: {sum(len(docs) for docs in job_ids.values())}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_duplicates())