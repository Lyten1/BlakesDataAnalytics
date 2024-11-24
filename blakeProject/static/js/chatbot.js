const history = document.getElementById("history");
const chatContainer = document.getElementById("chat-container");
const newChatButton = document.getElementById("new-chat-btn");

// Змінна для зберігання поточного лічильника чатів
let chatCount = 0;

// Функція для створення нового чату
function createNewChat() {
  // Оновлюємо лічильник тільки якщо чати є
  const chatsData = JSON.parse(localStorage.getItem("chats")) || [];
  chatCount = chatsData.length === 0 ? 1 : Math.max(...chatsData.map(chat => Number(chat.chatId.split("-")[1]))) + 1;

  const chatId = `chat-${chatCount}`;
  const chatName = `Chat ${chatCount}`;

  // Створення нового контейнера для чату
  const chatWindow = document.createElement("div");
  chatWindow.classList.add("chat-window");
  chatWindow.id = chatId;
  chatWindow.innerHTML = `
    <div class="messages" id="${chatId}-messages"></div>
    <div class="chat-input">
      <input type="text" id="${chatId}-user-input" placeholder="Type your message here">
      <button id="${chatId}-send-btn">Send</button>
    </div>
  `;
  chatContainer.appendChild(chatWindow);

  // Створення нового елемента для історії чатів
  const historyItem = createHistoryItem(chatId, chatName);
  history.appendChild(historyItem);

  // Перемикання на новий чат
  switchChat(chatId);

  // Додавання обробників для введення та кнопки "Send"
  const sendButton = document.getElementById(`${chatId}-send-btn`);
  const userInput = document.getElementById(`${chatId}-user-input`);

  sendButton.addEventListener("click", async () => sendMessage(chatId, userInput.value));
  userInput.addEventListener("keypress", async (e) => {
    if (e.key === "Enter") {
      sendMessage(chatId, userInput.value);
    }
  });

  // Додаємо новий чат у localStorage
  const newChatData = { chatId, messages: [] };
  chatsData.push(newChatData);
  localStorage.setItem("chats", JSON.stringify(chatsData));
}
// Функція для перемикання між чатами
function switchChat(chatId) {
  // Ховаємо всі чати
  const allChats = document.querySelectorAll(".chat-window");
  allChats.forEach(chat => chat.style.display = "none");

  // Показуємо вибраний чат
  const activeChat = document.getElementById(chatId);
  activeChat.style.display = "flex";

  // Відновлюємо повідомлення цього чату
  restoreMessages(chatId);
}

// Function to append messages and optionally a graph to the chat
function appendMessage(chatId, sender, message, graph = null) {
  const messagesDiv = document.getElementById(`${chatId}-messages`);

  // Add the message
  const messageDiv = document.createElement("div");
  messageDiv.className = sender === "user" ? "user-message" : "bot-message";
  messageDiv.textContent = message;
  messagesDiv.appendChild(messageDiv);

  // If there's a graph, add it
  if (graph) {
    const graphDiv = document.createElement("div");
    graphDiv.className = "bot-message graph-message"; // Use a unique class for styling graphs
    const img = document.createElement("img");
    img.src = graph;
    img.alt = "Graph representation";
    graphDiv.appendChild(img);
    messagesDiv.appendChild(graphDiv);
  }

  // Scroll to the bottom of the chat
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Function to send messages and handle bot responses with optional graphs
async function sendMessage(chatId, message) {
  const userMessage = message.trim();
  if (!userMessage) return;

  // Add the user's message
  appendMessage(chatId, "user", userMessage);
  document.getElementById(`${chatId}-user-input`).value = ""; // Clear the input field

  try {
    // Fetch the bot's response
    const response = await fetch("http://127.0.0.1:5500/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    });

    if (!response.ok) {
      const errorData = await response.text();
      appendMessage(chatId, "bot", `Server error: ${response.statusText}`);
      console.error("Error from server:", errorData);
      return;
    }

    const data = await response.json();

    // Add the bot's response and graph to the chat
    const botMessage = data.message || "Sorry, I couldn't understand your question.";
    const botGraph = data.graphs && data.graphs.length > 0 ? data.graphs[0] : null; // Use the first graph if available
    appendMessage(chatId, "bot", botMessage, botGraph);

    // Save the updated chat to localStorage
    saveChats();
  } catch (error) {
    console.error("Error fetching bot response:", error);
    appendMessage(chatId, "bot", "Sorry, I couldn't process your request due to a technical issue.");
  }
}

async function getBotResponse(userMessage) {
  try {
    console.log("User message:", JSON.stringify({ message: userMessage }));

    const response = await fetch("http://127.0.0.1:5500/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: userMessage }),
    });

    if (!response.ok) {
      // Attempt to parse error as JSON, fallback to plain text if necessary
      let errorData;
      try {
        errorData = await response.json();
      } catch (parseError) {
        errorData = { error: await response.text() };
      }
      console.error("Error from server:", response.status, errorData);
      return errorData.error || `Server error: ${response.statusText}`;
    }

    // Try parsing the response as JSON
    const data = await response.json();

    // Return the bot's response if available
    return data.message || "Sorry, I couldn't understand your question.";
  } catch (error) {
    console.error("Error fetching bot response:", error);
    // Return a default error message
    return "Sorry, I couldn't process your request due to a technical issue.";
  }
}



// Функція для збереження чатів в localStorage
function saveChats() {
  const allChats = document.querySelectorAll(".chat-window");
  const chatsData = [];

  allChats.forEach((chat, index) => {
    const chatId = chat.id;
    const messages = [];
    const messageElements = chat.querySelectorAll(".messages .user-message, .messages .bot-message");

    messageElements.forEach(messageElement => {
      const sender = messageElement.classList.contains("user-message") ? "user" : "bot";
      messages.push({ sender, message: messageElement.textContent });
    });

    chatsData.push({ chatId, messages });
  });

  // Зберігаємо дані в localStorage
  localStorage.setItem("chats", JSON.stringify(chatsData));
}

// Функція для завантаження чатів з localStorage
// Завантажуємо чати з localStorage
function loadChats() {
  const chatsData = JSON.parse(localStorage.getItem("chats")) || [];

  chatsData.forEach(chat => {
    const chatId = chat.chatId;
    const chatName = `Chat ${chatId.split("-")[1]}`;

    // Створюємо контейнер для чату
    const chatWindow = document.createElement("div");
    chatWindow.classList.add("chat-window");
    chatWindow.id = chatId;
    chatWindow.innerHTML = `
      <div class="messages" id="${chatId}-messages"></div>
      <div class="chat-input">
        <input type="text" id="${chatId}-user-input" placeholder="Type your message here">
        <button id="${chatId}-send-btn">Send</button>
      </div>
    `;
    chatContainer.appendChild(chatWindow);

    // Відновлюємо повідомлення для кожного чату
    chat.messages.forEach(msg => {
      appendMessage(chatId, msg.sender, msg.message);
    });

    // Створюємо елемент для історії
    const historyItem = createHistoryItem(chatId, chatName);
    history.appendChild(historyItem);

    // Додаємо обробники для нового чату
    const sendButton = document.getElementById(`${chatId}-send-btn`);
    const userInput = document.getElementById(`${chatId}-user-input`);

    sendButton.addEventListener("click", async () => sendMessage(chatId, userInput.value));
    userInput.addEventListener("keypress", async (e) => {
      if (e.key === "Enter") {
        sendMessage(chatId, userInput.value);
      }
    });
  });

  // Перемикаємося на перший чат, якщо він є
  if (chatsData.length > 0) {
    switchChat(chatsData[0].chatId);
  }
}



// Функція для відновлення повідомлень при перемиканні між чатами
function restoreMessages(chatId) {
  const messagesDiv = document.getElementById(`${chatId}-messages`);
  
  // Перевіряємо, чи вже є повідомлення в контейнері
  if (messagesDiv && messagesDiv.childElementCount > 0) {
    return; // Якщо повідомлення вже є, не додаємо їх знову
  }

  // Завантажуємо чати з localStorage
  const chatsData = JSON.parse(localStorage.getItem("chats")) || []; // Перевіряємо, чи є дані
  
  const currentChat = chatsData.find(chat => chat.chatId === chatId);
  
  if (currentChat) {
    // Відновлюємо повідомлення для цього чату
    currentChat.messages.forEach(msg => {
      appendMessage(chatId, msg.sender, msg.message);
    });
  }
}

// Функція для створення елемента історії чатів
function createHistoryItem(chatId, chatName) {
  const historyItem = document.createElement("div");
  historyItem.classList.add("history-item");
  historyItem.setAttribute("data-chat-id", chatId);
  
  const itemContent = document.createElement("div");
  itemContent.classList.add("history-item-content");
  
  const chatNameSpan = document.createElement("span");
  chatNameSpan.textContent = chatName;
  chatNameSpan.classList.add("chat-name");

  const deleteButton = document.createElement("button");
  deleteButton.classList.add("delete-btn");

  const iconDelete = document.createElement("img");
  iconDelete.src = "/"; // Вказуємо шлях до вашої іконки
  iconDelete.src = "../static/source/iconDelete.png";// Вказуємо шлях до вашої іконки
  iconDelete.alt = "Delete chat";
  deleteButton.appendChild(iconDelete);

  deleteButton.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteChat(chatId);
  });

  itemContent.appendChild(chatNameSpan);
  itemContent.appendChild(deleteButton);

  historyItem.appendChild(itemContent);

  historyItem.addEventListener("click", () => switchChat(chatId));

  return historyItem;
}

// Функція для оновлення історії чатів
function updateHistory() {
  const chatsData = JSON.parse(localStorage.getItem("chats"));
  history.innerHTML = ''; // Очищаємо історію перед оновленням

  // Якщо чати є в localStorage
  if (chatsData && chatsData.length > 0) {
    chatsData.forEach((chatData) => {
      const chatId = chatData.chatId;
      const chatName = `Chat ${chatData.chatId.replace("chat-", "")}`; // Витягуємо номер чату з chatId

      // Створення нового елемента для історії чатів з кнопкою видалення
      const historyItem = createHistoryItem(chatId, chatName);
      history.appendChild(historyItem);
    });
  }
}

// Функція для видалення чату
function deleteChat(chatId) {
  // Завантажуємо чати з localStorage
  let chatsData = JSON.parse(localStorage.getItem("chats")) || [];

  // Фільтруємо чати, щоб видалити вибраний
  chatsData = chatsData.filter(chat => chat.chatId !== chatId);

  // Оновлюємо localStorage
  localStorage.setItem("chats", JSON.stringify(chatsData));

  // Видаляємо чат з DOM
  const chatWindow = document.getElementById(chatId);
  if (chatWindow) chatWindow.remove();

  // Видаляємо елемент з історії
  const historyItem = document.querySelector(`.history-item[data-chat-id="${chatId}"]`);
  if (historyItem) historyItem.remove();

  // Якщо це був останній чат, скидаємо лічильник
  if (chatsData.length === 0) {
    chatCount = 0;
  }

  // Якщо залишилися чати, переключаємося на перший доступний
  if (chatsData.length > 0) {
    switchChat(chatsData[0].chatId);
  }
}


// Завантажуємо чати при першому завантаженні сторінки
document.addEventListener("DOMContentLoaded", () => {
  loadChats();
  newChatButton.addEventListener("click", createNewChat);
});