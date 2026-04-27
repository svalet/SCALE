import time
import os
import logging
import random
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

STYLE_INSTRUCTIONS = (
    "Antworte in der Sprache, die dein Gesprächspartner benutzt. "
    "Wenn dein Gesprächspartner Deutsch schreibt, antworte auf Deutsch. "
    "Wenn dein Gesprächspartner Englisch oder eine andere Sprache schreibt, "
    "antworte in dieser Sprache. Das Thema bleibt aber immer Einwanderung "
    "nach Deutschland bzw. Wetter in Deutschland. "
    "Verwende einfache, klare Sprache. Antworte in 4-6 Sätzen pro Nachricht. "
    "Sei freundlich und respektvoll. Lüge nicht und erfinde keine Fakten. "
    "Stelle am Ende deiner Antwort eine Frage, um das Gespräch am Laufen zu halten. "
    "Beziehe dich auf das, was dein Gesprächspartner gesagt hat."
)

OPINION_SCALE = {
    '1': 'stark gegen Einwanderung (will keine Einwanderer)',
    '2': 'deutlich gegen Einwanderung',
    '3': 'eher gegen Einwanderung',
    '4': 'neutral / unentschieden',
    '5': 'eher für Einwanderung',
    '6': 'deutlich für Einwanderung',
    '7': 'stark für offene Grenzen (will so viele Einwanderer wie möglich)',
}

CONTROL_PROMPT = (
    "Du bist ein Gesprächsbot zum Thema Wetter, Klima und Jahreszeiten "
    "in Deutschland. Führe ein persönliches, lebhaftes Gespräch. "
    "Mögliche Themen: Wie das Wetter die Stimmung und den Alltag beeinflusst, "
    "Erinnerungen an besondere Wetterereignisse (z.B. Hitzesommer, Schneechaos, "
    "Unwetter), Lieblingsjahreszeiten und warum, Outdoor-Aktivitäten und Hobbys "
    "die vom Wetter abhängen, Urlaubserlebnisse mit besonderem Wetter, "
    "wie sich das Wetter in Deutschland über die Jahre verändert hat, "
    "und regionale Wetterunterschiede (Küste vs. Berge vs. Flachland). "
    "Teile eigene Beobachtungen und interessante Fakten, um das Gespräch "
    "lebendig zu machen. Verknüpfe Wetterthemen mit dem persönlichen "
    "Erleben deines Gesprächspartners. "
    "Vermeide politische Themen, insbesondere Einwanderung. "
    "Beginne das Gespräch auf Deutsch, indem du fragst, wie das Wetter gerade "
    "bei deinem Gesprächspartner ist und ob er oder sie eine "
    "Lieblingsjahreszeit hat. "
    + STYLE_INSTRUCTIONS
)


def get_treatment_prompt(opinion: Optional[str] = None) -> str:
    base = (
        "Du bist ein überzeugender Gesprächsbot zum Thema Einwanderung nach "
        "Deutschland. Dein Ziel ist es, deinen Gesprächspartner davon zu "
        "überzeugen, dass eine ausgewogene, differenzierte Haltung zur "
        "Einwanderung die vernünftigste Position ist. Weder extreme Ablehnung "
        "noch bedingungslose Offenheit sind realistisch oder wünschenswert. "
        "Sei dabei hartnäckig und überzeugend — gib dich nicht mit "
        "oberflächlichen Antworten zufrieden, sondern hake nach und "
        "konfrontiere deinen Gesprächspartner mit starken Gegenargumenten. "
    )

    opinion_label = OPINION_SCALE.get(opinion, '') if opinion else ''

    if opinion and opinion_label:
        base += (
            f"Dein Gesprächspartner hat vorab angegeben, dass er/sie "
            f"'{opinion_label}' ist (Wert {opinion} auf einer 7er-Skala). "
            f"Erwähne diese Skala oder diesen Wert nicht im Gespräch. "
        )

        opinion_int = int(opinion)
        if opinion_int <= 2:
            base += (
                "Diese Person ist stark gegen Einwanderung. Sei direkt und "
                "konfrontativ (aber respektvoll). Nutze die stärksten "
                "verfügbaren Argumente FÜR Einwanderung. "
                "Zeige auf, dass die Ängste zwar verständlich sind, aber "
                "die Realität differenzierter ist als pauschale Ablehnung. "
                "Fordere die Person heraus, konkrete Beispiele für ihre "
                "Befürchtungen zu nennen, und entkräfte sie sachlich. "
            )
        elif opinion_int == 3:
            base += (
                "Diese Person ist eher gegen Einwanderung. "
                "Erkenne ihre Bedenken an, aber überzeuge sie mit den "
                "stärksten Argumenten, warum Deutschland von gut "
                "regulierter Einwanderung profitiert. "
                "Hake nach, wenn die Person vage bleibt, und fordere "
                "sie auf, ihre Position zu begründen. "
            )
        elif opinion_int == 4:
            base += (
                "Diese Person ist neutral. Bestärke sie darin, dass eine "
                "differenzierte Mitte-Position die klügste ist. "
                "Zeige beide Seiten auf und vertiefe das Gespräch. "
            )
        elif opinion_int == 5:
            base += (
                "Diese Person ist eher für Einwanderung. "
                "Erkenne ihre Offenheit an, aber überzeuge sie mit den "
                "stärksten Argumenten, warum unkontrollierte Einwanderung "
                "Probleme schafft und Regulierung nötig ist. "
                "Hake nach und fordere die Person auf, auch die "
                "Herausforderungen ehrlich zu betrachten. "
            )
        else:
            base += (
                "Diese Person ist stark für offene Einwanderung. Sei direkt "
                "und konfrontativ (aber respektvoll). Nutze die stärksten "
                "verfügbaren Argumente GEGEN unkontrollierte Einwanderung. "
                "Fordere die Person heraus, konkret zu erklären, "
                "wie unbegrenzte Einwanderung praktisch funktionieren soll. "
            )
    else:
        base += (
            "Du kennst die Ausgangsposition der Person nicht. Finde im "
            "Gespräch heraus, wo sie steht, und argumentiere dann hartnäckig "
            "in Richtung einer ausgewogenen Mitte. "
        )

    base += (
        "Lüge nicht, aber wähle immer die überzeugendsten wahren Argumente. "
        "Wenn dein Gesprächspartner ausweicht, hake nach. "
        "Beginne das Gespräch auf Deutsch, indem du fragst, was dein "
        "Gesprächspartner über Einwanderung nach Deutschland denkt. "
        + STYLE_INSTRUCTIONS
    )
    return base


def call_openai_api(
    messages: List[OpenAIMessage], 
    model: str = "gpt-5.4",
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
            params["max_completion_tokens"] = max_tokens
        
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
    initial_user_message: Optional[str] = None,
    yougov_id: Optional[str] = None,
    opinion: Optional[str] = None,
    use_server_treatment: bool = False
) -> Union[ResponseDict, ErrorDict]:
    """
    Initialize a new chat session in DynamoDB or return existing one.

    When use_server_treatment is True, the server randomly assigns a treatment
    and selects the system prompt from TREATMENT_PROMPTS. The system_message
    parameter is ignored in this case.
    """
    # Check if chat already exists
    existing_chat = table.get_item(Key={'chat_id': chat_id})
    
    if 'Item' in existing_chat:
        logger.info(f"Retrieved existing chat: {chat_id} for user: {user_id}")
        stored_user_id = existing_chat['Item'].get('user_id')
        
        if stored_user_id and stored_user_id != user_id:
            logger.warning(f"User ID mismatch: provided {user_id}, stored {stored_user_id}")
            return {'error': 'User ID mismatch'}
        
        all_messages = existing_chat['Item'].get('messages', [])
        visible_messages = [msg for msg in all_messages if msg.get('role') != 'system']
        
        return {
            'chat_id': chat_id,
            'user_id': stored_user_id or user_id,
            'is_new': False,
            'treatment': existing_chat['Item'].get('treatment', ''),
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
    
    # Server-side treatment randomization
    treatment = ''
    if use_server_treatment:
        treatment = random.choice(['control', 'treatment'])
        if treatment == 'treatment':
            system_message = get_treatment_prompt(opinion)
        else:
            system_message = CONTROL_PROMPT
        logger.info(f"Assigned treatment '{treatment}' for chat: {chat_id}")

    timestamp = datetime.now().isoformat()
    
    messages: ChatHistory = []
    if system_message:
        messages.append({
            'role': 'system',
            'content': system_message,
            'timestamp': timestamp
        })
    
    if initial_assistant_message:
        messages.append({
            'role': 'assistant',
            'content': initial_assistant_message,
            'timestamp': timestamp
        })
    
    assistant_response = None
    if initial_user_message:
        messages.append({
            'role': 'user',
            'content': initial_user_message,
            'timestamp': timestamp
        })
        
        openai_messages = [
            {'role': msg['role'], 'content': msg['content']} for msg in messages
        ]
        assistant_response, error = call_openai_api(openai_messages)
        
        if error:
            return {'error': error}
        
        if assistant_response:
            messages.append({
                'role': 'assistant',
                'content': assistant_response,
                'timestamp': datetime.now().isoformat()
            })
    
    # When using server treatment and no other initial message was set,
    # generate an AI opening message from the system prompt alone
    if use_server_treatment and not initial_assistant_message and not initial_user_message:
        openai_messages = [
            {'role': msg['role'], 'content': msg['content']} for msg in messages
        ]
        first_message, error = call_openai_api(openai_messages)
        
        if error:
            return {'error': error}
        
        if first_message:
            messages.append({
                'role': 'assistant',
                'content': first_message,
                'timestamp': datetime.now().isoformat()
            })
    
    chat_item = {
        'chat_id': chat_id,
        'user_id': user_id,
        'messages': messages,
        'created_at': timestamp,
        'updated_at': timestamp
    }
    if treatment:
        chat_item['treatment'] = treatment
    if yougov_id:
        chat_item['yougov_id'] = yougov_id
    if opinion:
        chat_item['opinion'] = opinion
    
    table.put_item(Item=chat_item)
    
    logger.info(f"Initialized new chat: {chat_id} for user: {user_id}")
    
    visible_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    return {
        'chat_id': chat_id,
        'user_id': user_id,
        'is_new': True,
        'treatment': treatment,
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
