
const chatToggle = document.getElementById("chat-toggle");
const chatPanel = document.getElementById("chat-panel");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");

if (!chatToggle || !chatPanel || !chatForm || !chatInput || !chatMessages) {
    console.error("EmployeeHub chatbot HTML elements are missing.");
} else {
    chatToggle.addEventListener("click", () => {
        chatPanel.hidden = !chatPanel.hidden;

        if (!chatPanel.hidden) {
            chatInput.focus();
        }
    });

    function addMessage(sender, text, sources = []) {
        const message = document.createElement("div");
        message.className = `chat-message ${sender}`;

        const paragraph = document.createElement("p");
        paragraph.textContent = text;
        message.appendChild(paragraph);

        if (sources.length > 0) {
            const sourceElement = document.createElement("small");
            sourceElement.textContent =
                "Sources: " +
                sources.map(source =>
                    typeof source === "string"
                        ? source
                        : source.source || source.title || "Document"
                ).join(", ");

            message.appendChild(sourceElement);
        }

        chatMessages.appendChild(message);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return message;
    }

    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const message = chatInput.value.trim();
        if (!message) return;

        addMessage("user", message);

        chatInput.value = "";
        chatInput.disabled = true;

        const sendButton = chatForm.querySelector('button[type="submit"]');
        if (sendButton) {
            sendButton.disabled = true;
            sendButton.textContent = "Sending…";
        }

        const loadingMessage = addMessage(
            "assistant",
            "Thinking…"
        );

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message }),
                signal: controller.signal
            });

            const data = await response.json().catch(() => ({}));

            loadingMessage.remove();

            if (!response.ok) {
                console.error("Chat API error:", response.status, data);

                addMessage(
                    "assistant",
                    data.detail
                        ? `Chatbot error (${response.status}): ${data.detail}`
                        : `The server returned error ${response.status}. Check the FastAPI terminal.`
                );

                return;
            }

            addMessage(
                "assistant",
                data.answer || "The chatbot returned an empty answer.",
                data.sources || []
            );
        } catch (error) {
            loadingMessage.remove();

            if (error.name === "AbortError") {
                addMessage(
                    "assistant",
                    "The chatbot took longer than 60 seconds. Please check the FastAPI terminal for the Gemini API error and try again."
                );
            } else {
                console.error("Chatbot request failed:", error);

                addMessage(
                    "assistant",
                    "I couldn't connect to the chatbot. Check that FastAPI is running and inspect the terminal for errors."
                );
            }
        } finally {
            clearTimeout(timeoutId);
            chatInput.disabled = false;

            if (sendButton) {
                sendButton.disabled = false;
                sendButton.textContent = "Send";
            }

            chatInput.focus();
        }
    });
}
