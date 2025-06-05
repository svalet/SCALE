"""
User configuration for Lambda function access control.
Update this list to control which users can access the API from non-localhost origins.
"""

# List of allowed user IDs for non-localhost origins
# Leave empty to allow all users from configured origins
# For otree, use participant.code as the user ID
ALLOWED_USER_IDS = [
    # "user123",
    # "user456", 
    # "user789"
]