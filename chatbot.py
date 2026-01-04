import json
import random
import re
import os
from datetime import datetime

class ChatBot:
    def __init__(self, intents_file='intents.json'):
        # Initial load
        self.intents = []
        self.intents_file = intents_file
        self.last_modified = None
        self.load_intents(intents_file)

    def load_intents(self, intents_file):
        """Loads intents from a JSON file."""
        try:
            file_path = os.path.join(os.path.dirname(__file__), intents_file)
            
            # Check if file was modified and reload if needed
            current_modified = os.path.getmtime(file_path)
            if self.last_modified is None or current_modified > self.last_modified:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.intents = data.get('intents', [])
                    self.last_modified = current_modified
                    print(f"Loaded {len(self.intents)} intents from {intents_file}")
        except Exception as e:
            print(f"Error loading intents: {e}")
            self.intents = []

    def get_response(self, message):
        """
        Determines the best response for a given message.
        Uses simple keyword matching for now.
        """
        # Reload intents if file was modified
        self.load_intents(self.intents_file)
        
        message = message.lower()
        
        best_intent = None
        highest_score = 0

        for intent in self.intents:
            score = 0
            for pattern in intent['patterns']:
                # Simple containment check, can be improved with regex or NLP libraries
                if pattern.lower() in message:
                    score += 1
                    # Give bonus for exact matches or longer matches
                    if pattern.lower() == message:
                        score += 2
                    # Give bonus for longer pattern matches
                    if len(pattern.split()) > 1 and pattern.lower() in message:
                        score += 1
            
            if score > highest_score:
                highest_score = score
                best_intent = intent

        if best_intent and highest_score > 0:
            return random.choice(best_intent['responses'])
        
        return "I'm not sure I understand that. Could you ask me about our features, pricing, security, analytics, getting started, or anything else about Smart Link Intelligence? I'm here to help! 😊"

# Singleton instance for easy import
chatbot_instance = ChatBot()

def get_chat_response(message):
    return chatbot_instance.get_response(message)
