CSC482 Lab 5: Chatbot
Names: Braeden Alonge, Lucas Summers, Rory Smail, and Nathan Lim

DESCRIPTION:
This is an IRC based chatbot that can handle a complex greeting protocol, various commands, and answer questions about country statistics 
(population, area, region, coastline, population density, GDP, literacy, cellular subscriptions, birthrate, deathrate).

The system will automatically download the spaCy English language model (en_core_web_lg) on first run if not present.

HOW TO RUN:

1. Install dependencies:
   pip install -r packages.txt

2. Run the bot:
   python main.py

The bot will:
- Connect to IRC server: irc.libera.chat (port 6667)
- Join channel: #csc482
- Use a random bot nickname starting with "rando-bot"

COMMANDS:
- Address the bot with "botname:" prefix for commands
- "die" - Shut down the bot
- "forget" - Clear memory and reset conversations
- "who are you" or "usage" - Get bot information and capabilities
- "users" - List users in the channel
- "hi", "hello", "hey" - Start a greeting conversation

COUNTRY QUESTIONS:
Ask questions like:
- "How many people live in Italy?"
- "How big is Italy?"
- "How many people have phones in China?"

The bot uses natural language processing to understand and answer country-related questions.
