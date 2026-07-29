document.addEventListener("DOMContentLoaded", function () {
    // Load chat history when the page loads
    loadChatHistory();

    // Send message on button click or Enter key
    document.getElementById("send-query-button").addEventListener("click", sendMessage);
    document.getElementById("chat-input").addEventListener("keypress", function (e) {
        if (e.key === "Enter") sendMessage();
    });

    // Microphone button for voice input
    document.getElementById("microphone_btn").addEventListener("click", () => {
        eel.get_voice_command()((response) => {
            if (response && response !== "stop") {
                handleUserInput(response); // Handle user's voice input
            }
        });
    });

    // Toggle chat history visibility
    document.getElementById("chat-history-toggle").addEventListener("click", () => {
        document.getElementById("chat-history").classList.toggle("show");
    });

    // Settings button
    document.getElementById("settings-button").addEventListener("click", function () {
        document.getElementById("settings-popup").style.display = "block";
    });

    // Close Settings Popup
    document.getElementById("close-settings-btn").addEventListener("click", function () {
        document.getElementById("settings-popup").style.display = "none";
    });

    // Improved website saving functionality

    document.getElementById('stop-speak').addEventListener('click', function () {
         eel.kill_tts()();  // Double parentheses for Eel calls
    });
    
    

    // Stored Data Button - Open Pop-up
    document.getElementById("stored-data-btn").addEventListener("click", function () {
        eel.get_webinfo()(function (data) {
            const dataList = document.getElementById("data-list");
            dataList.innerHTML = ''; // Clear previous data

            if (data.urls.length === 0) {
                dataList.innerHTML = "<li>No stored data available.</li>";
            } else {
                data.urls.forEach(item => {
                    let listItem = document.createElement("li");
                    listItem.textContent = `🌐 ${item[0]} - ${item[1]}`;
                    dataList.appendChild(listItem);
                });
            }

            document.getElementById("stored-data-popup").style.display = "block"; // Show popup
        });
    });

    // Close Stored Data Popup
    document.getElementById("close-stored-data").addEventListener("click", function () {
        document.getElementById("stored-data-popup").style.display = "none";
    });

    // Delete Chat History
    document.getElementById("delete-history-btn").addEventListener("click", function () {
        if (confirm("Are you sure you want to delete the chat history?")) {
            eel.clear_chat_history()(() => {
                document.getElementById("history-content").innerHTML = ""; // Clear frontend history
            });
        }
    });
});

// ALL OTHER FUNCTIONS REMAIN EXACTLY THE SAME AS BEFORE
function loadChatHistory() {
    eel.get_chat_history()((history) => {
        const historyContent = document.getElementById("history-content");
        historyContent.innerHTML = ""; // Clear existing content

        history.forEach((item, index) => {
            const historyItem = document.createElement("div");
            historyItem.className = "history-item";

            // Display the query (first 20 characters)
            const displayQuery = item.query.replace("hey pluto ", "").substring(0, 30);
            historyItem.textContent = displayQuery; // Display first 20 letters of the query
            historyItem.setAttribute("data-index", index); // Store index for reference
            historyItem.style.cursor = "pointer";
            historyItem.style.marginBottom = "10px";
            historyItem.style.color = "white";

            // Add click event to display full query and response
            historyItem.addEventListener("click", () => {
                
                displayMessage(item.query, "user"); // Display user's query
                if (item.isForAssistant) {
                    displayMessage(item.response, "assistant"); // Display assistant's response
                } else {
                    displayMessage(item.response, "response"); // Display non-assistant response
                }
                addSpacing();
            });

            historyContent.appendChild(historyItem);
        });
    });
}

function handleUserInput(userInput) {
    displayMessage(userInput, "user"); // Display user's query

    if (isQueryForAssistant(userInput)) {
        // Query is for DeepSeek (Assistant)
        eel.get_assistant_response(userInput)((assistantResponse) => {
            if (assistantResponse) {
                displayMessage(assistantResponse, "assistant"); // Display assistant's response
            }
            addSpacing(); // Add spacing between query-response pairs
            loadChatHistory(); // Reload chat history after new query
        });
    } else {
        // Query is NOT for DeepSeek (System Command)
        eel.get_non_assistant_response(userInput)((nonAssistantResponse) => {
            if (nonAssistantResponse) {
                displayMessage(nonAssistantResponse, "response"); // Display system command response
            }
            addSpacing(); // Add spacing between query-response pairs
            loadChatHistory(); // Reload chat history after new query
        });
    }
}

async function sendMessage() {
    const userInput = document.getElementById("chat-input").value.trim();
    if (!userInput) {
        displayMessage("Please enter a message!", "response");
        return;
    }

    handleUserInput(userInput); // Handle the user's input

    // Clear the input field
    document.getElementById("chat-input").value = "";
}

function isQueryForAssistant(query) {
    // Check if the query starts with "hey jarvis"
    return query.startsWith("hey pluto ");
}

function displayMessage(message, sender) {
    const displayScreen = document.getElementById("display-screen");
    const messageDiv = document.createElement("div");

    // Add prefix based on the sender
    let formattedMessage;
    if (sender === "user") {
        formattedMessage = `Q: ${message}`; // User query
    } else if (sender === "assistant") {
        formattedMessage = `A: ${message}`; // Assistant response
    } else if (sender === "response") {
        formattedMessage = `R: ${message}`; // Non-assistant response
    }

    messageDiv.className = sender === "user" ? "user-message" : sender === "assistant" ? "assistant-message" : "response-message";
    messageDiv.innerText = formattedMessage;

    displayScreen.appendChild(messageDiv);
    displayScreen.scrollTop = displayScreen.scrollHeight; // Auto-scroll to the latest message
}

function addSpacing() {
    const displayScreen = document.getElementById("display-screen");
    const spacer = document.createElement("div");
    spacer.style.height = "15px";
    displayScreen.appendChild(spacer);
}

// Expose the displayMessage function to Python
eel.expose(displayMessage);



