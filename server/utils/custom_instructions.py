{
  "id": "error-message-consistency",
  "description": "Ensure consistent error message handling across the application by using centralized error message constants.",
  "rules": [
    {
      "id": "error-message-centralization",
      "description": "All error messages must be defined as constants in the error_messages.py file and organized by module/feature.",
      "severity": "error"
    },
    {
      "id": "error-message-formatting",
      "description": "Error messages that require variable interpolation must use string formatting with named parameters.",
      "severity": "error"
    },
    {
      "id": "error-message-reuse",
      "description": "Error messages must be reused across application code and tests to ensure consistency in error handling.",
      "severity": "error"
    },
    {
      "id": "error-message-logging",
      "description": "Error messages must be logged before being raised as exceptions, using the same message string.",
      "severity": "error"
    },
    {
      "id": "error-message-testing",
      "description": "Tests must import and use error message constants to validate error handling.",
      "severity": "error"
    }
  ]
} 