from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from server.api.schemas import (
    ErrorSchema, ErrorResponseSchema, SuccessResponseSchema,
    CampaignSchema, CampaignCreateSchema, CampaignStartSchema,
    JobSchema, LeadSchema, AuthSchema, LoginSchema, TokenSchema, UserSchema
)
from apispec.exceptions import DuplicateComponentNameError

def create_spec():
    """Create and configure the OpenAPI specification."""
    spec = APISpec(
        title="Lead Generation API",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
        info={
            "description": "API for managing lead generation campaigns",
            "contact": {
                "name": "API Support",
                "email": "support@example.com"
            }
        }
    )

    # Register schemas
    spec.components.schema("Error", schema=ErrorSchema)
    spec.components.schema("ErrorResponse", schema=ErrorResponseSchema)
    spec.components.schema("SuccessResponse", schema=SuccessResponseSchema)
    spec.components.schema("Campaign", schema=CampaignSchema)
    spec.components.schema("CampaignCreate", schema=CampaignCreateSchema)
    spec.components.schema("CampaignStart", schema=CampaignStartSchema)
    try:
        spec.components.schema("Job", schema=JobSchema)
    except DuplicateComponentNameError:
        pass
    spec.components.schema("Lead", schema=LeadSchema)
    spec.components.schema("Auth", schema=AuthSchema)
    spec.components.schema("Login", schema=LoginSchema)
    spec.components.schema("Token", schema=TokenSchema)
    spec.components.schema("User", schema=UserSchema)

    # Security schemes
    spec.components.security_scheme(
        "bearerAuth",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    )

    # Global security requirement
    spec.options = {
        "security": [{"bearerAuth": []}]
    }

    return spec

def register_spec(app, spec):
    """Register the OpenAPI specification with the Flask app."""
    @app.route("/api/spec.json")
    def get_spec():
        return spec.to_dict()

    @app.route("/api/docs")
    def get_docs():
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Documentation</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body {
                    margin: 0;
                    padding: 0;
                }
            </style>
        </head>
        <body>
            <redoc spec-url="/api/spec.json"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"> </script>
        </body>
        </html>
        """ 