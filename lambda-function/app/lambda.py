import json
import logging
import os
from main import (
    initialize_chat, 
    add_message_and_get_response, 
    get_chat_history
)
from user_config import ALLOWED_USER_IDS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_allowed = {'http://localhost:8000'}
prod = os.getenv('ALLOWED_PROD_ORIGIN', '').rstrip('/')

wildcard = (prod == '*')
if prod and prod != '*':
    _allowed.add(prod)

def _is_allowed_origin(origin):
    # Check if the origin starts with any of our allowed domains
    return any(origin.startswith(allowed) for allowed in _allowed)

def _cors_headers(origin):
    return {
        'Access-Control-Allow-Origin': '*' if wildcard else origin,
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
    }

def handler(event, context):
    """
    Lambda handler function to process API Gateway events.
    
    Routes:
    - initialize: Create a new chat session
    - chat: Add a message and get a response
    - history: Get chat history
    
    Args:
        event: API Gateway event
        context: Lambda context
    
    Returns:
        dict: API Gateway response
    """
    
    headers = event.get('headers', {})
    origin = (headers.get('Origin') or headers.get('origin') or '').rstrip('/')
 
    if not _is_allowed_origin(origin):
        # no CORS headers on 403 forces browser to block
        logger.warning(f"Origin '{origin}' not allowed")
        return {'statusCode': 403, 'body': json.dumps({'error': 'Origin not allowed'})}

    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': _cors_headers(origin),
            'body': json.dumps({'message': 'CORS preflight successful'})
        }

    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        route = body.get('route')
        payload = body.get('payload', {})

        # Add debug logging
        logger.info(f"Received request with route: {route}")
        logger.info(f"Payload: {payload}")
        
        # Validate common required parameters
        missing = [k for k in ('user_id','chat_id') if k not in payload]
        if missing:
            return {
                'statusCode': 400,
                'headers': _cors_headers(origin),
                'body': json.dumps({'error': f"Missing: {', '.join(missing)}"})
            }
        
        # Allow all user_ids if origin is localhost, else allow specific user_ids
        # optional user check
        user_id = payload['user_id']
        if origin != 'http://localhost:8000' and ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            return {
                'statusCode': 403, 
                'body': json.dumps({'error': 'User not allowed'})
            }

        # Route the request
        if route == 'initialize':
            result = initialize_chat(
                chat_id=payload['chat_id'],
                user_id=payload['user_id'],
                system_message=payload.get('system_message'),
                initial_assistant_message=payload.get('initial_assistant_message'),
                initial_user_message=payload.get('initial_user_message')
            )

        elif route == 'chat':
            if 'message' not in payload:
                raise ValueError('message is required')
            result = add_message_and_get_response(
                chat_id=payload['chat_id'],
                user_id=payload['user_id'],
                message=payload['message']
            )

        elif route == 'history':
            result = get_chat_history(
                chat_id=payload['chat_id'],
                user_id=payload['user_id']
            )
        
        else:
            result = {'error': 'Invalid route specified'}
        
        return {
            'statusCode': 200 if 'error' not in result else 400,
            'headers': _cors_headers(origin),
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': _cors_headers(origin),
            'body': json.dumps({'error': str(e)})
        }