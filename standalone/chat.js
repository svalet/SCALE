//---------------------------------------------------------------------------
// CONFIGURATION
//---------------------------------------------------------------------------

const CONFIG = {
  API_ENDPOINT:
    "https://okvf45wab3.execute-api.eu-central-1.amazonaws.com/Prod/",
  API_SECRET: "tomatoe-ruffle-shoe-slip",
  MAX_MESSAGES: 50,
  MAX_CHARACTERS: 500,
};

//---------------------------------------------------------------------------
// READ YOUGOV ID FROM URL
//---------------------------------------------------------------------------

const urlParams = new URLSearchParams(window.location.search);
const YOUGOV_ID =
  urlParams.get("participant_label") || urlParams.get("uid") || "";
const OPINION = urlParams.get("opinion") || "";
const CHAT_ID =
  YOUGOV_ID || "anonymous-" + Math.random().toString(36).slice(2, 10);
const USER_ID = CHAT_ID;

if (!YOUGOV_ID) {
  console.warn("No participant_label found in URL parameters");
}

//---------------------------------------------------------------------------
// DOM ELEMENTS
//---------------------------------------------------------------------------

const chatInput = document.getElementById("chatInput");
const sendButton = document.getElementById("sendButton");
const scrollingWindow = document.getElementById("scrollingWindow");
const chatMessages = document.getElementById("chatMessages");
let msgId = 1;
let userMsgCount = 0;

chatInput.setAttribute("maxlength", CONFIG.MAX_CHARACTERS);

const typingIndicator = document.getElementById("typingIndicator");

let typingDotsAnimFrame = null;

function stopTypingDotsAnimation() {
  if (typingDotsAnimFrame !== null) {
    cancelAnimationFrame(typingDotsAnimFrame);
    typingDotsAnimFrame = null;
  }
  typingIndicator.querySelectorAll(".typing-bubble-dot").forEach((dot) => {
    dot.style.transform = "";
    dot.style.opacity = "";
  });
}

function typingDotsTick(now) {
  if (!typingIndicator.classList.contains("is-active")) {
    typingDotsAnimFrame = null;
    return;
  }
  typingDotsAnimFrame = requestAnimationFrame(typingDotsTick);
  const t = now / 1000;
  typingIndicator.querySelectorAll(".typing-bubble-dot").forEach((dot, i) => {
    const phase = t * Math.PI * 2 * 1.15 + i * 0.9;
    const lift = Math.max(0, Math.sin(phase));
    dot.style.transform = `translateY(${-8 * lift}px)`;
    dot.style.opacity = String(0.32 + 0.68 * lift);
  });
}

function startTypingDotsAnimation() {
  stopTypingDotsAnimation();
  typingDotsAnimFrame = requestAnimationFrame(typingDotsTick);
}

//---------------------------------------------------------------------------
// HELPER FUNCTIONS
//---------------------------------------------------------------------------

/** @param {"idle" | "waiting_ai" | "locked"} state */
function setInputState(state) {
  const enabled = state === "idle";
  const showTyping = state === "waiting_ai";

  chatInput.disabled = !enabled;
  sendButton.disabled = !enabled;

  if (showTyping) {
    typingIndicator.classList.add("is-active");
    typingIndicator.setAttribute("aria-hidden", "false");
    startTypingDotsAnimation();
  } else {
    stopTypingDotsAnimation();
    typingIndicator.classList.remove("is-active");
    typingIndicator.setAttribute("aria-hidden", "true");
  }

  if (enabled) {
    chatInput.focus();
  }

  if (showTyping) {
    scrollToBottom();
  }
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    scrollingWindow.scrollTop = scrollingWindow.scrollHeight;
  });
}

["copy", "cut", "paste"].forEach((eventType) => {
  [scrollingWindow, chatInput].forEach((element) => {
    element.addEventListener(eventType, (event) => {
      event.preventDefault();
    });
  });
});

//---------------------------------------------------------------------------
// CHAT MESSAGE DISPLAY
//---------------------------------------------------------------------------

function appendChatMessage(sender, message) {
  const formattedMessage = message.replace(/\n/g, "<br>");

  const messageWrapper = document.createElement("div");
  messageWrapper.classList.add("message-wrapper", sender);

  const messageDiv = document.createElement("div");
  messageDiv.setAttribute("id", `msg${msgId}`);
  messageDiv.classList.add("message", sender);
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
  const statusDiv = document.createElement("div");
  statusDiv.classList.add(
    "alert",
    "alert-info",
    "mt-3",
    "message-wrapper",
    "status",
  );
  statusDiv.setAttribute("role", "alert");
  statusDiv.innerHTML = message;
  chatMessages.appendChild(statusDiv);
  scrollToBottom();
}

//---------------------------------------------------------------------------
// INITIALIZE CHAT ON PAGE LOAD
//---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", function () {
  setInputState("waiting_ai");

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
        use_server_treatment: true,
      },
    }),
    contentType: "application/json",
    dataType: "json",
    success: function (data) {
      let hitMax = false;
      data.messages.forEach((message) => {
        appendChatMessage(message.role, message.content);
        if (userMsgCount > CONFIG.MAX_MESSAGES) {
          hitMax = true;
        }
      });
      if (hitMax) {
        appendStatusMessage(
          "Maximale Anzahl an Nachrichten erreicht. Vielen Dank für Ihre Teilnahme!",
        );
        setInputState("locked");
      } else {
        setInputState("idle");
      }
    },
    error: function (jqXHR, textStatus, errorThrown) {
      console.error("Error details:", {
        status: jqXHR.status,
        statusText: jqXHR.statusText,
        responseText: jqXHR.responseText,
        errorType: textStatus,
        error: errorThrown,
      });
      appendStatusMessage(
        "Es gab einen technischen Fehler. Bitte laden Sie die Seite neu.",
      );
      setInputState("idle");
    },
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

  if (messageText && !chatInput.disabled) {
    chatInput.value = "";
    setInputState("waiting_ai");
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
          message: messageText,
        },
      }),
      contentType: "application/json",
      dataType: "json",
      success: function (data) {
        var botResponse = data.message.trim();
        appendChatMessage("assistant", botResponse);

        if (userMsgCount >= CONFIG.MAX_MESSAGES) {
          appendStatusMessage(
            "Maximale Anzahl an Nachrichten erreicht. Vielen Dank für Ihre Teilnahme!",
          );
          setInputState("locked");
        } else {
          setInputState("idle");
        }
      },
      error: function (jqXHR, textStatus, errorThrown) {
        console.error("Error details:", {
          status: jqXHR.status,
          statusText: jqXHR.statusText,
          responseText: jqXHR.responseText,
          errorType: textStatus,
          error: errorThrown,
        });
        appendStatusMessage(
          "Es gab einen technischen Fehler. Bitte versuchen Sie es erneut.",
        );
        setInputState("idle");
      },
    });
  }
}
