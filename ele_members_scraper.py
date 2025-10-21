#!/usr/bin/env python3
"""
ELE LLC Members Directory Scraper
Scrapes member information from https://www.ele.llc/members?_active=false
and exports to CSV or provides API access.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re
from dataclasses import dataclass
from flask import Flask, jsonify, request
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ele_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Member:
    """Data class for member information"""
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    profile_url: Optional[str] = None

class ELEMembersScraper:
    """Main scraper class for ELE LLC members directory"""
    
    def __init__(self, base_url: str = "https://www.ele.llc"):
        self.base_url = base_url
        self.members_url = f"{base_url}/members?_active=false"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.members: List[Member] = []
        
    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch a page with retry logic and rate limiting"""
        for attempt in range(retries):
            try:
                logger.info(f"Fetching: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Rate limiting - be respectful
                time.sleep(1)
                
                return BeautifulSoup(response.content, 'html.parser')
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
        
        return None
    
    def extract_member_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract member profile links from the main directory page"""
        member_links = []
        
        # Look for various patterns that might contain member links
        selectors = [
            'a[href*="/members/"]',
            'a[href*="/member/"]',
            'a[href*="/profile/"]',
            '.member-card a',
            '.member-item a',
            '.profile-link',
            '[data-member-id] a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in member_links:
                        member_links.append(full_url)
        
        # Also look for pagination if needed
        pagination_links = soup.select('a[href*="page="], a[href*="p="]')
        for link in pagination_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in member_links:
                    member_links.append(full_url)
        
        logger.info(f"Found {len(member_links)} member links")
        return member_links
    
    def extract_member_info(self, soup: BeautifulSoup, profile_url: str) -> Optional[Member]:
        """Extract member information from a profile page"""
        try:
            # Initialize member with basic info
            member = Member(name="", profile_url=profile_url)
            
            # Extract name - try multiple selectors
            name_selectors = [
                'h1',
                '.member-name',
                '.profile-name',
                '.name',
                'title'
            ]
            
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem and name_elem.get_text(strip=True):
                    member.name = name_elem.get_text(strip=True)
                    break
            
            # Extract title/position
            title_selectors = [
                '.member-title',
                '.profile-title',
                '.title',
                '.position',
                '.job-title'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    member.title = title_elem.get_text(strip=True)
                    break
            
            # Extract company
            company_selectors = [
                '.member-company',
                '.profile-company',
                '.company',
                '.organization'
            ]
            
            for selector in company_selectors:
                company_elem = soup.select_one(selector)
                if company_elem:
                    member.company = company_elem.get_text(strip=True)
                    break
            
            # Extract location
            location_selectors = [
                '.member-location',
                '.profile-location',
                '.location',
                '.address'
            ]
            
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem:
                    member.location = location_elem.get_text(strip=True)
                    break
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_elem = soup.find(text=re.compile(email_pattern))
            if email_elem:
                member.email = re.search(email_pattern, email_elem).group()
            
            # Extract phone
            phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
            phone_elem = soup.find(text=re.compile(phone_pattern))
            if phone_elem:
                member.phone = re.search(phone_pattern, phone_elem).group()
            
            # Extract LinkedIn
            linkedin_elem = soup.find('a', href=re.compile(r'linkedin\.com'))
            if linkedin_elem:
                member.linkedin = linkedin_elem.get('href')
            
            # Extract website
            website_elem = soup.find('a', href=re.compile(r'https?://(?!.*linkedin\.com)'))
            if website_elem:
                member.website = website_elem.get('href')
            
            # Extract bio/description
            bio_selectors = [
                '.member-bio',
                '.profile-bio',
                '.bio',
                '.description',
                '.about'
            ]
            
            for selector in bio_selectors:
                bio_elem = soup.select_one(selector)
                if bio_elem:
                    member.bio = bio_elem.get_text(strip=True)
                    break
            
            # If no specific bio found, try to get a general description
            if not member.bio:
                # Look for paragraphs that might contain bio info
                paragraphs = soup.select('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50 and not any(keyword in text.lower() for keyword in ['copyright', 'privacy', 'terms', 'cookie']):
                        member.bio = text
                        break
            
            return member if member.name else None
            
        except Exception as e:
            logger.error(f"Error extracting member info from {profile_url}: {e}")
            return None
    
    def scrape_all_members(self) -> List[Member]:
        """Main method to scrape all members from the directory"""
        logger.info("Starting ELE LLC members scraping...")
        
        # Get the main directory page
        soup = self.get_page(self.members_url)
        if not soup:
            logger.error("Failed to fetch main directory page")
            return []
        
        # Extract member links
        member_links = self.extract_member_links(soup)
        
        if not member_links:
            logger.warning("No member links found. The page structure might have changed.")
            # Try to extract members directly from the main page
            return self.extract_members_from_main_page(soup)
        
        # Scrape each member profile
        for i, link in enumerate(member_links, 1):
            logger.info(f"Scraping member {i}/{len(member_links)}: {link}")
            
            member_soup = self.get_page(link)
            if member_soup:
                member = self.extract_member_info(member_soup, link)
                if member:
                    self.members.append(member)
                    logger.info(f"Successfully scraped: {member.name}")
                else:
                    logger.warning(f"Failed to extract member info from {link}")
            else:
                logger.warning(f"Failed to fetch member page: {link}")
        
        logger.info(f"Scraping completed. Found {len(self.members)} members.")
        return self.members
    
    def extract_members_from_main_page(self, soup: BeautifulSoup) -> List[Member]:
        """Extract member information directly from the main directory page"""
        members = []
        
        # Look for member cards or items on the main page
        member_selectors = [
            '.member-card',
            '.member-item',
            '.profile-card',
            '.member',
            '[data-member]'
        ]
        
        for selector in member_selectors:
            member_elements = soup.select(selector)
            for elem in member_elements:
                member = Member(name="")
                
                # Extract name
                name_elem = elem.select_one('h1, h2, h3, .name, .member-name')
                if name_elem:
                    member.name = name_elem.get_text(strip=True)
                
                # Extract other info
                title_elem = elem.select_one('.title, .position, .job-title')
                if title_elem:
                    member.title = title_elem.get_text(strip=True)
                
                company_elem = elem.select_one('.company, .organization')
                if company_elem:
                    member.company = company_elem.get_text(strip=True)
                
                location_elem = elem.select_one('.location, .address')
                if location_elem:
                    member.location = location_elem.get_text(strip=True)
                
                # Extract email
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                text_content = elem.get_text()
                email_match = re.search(email_pattern, text_content)
                if email_match:
                    member.email = email_match.group()
                
                # Extract LinkedIn
                linkedin_elem = elem.find('a', href=re.compile(r'linkedin\.com'))
                if linkedin_elem:
                    member.linkedin = linkedin_elem.get('href')
                
                if member.name:
                    members.append(member)
        
        return members
    
    def export_to_csv(self, filename: str = "ele_members.csv") -> str:
        """Export members data to CSV file"""
        if not self.members:
            logger.warning("No members to export")
            return ""
        
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'name', 'title', 'company', 'location', 'email', 
                'phone', 'linkedin', 'website', 'bio', 'profile_url'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for member in self.members:
                writer.writerow({
                    'name': member.name,
                    'title': member.title or '',
                    'company': member.company or '',
                    'location': member.location or '',
                    'email': member.email or '',
                    'phone': member.phone or '',
                    'linkedin': member.linkedin or '',
                    'website': member.website or '',
                    'bio': member.bio or '',
                    'profile_url': member.profile_url or ''
                })
        
        logger.info(f"Exported {len(self.members)} members to {filepath}")
        return filepath
    
    def export_to_json(self, filename: str = "ele_members.json") -> str:
        """Export members data to JSON file"""
        if not self.members:
            logger.warning("No members to export")
            return ""
        
        filepath = os.path.join(os.getcwd(), filename)
        
        members_data = []
        for member in self.members:
            members_data.append({
                'name': member.name,
                'title': member.title,
                'company': member.company,
                'location': member.location,
                'email': member.email,
                'phone': member.phone,
                'linkedin': member.linkedin,
                'website': member.website,
                'bio': member.bio,
                'profile_url': member.profile_url
            })
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(members_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(self.members)} members to {filepath}")
        return filepath

def create_api_app(scraper: ELEMembersScraper) -> Flask:
    """Create Flask API for accessing member data"""
    app = Flask(__name__)
    
    @app.route('/api/members', methods=['GET'])
    def get_members():
        """Get all members"""
        return jsonify({
            'count': len(scraper.members),
            'members': [
                {
                    'name': member.name,
                    'title': member.title,
                    'company': member.company,
                    'location': member.location,
                    'email': member.email,
                    'phone': member.phone,
                    'linkedin': member.linkedin,
                    'website': member.website,
                    'bio': member.bio,
                    'profile_url': member.profile_url
                } for member in scraper.members
            ]
        })
    
    @app.route('/api/members/search', methods=['GET'])
    def search_members():
        """Search members by query"""
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        results = []
        for member in scraper.members:
            if (query in member.name.lower() or 
                (member.title and query in member.title.lower()) or
                (member.company and query in member.company.lower()) or
                (member.location and query in member.location.lower())):
                results.append({
                    'name': member.name,
                    'title': member.title,
                    'company': member.company,
                    'location': member.location,
                    'email': member.email,
                    'phone': member.phone,
                    'linkedin': member.linkedin,
                    'website': member.website,
                    'bio': member.bio,
                    'profile_url': member.profile_url
                })
        
        return jsonify({
            'query': query,
            'count': len(results),
            'results': results
        })
    
    @app.route('/api/members/export/csv', methods=['GET'])
    def export_csv():
        """Export members to CSV"""
        filename = f"ele_members_{int(time.time())}.csv"
        filepath = scraper.export_to_csv(filename)
        if filepath:
            return jsonify({'message': f'CSV exported to {filename}', 'filepath': filepath})
        else:
            return jsonify({'error': 'No members to export'}), 400
    
    @app.route('/api/members/export/json', methods=['GET'])
    def export_json():
        """Export members to JSON"""
        filename = f"ele_members_{int(time.time())}.json"
        filepath = scraper.export_to_json(filename)
        if filepath:
            return jsonify({'message': f'JSON exported to {filename}', 'filepath': filepath})
        else:
            return jsonify({'error': 'No members to export'}), 400
    
    return app

def main():
    """Main function to run the scraper"""
    scraper = ELEMembersScraper()
    
    # Scrape all members
    members = scraper.scrape_all_members()
    
    if members:
        # Export to CSV
        csv_file = scraper.export_to_csv()
        print(f"CSV exported to: {csv_file}")
        
        # Export to JSON
        json_file = scraper.export_to_json()
        print(f"JSON exported to: {json_file}")
        
        # Print summary
        print(f"\nScraping Summary:")
        print(f"Total members found: {len(members)}")
        print(f"Members with email: {sum(1 for m in members if m.email)}")
        print(f"Members with LinkedIn: {sum(1 for m in members if m.linkedin)}")
        print(f"Members with company: {sum(1 for m in members if m.company)}")
        
        # Start API server
        print(f"\nStarting API server...")
        print(f"API endpoints available:")
        print(f"  GET /api/members - Get all members")
        print(f"  GET /api/members/search?q=query - Search members")
        print(f"  GET /api/members/export/csv - Export CSV")
        print(f"  GET /api/members/export/json - Export JSON")
        
        app = create_api_app(scraper)
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("No members found. Please check the website structure or try again later.")

if __name__ == "__main__":
    main()
