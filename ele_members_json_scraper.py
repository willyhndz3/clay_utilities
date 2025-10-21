#!/usr/bin/env python3
"""
ELE LLC Members Directory Scraper - JSON Version
Extracts all 700+ members from the Next.js __NEXT_DATA__ JSON
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    member_type: Optional[str] = None
    badges: Optional[str] = None

class ELEMembersJSONScraper:
    """Scraper that extracts member data from Next.js JSON"""
    
    def __init__(self, base_url: str = "https://www.ele.llc"):
        self.base_url = base_url
        self.members_url = f"{base_url}/members"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        })
        self.members: List[Member] = []
    
    def scrape_all_members(self) -> List[Member]:
        """Extract all members from the JSON data"""
        logger.info(f"Fetching members from {self.members_url}")
        
        try:
            response = self.session.get(self.members_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the Next.js data script tag
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not next_data_script:
                logger.error("Could not find __NEXT_DATA__ script tag")
                return []
            
            # Parse the JSON
            data = json.loads(next_data_script.string)
            members_json = data.get('props', {}).get('pageProps', {}).get('members', [])
            
            logger.info(f"Found {len(members_json)} members in JSON data")
            
            # Convert JSON to Member objects
            for member_data in members_json:
                member = self.parse_member(member_data)
                if member:
                    self.members.append(member)
            
            logger.info(f"Successfully parsed {len(self.members)} members")
            return self.members
            
        except Exception as e:
            logger.error(f"Error scraping members: {e}")
            return []
    
    def parse_member(self, member_data: dict) -> Optional[Member]:
        """Parse a member from JSON data"""
        try:
            name = member_data.get('display_name', '')
            if not name:
                return None
            
            # Extract email
            email = member_data.get('user_email', '')
            
            # Extract position/title and try to split company
            position = member_data.get('position', '')
            title = None
            company = None
            
            if position:
                # Try to split "Title @ Company" format
                if '@' in position:
                    parts = position.split('@', 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                else:
                    title = position
            
            # Extract LinkedIn from socials JSON
            linkedin = None
            try:
                socials_str = member_data.get('socials', '[]')
                socials = json.loads(socials_str) if socials_str else []
                for social in socials:
                    if isinstance(social, dict) and 'linkedin' in social:
                        linkedin = social['linkedin']
                        if linkedin:
                            break
            except:
                pass
            
            # Extract badges (Influencer, Ambassador, etc.)
            badges = member_data.get('badges', [])
            badges_str = ', '.join(badges) if badges else None
            
            # Extract roles/designations from role_cap
            roles = []
            try:
                role_cap_str = member_data.get('role_cap', '[]')
                roles = json.loads(role_cap_str) if role_cap_str else []
            except:
                pass
            
            # Determine member type based on roles
            member_type = self.determine_member_type(roles)
            
            # Create profile URL
            user_nicename = member_data.get('user_nicename', '')
            profile_url = f"{self.base_url}/members/{user_nicename}" if user_nicename else None
            
            member = Member(
                name=name,
                title=title,
                company=company,
                email=email or None,
                linkedin=linkedin or None,
                profile_url=profile_url,
                member_type=member_type,
                badges=badges_str
            )
            
            return member
            
        except Exception as e:
            logger.debug(f"Error parsing member: {e}")
            return None
    
    def determine_member_type(self, roles: list) -> str:
        """Determine member type from roles"""
        if not roles:
            return "Standard Member"
        
        # Priority order for member types
        role_priority = {
            'ele_industry_legend': 'Industry Legend',
            'ele_executive': 'Executive',
            'ele_cdo': 'CDO',
            'ele_ambassador': 'Ambassador',
            'ele_producer': 'Producer',
            'contributor': 'Contributor',
            'ele_tmec': 'TMEC',
            'ele_onboarding_buddy': 'Onboarding Buddy',
            'rcp_partner_member': 'Partner Member',
            'rcp_ele_member': 'ELE Member',
            'rcp_online-only_member': 'Online-Only Member',
            'invited': 'Invited',
            'subscriber': 'Subscriber',
            'member': 'Member'
        }
        
        # Find highest priority role
        for role_key, role_name in role_priority.items():
            if role_key in roles:
                return role_name
        
        # If no known role, join all roles
        return ', '.join(roles)

if __name__ == "__main__":
    scraper = ELEMembersJSONScraper()
    members = scraper.scrape_all_members()
    print(f"\n✅ Successfully scraped {len(members)} members!")
    print(f"\nFirst 5 members:")
    for i, member in enumerate(members[:5], 1):
        print(f"  {i}. {member.name}")
        if member.title:
            print(f"     Title: {member.title}")
        if member.company:
            print(f"     Company: {member.company}")
        if member.email:
            print(f"     Email: {member.email}")
        if member.member_type:
            print(f"     Member Type: {member.member_type}")

