from otree.api import *
from os import environ


author = "Sebastian Valet & Johannes D. Walter"

doc = """
a chatGPT interface for oTree that 
"""


# =============================================================================
# CLASSES
# =============================================================================

class C(BaseConstants):

    # Mandatory constants in otree
    NAME_IN_URL = 'Chat'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 2

    MAX_MESSAGES = 10 # Maximum number of user messages
    MAX_CHARACTERS = 500 # Maximum number of characters per message
    SAVE_CHAT_HISTORY = True # Whether to save the chat history in oTree
    
    # API endpoint of AWS edge function; define as environment variable
    API_ENDPOINT = environ.get("AWS_LAMBDA_API_ENDPOINT")


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    
    # If C.SAVE_CHAT_HISTORY is True, make a player attribute for the chat history
    if C.SAVE_CHAT_HISTORY:
        # Chat history
        chat_history = models.LongStringField()


# =============================================================================
# PAGES
# =============================================================================

class chat(Page):

    @staticmethod
    def vars_for_template(player):
        return dict(MAX_CHARACTERS=C.MAX_CHARACTERS)

    @staticmethod
    def js_vars(player):
        return dict(
            MAX_MESSAGES=C.MAX_MESSAGES,
            API_ENDPOINT=C.API_ENDPOINT,
            SAVE_CHAT_HISTORY=C.SAVE_CHAT_HISTORY,
            USER_ID = player.participant.code,
            CHAT_ID = f"{player.participant.code}-{player.round_number}",
            SYSTEM_MESSAGE = chat.get_system_prompt(player),
            INITIAL_ASSISTANT_MESSAGE = chat.get_initial_assistant_message(player),
            INITIAL_USER_MESSAGE = chat.get_initial_user_message(player)
        )
    
    @staticmethod
    def get_system_prompt(player):
        # Generate system prompt. Could include player specific information.
        # For example f"You are playing for {player.payoff}."
        # Set it None if you don't want it.
        system_prompt = """
            Be a helpful assistant. Be brief, concise and use simple language.
        """.strip()
        return system_prompt

    @staticmethod
    def get_initial_assistant_message(player):
        # Generate a static initial assistant message to be shown when the chat
        # is initialized. Could include player info, e.g. f"Hey {player.name}"
        # Set it None if you don't want it.
        initial_assistant_message = """
            Hi! I'm here to help you with your decision.
        """.strip()
        return initial_assistant_message
    
    @staticmethod
    def get_initial_user_message(player):
        # Generate an initial user message; this is for cases when you don't want
        # a hard-coded assistant message to initialize the chat. When initializing
        # a chat, an assistant message is generated based on the user message.
        # Set it None if you don't want it.
        initial_user_message = None
        return initial_user_message

    if C.SAVE_CHAT_HISTORY:
        @staticmethod
        def live_method(player, data):
            if 'chat_history' in data:
                player.chat_history = data['chat_history']


    @staticmethod
    def before_next_page(player, timeout_happened):
        return {}


page_sequence = [
    chat
]
