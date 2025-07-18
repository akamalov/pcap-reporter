#!/usr/bin/env python3
"""
Debug the streaming response issue.
"""

import asyncio
from io import BytesIO
from fastapi.responses import StreamingResponse

async def test_streaming_debug():
    """Debug streaming response behavior"""
    
    print("🔍 Testing StreamingResponse with different approaches...")
    
    # Create test data
    test_data = b"PDF content test data 123456789"
    
    # Test 1: iter([bytes])
    print("\n📝 Test 1: iter([bytes])")
    response1 = StreamingResponse(
        iter([test_data]),
        media_type="application/pdf"
    )
    
    content1 = b""
    async for chunk in response1.body_iterator:
        content1 += chunk
    
    print(f"   Original: {len(test_data)} bytes")
    print(f"   Streamed: {len(content1)} bytes")
    print(f"   Match: {content1 == test_data}")
    print(f"   Content: {content1[:50]}...")
    
    # Test 2: BytesIO
    print("\n📝 Test 2: BytesIO")
    response2 = StreamingResponse(
        BytesIO(test_data),
        media_type="application/pdf"
    )
    
    content2 = b""
    async for chunk in response2.body_iterator:
        content2 += chunk
    
    print(f"   Original: {len(test_data)} bytes")
    print(f"   Streamed: {len(content2)} bytes")
    print(f"   Match: {content2 == test_data}")
    print(f"   Content: {content2[:50]}...")
    
    # Test 3: Generator function
    print("\n📝 Test 3: Generator function")
    
    def generate_content():
        yield test_data
    
    response3 = StreamingResponse(
        generate_content(),
        media_type="application/pdf"
    )
    
    content3 = b""
    async for chunk in response3.body_iterator:
        content3 += chunk
    
    print(f"   Original: {len(test_data)} bytes")
    print(f"   Streamed: {len(content3)} bytes")
    print(f"   Match: {content3 == test_data}")
    print(f"   Content: {content3[:50]}...")
    
    # Test 4: Async generator
    print("\n📝 Test 4: Async generator")
    
    async def generate_content_async():
        yield test_data
    
    response4 = StreamingResponse(
        generate_content_async(),
        media_type="application/pdf"
    )
    
    content4 = b""
    async for chunk in response4.body_iterator:
        content4 += chunk
    
    print(f"   Original: {len(test_data)} bytes")
    print(f"   Streamed: {len(content4)} bytes")
    print(f"   Match: {content4 == test_data}")
    print(f"   Content: {content4[:50]}...")

if __name__ == "__main__":
    asyncio.run(test_streaming_debug())