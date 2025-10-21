#!/usr/bin/env python3
"""
Railway Deployment for ELE LLC Members API
This creates a production-ready API for Clay integration
"""

from flask import Flask, jsonify, request
import json
import csv
import io
import os
from ele_members_scraper import ELEMembersScraper

app = Flask(__name__)

# Global scraper instance
scraper = None

def initialize_scraper():
    """Initialize the scraper with real data"""
    global scraper
    if scraper is None:
        scraper = ELEMembersScraper()
        # Scrape the real data
        members = scraper.scrape_all_members()
        print(f"✅ Scraped {len(members)} members for Clay cloud integration")

@app.route('/clay/members', methods=['GET'])
def clay_get_members():
    """Clay-compatible endpoint to get all members"""
    initialize_scraper()
    
    # Clay expects a specific format
    response = {
        "success": True,
        "data": [],
        "count": len(scraper.members),
        "message": "Members retrieved successfully"
    }
    
    for member in scraper.members:
        clay_member = {
            "id": member.name.lower().replace(" ", "-"),
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
            "source": "ELE LLC Directory"
        }
        response["data"].append(clay_member)
    
    return jsonify(response)

@app.route('/clay/status', methods=['GET'])
def clay_status():
    """Clay-compatible status endpoint"""
    initialize_scraper()
    
    return jsonify({
        "success": True,
        "status": "active",
        "service": "ELE LLC Members API (Railway)",
        "version": "1.0.0",
        "members_count": len(scraper.members),
        "message": "API is running and ready for Clay cloud integration"
    })

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ELE LLC Members API",
        "message": "API is running"
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
