document.addEventListener('DOMContentLoaded', function() {
    const chatToggle = document.getElementById('chatToggle');
    const chatWindow = document.getElementById('chatWindow');
    const chatInput = document.getElementById('chatInput');
    const chatSend = document.getElementById('chatSend');
    const chatMessages = document.getElementById('chatMessages');
    const typingIndicator = document.getElementById('typingIndicator');

    let isOpen = false;

    // Toggle Chat Window
    chatToggle.addEventListener('click', () => {
        isOpen = !isOpen;
        if (isOpen) {
            chatWindow.classList.add('active');
            chatToggle.classList.add('active');
            // Focus input when opened
            setTimeout(() => chatInput.focus(), 100);
        } else {
            chatWindow.classList.remove('active');
            chatToggle.classList.remove('active');
        }
    });

    // Send Message Logic
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add User Message
        addMessage(message, 'user');
        chatInput.value = '';
        
        // Show Typing Indicator
        showTyping();

        // Send to Backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            hideTyping();
            addMessage(data.response || "Sorry, something went wrong.", 'bot');
        })
        .catch(error => {
            console.error('Error:', error);
            hideTyping();
            addMessage("Sorry, I'm having trouble connecting to the server.", 'bot');
        });
    }

    // FAQ Button Click Handler
    window.sendFAQQuestion = function(question) {
        // Add the question as a user message
        addMessage(question, 'user');
        
        // Show typing indicator
        showTyping();
        
        // Send to backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: question })
        })
        .then(response => response.json())
        .then(data => {
            hideTyping();
            addMessage(data.response || "Sorry, something went wrong.", 'bot');
        })
        .catch(error => {
            console.error('Error:', error);
            hideTyping();
            addMessage("Sorry, I'm having trouble connecting to the server.", 'bot');
        });
    };

    // Event Listeners
    chatSend.addEventListener('click', sendMessage);
    
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Helper Functions
    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.textContent = text;
        chatMessages.insertBefore(div, typingIndicator); // Insert before typing indicator
        scrollToBottom();
    }

    function showTyping() {
        typingIndicator.style.display = 'flex';
        scrollToBottom();
    }

    function hideTyping() {
        typingIndicator.style.display = 'none';
        scrollToBottom();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Auto-focus logic handled in toggle
    
    // Initial Greeting (Optional - check if empty)
    if (chatMessages.children.length <= 1) { // 1 because of typing indicator
        setTimeout(() => {
             addMessage("👋 Hi! I'm your Smart Link Intelligence AI assistant. I can help you with features, pricing, security, analytics, and getting started. What would you like to know?", 'bot');
        }, 500);
    }
});
