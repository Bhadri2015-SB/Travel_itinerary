const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
let threadId = ""; // Session handling

// Function to send user message
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Add user message to chat UI
    addMessage(message, "user");

    // API call to FastAPI
    const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, message: message }),
    });

    const data = await response.json();
    threadId = data.thread_id; // Store session ID
    addMessage(data.response, "bot");

    userInput.value = "";
}

// Function to display messages in the chat UI
function addMessage(text, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");
    messageDiv.textContent = text;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll
}

// Enter key to send message
userInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});
