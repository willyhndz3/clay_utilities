#!/usr/bin/env python3
"""
Railway Deployment for ELE LLC Members API
Full version with real scraper for Clay integration
"""

from flask import Flask, jsonify, request
import json
import os
from ele_members_json_scraper import ELEMembersJSONScraper

app = Flask(__name__)

# Global scraper instance
scraper = None
members_data = []

def initialize_scraper():
    """Initialize the scraper and fetch real data"""
    global scraper, members_data
    if scraper is None:
        print("🔄 Initializing ELE LLC Members scraper...")
        scraper = ELEMembersJSONScraper()
        scraper_members = scraper.scrape_all_members()
        
        # Convert Member objects to Clay-compatible dictionaries
        members_data = []
        for member in scraper_members:
            members_data.append({
                "id": member.name.lower().replace(" ", "-").replace("'", ""),
                "name": member.name,
                "title": member.title or "",
                "company": member.company or "",
                "location": member.location or "",
                "email": member.email or "",
                "phone": member.phone or "",
                "linkedin_url": member.linkedin or "",
                "website_url": member.website or "",
                "bio": member.bio or "",
                "profile_url": member.profile_url or "",
                "member_type": member.member_type or "Standard Member",
                "badges": member.badges or "",
                "source": "ELE LLC Directory"
            })
        
        print(f"✅ Scraped {len(members_data)} members successfully!")
    
    return members_data

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
    members = initialize_scraper()
    return jsonify({
        "success": True,
        "status": "active",
        "service": "ELE LLC Members API (Railway - Real Data)",
        "version": "2.0.0",
        "members_count": len(members),
        "message": "API is running with real ELE LLC member data"
    })

@app.route('/clay/members', methods=['GET'])
def clay_get_members():
    """Clay-compatible endpoint to get all members - returns array directly"""
    members = initialize_scraper()
    # Clay expects a direct array, not an object with a 'data' property
    return jsonify(members)

@app.route('/clay/members/search', methods=['GET'])
def clay_search_members():
    """Clay-compatible search endpoint - returns array directly"""
    members = initialize_scraper()
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify([]), 400
    
    results = [m for m in members if query in m['name'].lower() or query in m.get('title', '').lower()]
    
    # Clay expects a direct array
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Railway API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
