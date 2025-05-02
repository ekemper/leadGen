import os
import requests
import logging
from server.models.lead import Lead
from server.config.database import db
from typing import Dict, Any
from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session

# Configure logging
logger = logging.getLogger(__name__)

class ApolloService:
    """Service for interacting with the Apollo API."""
    
    def __init__(self):
        """Initialize the Apollo service."""
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        self.base_url = "https://api.apify.com/v2/acts/supreme_coder~apollo-scraper/runs/last/dataset/items"
        
    def fetch_leads(self, params: Dict[str, Any], campaign_id=None) -> Dict[str, Any]:
        """
        Fetch leads from Apollo using the provided parameters and save to the database.
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            # TEMPORARY WORKAROUND: Commenting out actual Apify API call for faster debugging
            # response = requests.get(
            #     self.base_url,
            #     headers=headers,
            #     json=params
            # )
            # response.raise_for_status()
            # data = response.json()
            data = [{
                "id": "66f23f644ef7680001daf5a5",
                "firstName": "Harris",
                "lastName": "Khan",
                "emailAddress": "harris@codment.com",
                "headline": "Co-Founder & COO",
                "linkedInProfileUrl": "http://www.linkedin.com/in/mharriskhan",
                "emailStatus": "verified",
                "profilePictureUrl": None,
                "twitterProfileUrl": None,
                "githubProfileUrl": None,
                "facebookProfileUrl": None,
                "companyId": "61eb9db1dcec7e0001b5fd57",
                "stateName": "New York",
                "cityName": "Bethpage",
                "countryName": "United States",
                "likelyToEngage": False,
                "departmentNames": ["c_suite", "master_information_technology", "master_operations"],
                "subDepartmentNames": ["founder", "operations_executive", "business_service_management_itsm", "operations"],
                "jobSeniority": "founder",
                "jobFunctions": ["operations", "entrepreneurship"],
                "contactPhoneNumbers": [{
                    "rawNumber": "+1 800-927-7118",
                    "sanitizedNumber": "+18009277118",
                    "phoneType": "work_hq",
                    "phonePosition": 0,
                    "phoneStatus": "no_status",
                    "dncStatus": None,
                    "dncOtherInfo": {},
                    "sourceName": "Apollo",
                    "vendorValidationStatuses": []
                }],
                "intentStrength": None,
                "displayIntent": False,
                "catchallEmailDomain": False,
                "companyName": "Codment",
                "rawAddress": "Bethpage, New York, United States",
                "linkedInUserId": None,
                "salesforceUserId": None,
                "creationDate": "2025-03-11T09:27:13.920Z",
                "sourceOfEmail": "crm_csv",
                "lastActiveDate": None,
                "hubspotVisitorId": None,
                "hubspotOrgId": None,
                "cleanedPhoneNumber": "+18009277118",
                "lastUpdatedDate": "2025-03-11T09:27:13.920Z",
                "presenceLevel": "full",
                "customerProvidedEmail": None,
                "emailUnavailableReason": None,
                "verifiedEmailStatus": "Verifying",
                "userTimeZone": "America/New_York",
                "isFreeDomain": False,
                "positionHistory": [],
                "company": {
                    "companyName": "Codment",
                    "websiteUrl": "http://www.codment.com",
                    "blogUrl": None,
                    "angelListProfileUrl": None,
                    "linkedInProfileUrl": "http://www.linkedin.com/company/codment",
                    "twitterProfileUrl": "https://twitter.com/codment",
                    "facebookProfileUrl": "https://www.facebook.com/codment/",
                    "spokenLanguages": [],
                    "alexaRank": None,
                    "contactPhone": "+1 800-927-7118",
                    "linkedInId": "76567882",
                    "yearFounded": None,
                    "stockSymbol": None,
                    "stockExchange": None,
                    "logoUrl": "https://zenprospect-production.s3.amazonaws.com/uploads/pictures/67c6d8bc35e96300019adc9b/picture",
                    "crunchbaseUrl": None,
                    "mainDomain": "codment.com",
                    "cleanedPhone": "+18009277118",
                    "businessIndustry": "information technology & services",
                    "searchKeywords": [
                        "it services & it consulting",
                        "ui/ux design",
                        "web development",
                        "e-commerce solutions",
                        "cms development",
                        "mobile app development",
                        "software development",
                        "blockchain solutions",
                        "quality assurance",
                        "custom web solutions",
                        "responsive design",
                        "full-stack development",
                        "react native apps",
                        "ios app development",
                        "android app development",
                        "wordpress development",
                        "shopify development",
                        "magento development",
                        "opencart development",
                        "bigcommerce solutions",
                        "web technologies",
                        "digital transformation",
                        "user experience",
                        "back-end development",
                        "front-end development",
                        "custom cms solutions",
                        "e-commerce website",
                        "user interface design",
                        "react js development",
                        "laravel development",
                        "vue js development",
                        "content management system",
                        "business automation",
                        "enterprise solutions",
                        "mobile optimization",
                        "agile development",
                        "post-launch support",
                        "web application development",
                        "cross-platform apps",
                        "tech consulting",
                        "performance optimization",
                        "seo-friendly design",
                        "online store development",
                        "bespoke development",
                        "project management",
                        "tech stack integration",
                        "service design",
                        "digital marketing strategy",
                        "maintenance & updates",
                        "information technology & services",
                        "consumer internet",
                        "consumers",
                        "internet",
                        "ux",
                        "productivity"
                    ],
                    "employeeEstimate": 11,
                    "businessIndustries": ["information technology & services"],
                    "additionalIndustries": [],
                    "storeCount": 0,
                    "fullAddress": "1050 old nichols rd islandia, ny 11749 11749 new york, ny, us, new york, new york 11749, us",
                    "addressLine": "1050 Old Nichols Rd",
                    "cityName": "Islandia",
                    "stateName": "New York",
                    "countryName": "United States",
                    "zipCode": "11749-5025",
                    "mainPhone": {
                        "phoneNumber": "+1 800-927-7118",
                        "phoneSource": "Scraped",
                        "cleanedPhoneNumber": "+18009277118"
                    }
                }
            }]

            created_leads = []
            session = db.create_scoped_session()
            try:
                for lead_data in data:
                    # Parse name from firstName and lastName
                    first_name = lead_data.get('firstName', '')
                    last_name = lead_data.get('lastName', '')
                    name = f"{first_name} {last_name}".strip()
                    if not name.strip():
                        name = lead_data.get('name', '')

                    # Parse email from emailAddress
                    email = lead_data.get('emailAddress', '')
                    if not email:
                        # fallback to 'email' or first in 'emails' array
                        email = lead_data.get('email', '')
                        if not email:
                            emails = lead_data.get('emails', [])
                            if isinstance(emails, list) and emails:
                                email = emails[0]

                    # Parse phone (not present in sample, fallback to previous logic)
                    phone = lead_data.get('phone', '')
                    if not phone:
                        phones = lead_data.get('phones', [])
                        if isinstance(phones, list) and phones:
                            phone = phones[0]
                        elif isinstance(lead_data.get('company', ''), dict):
                            main_phone = lead_data['company'].get('mainPhone', {})
                            if isinstance(main_phone, dict):
                                phone = main_phone.get('phoneNumber', '')

                    # Parse company name from company.companyName
                    company_name = ''
                    company_field = lead_data.get('company', '')
                    if isinstance(company_field, dict):
                        company_name = company_field.get('companyName', '')
                    elif isinstance(company_field, str):
                        company_name = company_field

                    lead = Lead(
                        name=name,
                        email=email,
                        company_name=company_name,
                        phone=phone,
                        status=lead_data.get('status', 'new'),
                        source=lead_data.get('source', 'apollo'),
                        notes=lead_data.get('notes', ''),
                        campaign_id=campaign_id,
                        raw_lead_data=lead_data
                    )
                    session.add(lead)
                    created_leads.append(lead)
                session.commit()
            finally:
                session.remove()

            return {
                "status": "success",
                "message": f"{len(created_leads)} leads saved to the database",
                "count": len(created_leads),
                "leads": [l.to_dict() for l in created_leads]
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Apollo leads: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error saving Apollo leads: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            } 