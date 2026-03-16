//---------------------------------------------------------------------------
// CONFIGURATION
//---------------------------------------------------------------------------

const CONFIG = {
    API_ENDPOINT: "https://okvf45wab3.execute-api.eu-central-1.amazonaws.com/Prod/",
    API_SECRET: "tomatoe-ruffle-shoe-slip",
    MAX_MESSAGES: 50,
    MAX_CHARACTERS: 500,
};

//---------------------------------------------------------------------------
// READ YOUGOV ID FROM URL
//---------------------------------------------------------------------------

const urlParams = new URLSearchParams(window.location.search);
const YOUGOV_ID = urlParams.get('participant_label') || urlParams.get('uid') || '';
const OPINION = urlParams.get('opinion') || '';
const CHAT_ID = YOUGOV_ID || 'anonymous-' + Math.random().toString(36).slice(2, 10);
const USER_ID = CHAT_ID;

if (!YOUGOV_ID) {
    console.warn('No participant_label found in URL parameters');
}

//---------------------------------------------------------------------------
// DOM ELEMENTS
//---------------------------------------------------------------------------

const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const scrollingWindow = document.getElementById('scrollingWindow');
const chatMessages = document.getElementById('chatMessages');
const continueButton = document.getElementById('continueButton');
let msgId = 1;
let userMsgCount = 0;

chatInput.setAttribute('maxlength', CONFIG.MAX_CHARACTERS);

//---------------------------------------------------------------------------
// HELPER FUNCTIONS
//---------------------------------------------------------------------------

function toggleChatInput(show = true) {
    if (show) {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    } else {
        chatInput.disabled = true;
        sendButton.disabled = true;
    }
}

function scrollToBottom() {
    var lastElement = scrollingWindow.lastElementChild;
    if (lastElement) {
        lastElement.scrollIntoView({
            behavior: 'smooth', block: 'end', inline: 'start'
        });
    }
}

["copy", "cut", "paste"].forEach(eventType => {
    [scrollingWindow, chatInput].forEach(element => {
        element.addEventListener(eventType, event => {
            event.preventDefault();
        });
    });
});

//---------------------------------------------------------------------------
// CHAT MESSAGE DISPLAY
//---------------------------------------------------------------------------

function appendChatMessage(sender, message) {
    const formattedMessage = message.replace(/\n/g, "<br>");

    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('message-wrapper', sender);

    const messageDiv = document.createElement('div');
    messageDiv.setAttribute('id', `msg${msgId}`);
    messageDiv.classList.add('message', sender);
    messageDiv.innerHTML = formattedMessage;

    messageWrapper.appendChild(messageDiv);
    chatMessages.appendChild(messageWrapper);
    scrollToBottom();

    msgId += 1;
    if (sender === "user") {
        userMsgCount += 1;
    }
}

function appendStatusMessage(message) {
    const statusDiv = document.createElement('div');
    statusDiv.classList.add('alert', 'alert-info', 'mt-3', 'message-wrapper', 'status');
    statusDiv.setAttribute('role', 'alert');
    statusDiv.innerHTML = message;
    chatMessages.appendChild(statusDiv);
    scrollToBottom();
}

//---------------------------------------------------------------------------
// INITIALIZE CHAT ON PAGE LOAD
//---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", function () {
    jQuery.ajax({
        url: CONFIG.API_ENDPOINT,
        timeout: 60000,
        type: "POST",
        data: JSON.stringify({
            api_secret: CONFIG.API_SECRET,
            route: "initialize",
            payload: {
                chat_id: CHAT_ID,
                user_id: USER_ID,
                yougov_id: YOUGOV_ID,
                opinion: OPINION,
                use_server_treatment: true
            }
        }),
        contentType: "application/json",
        dataType: "json",
        success: function (data) {
            data.messages.forEach(message => {
                appendChatMessage(message.role, message.content);
                if (userMsgCount > CONFIG.MAX_MESSAGES) {
                    appendStatusMessage("Maximale Anzahl an Nachrichten erreicht. Bitte klicken Sie auf 'Weiter'.");
                    toggleChatInput(false);
                }
            });
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error("Error details:", {
                status: jqXHR.status,
                statusText: jqXHR.statusText,
                responseText: jqXHR.responseText,
                errorType: textStatus,
                error: errorThrown
            });
            appendStatusMessage(
                "Es gab einen technischen Fehler. Bitte laden Sie die Seite neu."
            );
        }
    });
});

//---------------------------------------------------------------------------
// SEND MESSAGES
//---------------------------------------------------------------------------

sendButton.addEventListener("click", function () {
    sendMessage();
});

chatInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});

function sendMessage() {
    var messageText = chatInput.value.trim();

    if (messageText) {
        chatInput.value = "";
        toggleChatInput(false);
        appendChatMessage("user", messageText);

        jQuery.ajax({
            url: CONFIG.API_ENDPOINT,
            timeout: 60000,
            type: "POST",
            data: JSON.stringify({
                api_secret: CONFIG.API_SECRET,
                route: "chat",
                payload: {
                    chat_id: CHAT_ID,
                    user_id: USER_ID,
                    message: messageText
                }
            }),
            contentType: "application/json",
            dataType: "json",
            success: function (data) {
                var botResponse = data.message.trim();
                appendChatMessage('assistant', botResponse);

                if (userMsgCount >= CONFIG.MAX_MESSAGES) {
                    appendStatusMessage("Maximale Anzahl an Nachrichten erreicht. Bitte klicken Sie auf 'Weiter'.");
                } else {
                    toggleChatInput(true);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.error("Error details:", {
                    status: jqXHR.status,
                    statusText: jqXHR.statusText,
                    responseText: jqXHR.responseText,
                    errorType: textStatus,
                    error: errorThrown
                });
                appendStatusMessage("Es gab einen technischen Fehler. Bitte versuchen Sie es erneut.");
                toggleChatInput(true);
            }
        });
    }
}

//---------------------------------------------------------------------------
// CONTINUE BUTTON
//---------------------------------------------------------------------------

continueButton.addEventListener('click', function (event) {
    event.preventDefault();
    appendStatusMessage("Vielen Dank für Ihre Teilnahme!");
    toggleChatInput(false);
    continueButton.disabled = true;

    // If YouGov provides a redirect/completion URL, uncomment and set it:
    // window.parent.postMessage({status: 'complete', yougov_id: YOUGOV_ID}, '*');
});
