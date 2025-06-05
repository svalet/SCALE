import time
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'vibe_chats'))
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Type definitions for clarity
ChatMessage = Dict[str, str]
ChatHistory = List[ChatMessage]
ResponseDict = Dict[str, Any]
ErrorDict = Dict[str, str]
OpenAIMessage = Dict[str, str]

# High limit for number of messages per chat; just to prevent misuse
# A malignant user can only sent 100 messages max per chat, and start 20 chats
# Set these limits as low as fits your experiment; set to None if you want no
# restrictions
MAX_MESSAGES_PER_CHAT = 100
MAX_CHATS_PER_USER = 20


def call_openai_api(
    messages: List[OpenAIMessage], 
    model: str = "gpt-4o",
    max_tokens: Optional[int] = 1000
) -> Tuple[Optional[str], Optional[str]]:
    """
    Make a call to the OpenAI API and return the response.
    
    Args:
        messages: List of messages to send to the API
        model: OpenAI model to use
        max_tokens: Maximum number of tokens to generate
    
    Returns:
        Tuple containing:
            - The assistant's response message (or None if error)
            - Error message (or None if successful)
    """
    try:
        start_time = time.time()
        
        # Prepare API call parameters
        params = {
            "model": model,
            "messages": messages
        }
        
        # Add max_tokens if specified
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        # Call OpenAI API
        openai_response = openai_client.chat.completions.create(**params)
        
        logger.info(f"OpenAI API call took {time.time() - start_time:.2f} seconds")
        
        # Extract assistant response
        assistant_message = openai_response.choices[0].message.content
        return assistant_message, None
        
    except Exception as e:
        error_msg = f"Error calling OpenAI API: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def initialize_chat(
    chat_id: str, 
    user_id: str,
    system_message: Optional[str] = None, 
    initial_assistant_message: Optional[str] = None,
    initial_user_message: Optional[str] = None
) -> Union[ResponseDict, ErrorDict]:
    """
    Initialize a new chat session in DynamoDB or return existing one.
    
    Args:
        chat_id: Unique identifier for the chat session
        user_id: Identifier for the user (required)
        system_message: Initial system message to set context
        initial_assistant_message: Hard-coded initial message from the assistant
        initial_user_message: Initial user message that will trigger an API call to get an assistant response
    
    Returns:
        Dictionary containing:
            - chat_id: The chat identifier
            - user_id: The user identifier
            - is_new: Boolean indicating if this is a new session
            - messages: List of chat messages in the session (excluding system messages)
        Or an error dictionary if something goes wrong
    """
    # Check if chat already exists
    existing_chat = table.get_item(Key={'chat_id': chat_id})
    
    if 'Item' in existing_chat:
        logger.info(f"Retrieved existing chat: {chat_id} for user: {user_id}")
        stored_user_id = existing_chat['Item'].get('user_id')
        
        # Verify user_id matches
        if stored_user_id and stored_user_id != user_id:
            logger.warning(f"User ID mismatch: provided {user_id}, stored {stored_user_id}")
            return {'error': 'User ID mismatch'}
        
        # Get all messages excluding system messages
        all_messages = existing_chat['Item'].get('messages', [])
        visible_messages = [msg for msg in all_messages if msg.get('role') != 'system']
        
        return {
            'chat_id': chat_id,
            'user_id': stored_user_id or user_id,  # Use stored if available, otherwise use provided
            'is_new': False,
            'messages': visible_messages
        }

    # Check if user has reached the maximum number of chats
    response = table.scan(
        FilterExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': user_id},
        ProjectionExpression='chat_id'
    )
    user_chat_count = len(response.get('Items', []))
    if MAX_CHATS_PER_USER and user_chat_count >= MAX_CHATS_PER_USER:
        return {'error': f'Maximum number of chats ({MAX_CHATS_PER_USER}) reached for this user.'}
    
    # If not, create a new chat
    timestamp = datetime.now().isoformat()
    
    # Create initial messages list with optional system message
    messages: ChatHistory = []
    if system_message:
        messages.append({
            'role': 'system',
            'content': system_message,
            'timestamp': timestamp
        })
    
    # Add initial assistant message if provided
    # This is for cases when you want to show an initial hard coded assistant
    # message at the beginning of the chat
    if initial_assistant_message:
        messages.append({
            'role': 'assistant',
            'content': initial_assistant_message,
            'timestamp': timestamp
        })
    
    # Process initial user message if provided
    # This is for cases when you want to have an initial user message such that
    # you get a personalized initial assistant message is generated.
    assistant_response = None
    if initial_user_message:
        # Add the user message to the history
        messages.append({
            'role': 'user',
            'content': initial_user_message,
            'timestamp': timestamp
        })
        
        # Get assistant response via API call
        openai_messages = [
            {'role': msg['role'], 'content': msg['content']} for msg in messages
        ]
        assistant_response, error = call_openai_api(openai_messages)
        
        if error:
            return {'error': error}
        
        # Add assistant response to history if it exists
        if assistant_response:
            messages.append({
                'role': 'assistant',
                'content': assistant_response,
                'timestamp': datetime.now().isoformat()
            })
    
    # Prepare the item to store in DynamoDB
    chat_item = {
        'chat_id': chat_id,
        'user_id': user_id,
        'messages': messages,
        'created_at': timestamp,
        'updated_at': timestamp
    }
    
    # Write to DynamoDB
    table.put_item(Item=chat_item)
    
    logger.info(f"Initialized new chat: {chat_id} for user: {user_id}")
    
    # Filter out system messages for the response
    visible_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    return {
        'chat_id': chat_id,
        'user_id': user_id,
        'is_new': True,
        'messages': visible_messages
    }


def add_message_and_get_response(
    chat_id: str,
    user_id: str,
    message: str,
) -> Union[ResponseDict, ErrorDict]:
    """
    Add a message to the chat history and get a response from OpenAI.
    
    Args:
        chat_id: Unique identifier for the chat session
        user_id: Identifier for the user
        message: The message content
        role: The role of the message sender (default: 'user')
        model: OpenAI model to use
        max_tokens: Maximum number of tokens to generate
    
    Returns:
        Dictionary containing:
            - message: The assistant's reply
            - chat_id: The chat identifier
            - user_id: The user identifier
        Or an error dictionary if something goes wrong
    """
    # Get existing chat history
    response = table.get_item(Key={'chat_id': chat_id})
    if 'Item' not in response:
        return {'error': f"Chat session {chat_id} not found"}
    
    # Verify user_id matches
    stored_user_id = response['Item'].get('user_id')
    if stored_user_id and stored_user_id != user_id:
        logger.warning(f"User ID mismatch: provided {user_id}, stored {stored_user_id}")
        return {'error': 'User ID mismatch'}
    
    chat_history = response['Item']
    messages = chat_history.get('messages', [])

    user_message_count = sum(1 for msg in messages if msg.get('role') == 'user')
    if MAX_MESSAGES_PER_CHAT and user_message_count >= MAX_MESSAGES_PER_CHAT:
        return {'error': f'Message limit of {MAX_MESSAGES_PER_CHAT} reached for this chat.'}
    
    # Add new message to history
    timestamp = datetime.now().isoformat()
    new_message = {
        'role': 'user',
        'content': message,
        'timestamp': timestamp
    }
    messages.append(new_message)
    
    # Format messages for OpenAI API
    openai_messages = [
        {'role': msg['role'], 'content': msg['content']} for msg in messages
    ]
    
    # Call OpenAI API using the helper function
    assistant_message, error = call_openai_api(openai_messages)
    
    if error:
        return {'error': error}
    
    # Add assistant response to history
    assistant_entry = {
        'role': 'assistant',
        'content': assistant_message,
        'timestamp': datetime.now().isoformat()
    }
    messages.append(assistant_entry)
    
    # Update DynamoDB
    table.update_item(
        Key={'chat_id': chat_id},
        UpdateExpression="SET messages = :messages, updated_at = :updated_at",
        ExpressionAttributeValues={
            ':messages': messages,
            ':updated_at': datetime.now().isoformat()
        }
    )
    
    return {'message': assistant_message, 
            'chat_id': chat_id, 
            'user_id': user_id}


def get_chat_history(
    chat_id: str,
    user_id: str
) -> Union[ResponseDict, ErrorDict]:
    """
    Retrieve the chat history for a session (including the system messages).
    
    Args:
        chat_id: Unique identifier for the chat session
        user_id: Identifier for the user
    
    Returns:
        Dictionary containing the chat history with messages
        Or an error dictionary if something goes wrong
    """
    response = table.get_item(Key={'chat_id': chat_id})
    if 'Item' not in response:
        return {'error': f"Chat session {chat_id} not found"}
    
    # Verify user_id matches
    stored_user_id = response['Item'].get('user_id')
    if stored_user_id and stored_user_id != user_id:
        logger.warning(f"User ID mismatch: provided {user_id}, stored {stored_user_id}")
        return {'error': 'User ID mismatch'}
    
    return response['Item']
