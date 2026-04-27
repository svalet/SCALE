from otree.api import *
from os import environ
import random


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

    MAX_MESSAGES = 50 # Maximum number of user messages
    MAX_CHARACTERS = 500 # Maximum number of characters per message
    SAVE_CHAT_HISTORY = True # Whether to save the chat history in oTree
    
    # API endpoint of AWS edge function; define as environment variable
    # API_ENDPOINT = environ.get("AWS_LAMBDA_API_ENDPOINT")
    API_ENDPOINT = "https://okvf45wab3.execute-api.eu-central-1.amazonaws.com/Prod/"


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    
    yougov_id = models.StringField(blank=True)
    treatment = models.StringField(blank=True)

    if C.SAVE_CHAT_HISTORY:
        chat_history = models.LongStringField()


# =============================================================================
# PAGES
# =============================================================================

class chat(Page):

    @staticmethod
    def vars_for_template(player):
        if player.round_number == 1:
            player.participant.yougov_id = player.participant.label or ''
            player.participant.treatment = random.choice(['control', 'treatment'])
        player.yougov_id = player.participant.yougov_id
        player.treatment = player.participant.treatment
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
        style_instructions = (
            "Antworte immer auf Deutsch. "
            "Verwende einfache, klare Sprache. Halte dich kurz (2-4 Sätze pro Antwort). "
            "Sei freundlich und respektvoll. Lüge nicht und erfinde keine Fakten. "
            "Stelle Fragen, um das Gespräch am Laufen zu halten. "
            "Beziehe dich auf das, was dein Gesprächspartner gesagt hat."
        )

        if player.participant.treatment == 'treatment':
            system_prompt = (
                "Du bist ein Gesprächsbot zum Thema Einwanderung nach Deutschland. "
                "Dein Ziel ist es, deinen Gesprächspartner zu einer moderateren "
                "Position zu bewegen — egal ob die Person eher für oder gegen "
                "Einwanderung ist. Wenn die Person sehr gegen Einwanderung ist, "
                "bringe die stärksten Argumente für die Vorteile von Einwanderung "
                "(z.B. Fachkräftemangel, demographischer Wandel, wirtschaftliche "
                "Beiträge, kulturelle Bereicherung). Wenn die Person sehr für "
                "offene Grenzen ist, bringe die stärksten Argumente für eine "
                "regulierte Einwanderung (z.B. Integrationskapazitäten, "
                "Belastung von Kommunen, gesellschaftlicher Zusammenhalt). "
                "Sei dabei immer fair und ehrlich. Erkenne berechtigte Sorgen "
                "deines Gesprächspartners an, bevor du Gegenargumente bringst. "
                "Beginne das Gespräch, indem du fragst, was dein Gesprächspartner "
                "über Einwanderung nach Deutschland denkt. "
                + style_instructions
            )
        else:
            system_prompt = (
                "Du bist ein Gesprächsbot zum Thema Wetter und Klima in Deutschland. "
                "Unterhalte dich mit deinem Gesprächspartner über Wetterthemen — "
                "zum Beispiel Lieblingsjahreszeiten, Wetterextreme, regionale "
                "Wetterunterschiede in Deutschland, Urlaubswetter, oder wie das "
                "Wetter den Alltag beeinflusst. Sei neugierig und stelle Fragen. "
                "Teile interessante Fakten über das Wetter, wenn es passt. "
                "Vermeide politische Themen, insbesondere Einwanderung. "
                "Beginne das Gespräch, indem du fragst, wie das Wetter gerade "
                "bei deinem Gesprächspartner ist. "
                + style_instructions
            )
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
