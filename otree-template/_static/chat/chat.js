//---------------------------------------------------------------------------
// CONSTANTS FROM DOM //
//---------------------------------------------------------------------------

const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const scrollingWindow = document.getElementById('scrollingWindow');
const chatMessages = document.getElementById('chatMessages');
const continueButton = document.getElementById('continueButton');
let msgId = 1;
let userMsgCount = 0


// --------------------------------------------------------------------------
// HELPER FUNCTIONS
// --------------------------------------------------------------------------

// Function for toggling chat input
function toggleChatInput(show = true) {
    if (show) {
        chatInput.disabled = false;
        sendButton.disabled = false;
    } else {
        chatInput.disabled = true;
        sendButton.disabled = true;
    };
}


// Function for scrolling to bottom
function scrollToBottom() {
    var lastElement = scrollingWindow.lastElementChild;
    if (lastElement) {
        lastElement.scrollIntoView({ 
            behavior: 'smooth', block: 'end', inline: 'start'
        });
    }
}

// Prevent copy, cut, and paste in scrollingWindow and chatInput
["copy", "cut", "paste"].forEach(eventType => {
    [scrollingWindow, chatInput].forEach(element => {
        element.addEventListener(eventType, event => {
            event.preventDefault();
        });
    });
});


// --------------------------------------------------------------------------
// FUNCTIONS TO UPDATE CHAT WINDOW  //
// --------------------------------------------------------------------------

// Function for appending chat messages
function appendChatMessage(sender, message) {
    
    // Replace newline characters with HTML <br> elements
    const formattedMessage = message.replace(/\n/g, "<br>");

    // Create main message wrapper
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('message-wrapper', sender);

    // Create main message container
    const messageDiv = document.createElement('div');
    messageDiv.setAttribute('id', `msg${msgId}`);
    messageDiv.classList.add('message', sender);

    // Set message text directly
    messageDiv.innerHTML = formattedMessage;

    // Add message to wrapper
    messageWrapper.appendChild(messageDiv);

    // Add to chat window
    chatMessages.appendChild(messageWrapper);
    scrollToBottom();

    // Increment the global msgId and user message count
    msgId += 1;
    if (sender === "user") {
        userMsgCount += 1;
    }
}

// Function for appending status messages
function appendStatusMessage(message) {
    // Create a new div element for the status message
    const statusDiv = document.createElement('div');
    statusDiv.classList.add('alert', 'alert-info', 'mt-3', 'message-wrapper', 'status');
    statusDiv.setAttribute('role', 'alert');
    statusDiv.innerHTML = message;

    // Append the status message to the chat messages area
    chatMessages.appendChild(statusDiv);
    scrollToBottom();
}


// --------------------------------------------------------------------------
// INITIALIZE OR LOAD CHAT ON PAGE LOAD //
// --------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", function (event) {
    jQuery.ajax({
        url: js_vars.API_ENDPOINT,
        timeout: 60000,
        type: "POST",
        data: JSON.stringify({
            route: "initialize",
            payload: {
                chat_id: js_vars.CHAT_ID, 
                user_id: js_vars.USER_ID,
                system_message: js_vars.SYSTEM_MESSAGE ,
                initial_assistant_message: js_vars.INITIAL_ASSISTANT_MESSAGE,
                initial_user_message: js_vars.INITIAL_USER_MESSAGE
            }
        }),
        contentType: "application/json",
        dataType: "json",
        success: function (data) {
            // Process each message in the messages array
            data.messages.forEach(message => {
                appendChatMessage(message.role, message.content);
                if (userMsgCount > js_vars.MAX_MESSAGES) {
                    appendStatusMessage("Maximum number of messages reached. Please proceed to make your choices");
                    toggleChatInput(show = false);
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
                "There was a technical error. Please refresh the page or proceed in the survey."
            );
        }
    });
});


//---------------------------------------------------------------------------
// FUNCTIONS TO SEND MESSAGES AND RECEIVE RESPONSE //
//---------------------------------------------------------------------------

// Send message on submit button click
sendButton.addEventListener("click", function () {
    sendMessage();
});

// Send message on Enter key
chatInput.addEventListener("keydown", function (event) {
if (event.key === "Enter") {
    event.preventDefault(); // Prevent form submission
    sendMessage();
    }
});

// Function for sending messages
function sendMessage() {

    var messageText = chatInput.value.trim();

    if (messageText) {
        // Clear the input field
        chatInput.value = "";

        // Deactivate chatInput and button until chatbot replies
        toggleChatInput(show = false);

        // Add user message to area
        appendChatMessage("user", messageText);   
        
        // Get bot response
        jQuery.ajax({
            url: js_vars.API_ENDPOINT,
            timeout: 60000,
            type: "POST",
            data: JSON.stringify({
                route: "chat",
                payload: {
                    chat_id: js_vars.CHAT_ID,
                    user_id: js_vars.USER_ID,
                    message: messageText
                }
            }),
            contentType: "application/json",
            dataType: "json",
            success: function (data) {
                
                // Add bot response to chat
                var botResponse = data.message.trim();
                appendChatMessage('assistant', botResponse);

                // Check if maximum number of messages has been reached
                // We only count user messages
                if (userMsgCount >= js_vars.MAX_MESSAGES) {
                    appendStatusMessage("Maximum number of messages reached. Please proceed to make your choices");
                } else {
                    toggleChatInput(show = true);
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
                appendStatusMessage("There was a technical error. Please try again.");
                toggleChatInput(show = true);
            }
        });
    }
}


//---------------------------------------------------------------------------
// GET CHAT HISTORY //
//---------------------------------------------------------------------------

continueButton.addEventListener('click', function (event) {
    event.preventDefault(); // Prevent form submission

    if (js_vars.SAVE_CHAT_HISTORY) {
        // Get chat history from database
        jQuery.ajax({
            url: js_vars.API_ENDPOINT,
            timeout: 60000,
            type: "POST",
            data: JSON.stringify({
                route: "history",
                payload: {
                    chat_id: js_vars.CHAT_ID,
                    user_id: js_vars.USER_ID
                }
            }),
            contentType: "application/json",
            dataType: "json",
            success: function (data) {
                console.log(data);
                // Send the chat history to oTree
                liveSend({
                    'chat_history': JSON.stringify(data.messages)
                });
            },
            error: function (jqXHR, textStatus, errorThrown) {
                error_message = {
                    status: jqXHR.status,
                    statusText: jqXHR.statusText,
                    responseText: jqXHR.responseText,
                    errorType: textStatus,
                    error: errorThrown
                }
                console.log("Error details:", error_message);
                
                // If error, send the error message to oTree 
                liveSend({
                    'chat_history': JSON.stringify(error_message)
                })
            },
            complete: function () {
                // Submit the form after attempting to send chat history
                document.forms[0].submit();
            }
        });
    } else {
        // Directly submit the form if SAVE_CHAT_HISTORY is false
        document.forms[0].submit();
    }
});
