#!/usr/bin/env python3
"""
Manual export endpoint check.

Note: This script is interactive (prompts for access_token) and is intended
to be run manually, not under pytest. We mark the pytest test as skipped to
avoid blocking CI with stdin prompts.
"""
import requests
import sys
import pytest

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

@pytest.mark.skip(reason="manual integration check that prompts for token; skip in CI")
def test_export_endpoint():
    """Test the export endpoint directly"""
    
    print("Testing Aging Report Export Endpoint")
    print("=" * 50)
    
    # First, check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Server is running (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running!")
        print("  Please start the server with: uvicorn app.main:app --reload")
        sys.exit(1)
    
    # You'll need a valid auth token - get this from your browser's dev tools
    # or create a test login
    print("\n⚠ NOTE: You need to provide a valid auth token")
    print("  Get it from: Browser DevTools → Application → Cookies → access_token")
    token = input("\nEnter your access_token (or press Enter to skip auth test): ").strip()
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Test Excel export
    print("\n1. Testing Excel Export...")
    print(f"   URL: {BASE_URL}{API_PREFIX}/reports/aging/export?format=excel")
    
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/reports/aging/export",
            params={"format": "excel"},
            headers=headers,
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Content-Length: {len(response.content)} bytes")
        
        if 'Content-Disposition' in response.headers:
            print(f"   Content-Disposition: {response.headers['Content-Disposition']}")
        
        # Check if response is binary or JSON
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            print("\n   ⚠ Response is JSON (not a file):")
            try:
                print(f"   {response.json()}")
            except:
                print(f"   {response.text[:500]}")
        elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
            print("\n   ✓ Response is Excel file (binary)")
            print("   File should download automatically in browser")
            
            # Optionally save to test
            with open('/tmp/test_export.xlsx', 'wb') as f:
                f.write(response.content)
            print("   ✓ Saved test file to: /tmp/test_export.xlsx")
        else:
            print(f"\n   ⚠ Unexpected content type: {content_type}")
            print(f"   First 200 chars: {response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Request failed: {e}")
    
    # Test PDF export
    print("\n2. Testing PDF Export...")
    print(f"   URL: {BASE_URL}{API_PREFIX}/reports/aging/export?format=pdf")
    
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/reports/aging/export",
            params={"format": "pdf"},
            headers=headers,
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Content-Length: {len(response.content)} bytes")
        
        if 'Content-Disposition' in response.headers:
            print(f"   Content-Disposition: {response.headers['Content-Disposition']}")
        
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            print("\n   ⚠ Response is JSON (not a file):")
            try:
                print(f"   {response.json()}")
            except:
                print(f"   {response.text[:500]}")
        elif 'application/pdf' in content_type:
            print("\n   ✓ Response is PDF file (binary)")
            print("   File should download automatically in browser")
            
            # Optionally save to test
            with open('/tmp/test_export.pdf', 'wb') as f:
                f.write(response.content)
            print("   ✓ Saved test file to: /tmp/test_export.pdf")
        else:
            print(f"\n   ⚠ Unexpected content type: {content_type}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("Test complete!")
    print("\nNext steps:")
    print("1. If response is JSON → Backend changes NOT applied yet")
    print("2. If response is binary → Backend is correct, check frontend")
    print("3. Check browser Network tab for actual response")

if __name__ == "__main__":
    test_export_endpoint()
