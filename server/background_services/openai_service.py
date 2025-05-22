import os
from openai import OpenAI
from typing import Dict, Any, Optional
from server.utils.logging_config import setup_logger, ContextLogger

# Configure module logger
logger = setup_logger('openai_service')

class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self):
        """Initialize the OpenAI service."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI()  # Use default client initialization
        self.logger = logger

    def generate_email_copy(self, lead, enrichment_result):
        """Generate personalized email copy for a lead."""
        with ContextLogger(self.logger, lead_id=lead.id):
            try:
                # Extract relevant information
                first_name = lead.first_name or ''
                last_name = lead.last_name or ''
                company = lead.company or ''
                title = lead.title or ''
                
                # Build prompt
                prompt = f"""
                Write a personalized email to {first_name} {last_name}, who works as {title} at {company}.
                
                Use the following enrichment data to personalize the message:
                {enrichment_result}
                
                The email should:
                1. Be concise (2-3 short paragraphs)
                2. Reference specific details from their background
                3. Have a clear call to action
                4. Be professional but conversational
                5. Focus on value proposition
                """
                
                self.logger.info("Generating email copy", extra={
                    'metadata': {
                        'lead_id': lead.id,
                        'first_name': first_name,
                        'company': company
                    }
                })
                
                response = self.client.chat.completions.create(
                    model="gpt-4",  # Revert to original model
                    messages=[
                        {"role": "system", "content": "You are an expert at writing personalized sales emails that get responses."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                self.logger.info("Successfully generated email copy")
                return response
                
            except Exception as e:
                self.logger.error(f"Error generating email copy: {str(e)}", exc_info=True)
                raise 