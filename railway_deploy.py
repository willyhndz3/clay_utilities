#!/usr/bin/env python3
"""
Railway Deployment for ELE LLC Members API
Minimal version for Clay integration
"""

from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

# Mock data for testing (will be replaced with real scraper later)
MOCK_MEMBERS = [
    {
        "id": "test-member-1",
        "name": "Test Member 1",
        "title": "CEO",
        "company": "Test Company",
        "location": "San Francisco, CA",
        "email": "test@example.com",
        "phone": "555-0123",
        "linkedin_url": "https://linkedin.com/in/test",
        "website_url": "https://example.com",
        "bio": "Test bio",
        "profile_url": "https://www.ele.llc/members/test",
        "source": "ELE LLC Directory"
    }
]

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ELE LLC Members API",
        "message": "API is running on Railway! 🚀"
    })

@app.route('/clay/status', methods=['GET'])
def clay_status():
    """Clay-compatible status endpoint"""
    return jsonify({
        "success": True,
        "status": "active",
        "service": "ELE LLC Members API (Railway)",
        "version": "1.0.0",
        "members_count": len(MOCK_MEMBERS),
        "message": "API is running and ready for Clay cloud integration"
    })

@app.route('/clay/members', methods=['GET'])
def clay_get_members():
    """Clay-compatible endpoint to get all members"""
    return jsonify({
        "success": True,
        "data": MOCK_MEMBERS,
        "count": len(MOCK_MEMBERS),
        "message": "Members retrieved successfully"
    })

@app.route('/clay/members/search', methods=['GET'])
def clay_search_members():
    """Clay-compatible search endpoint"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' is required",
            "data": [],
            "count": 0
        }), 400
    
    results = [m for m in MOCK_MEMBERS if query in m['name'].lower() or query in m.get('title', '').lower()]
    
    return jsonify({
        "success": True,
        "data": results,
        "count": len(results),
        "query": query,
        "message": f"Found {len(results)} members matching '{query}'"
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Railway API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
