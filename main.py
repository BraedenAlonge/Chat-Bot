import os
import random
import sys
import time
import spacy
from chatbot.auto_greeting_controller import OutreachController
from chatbot.country_information_store import CountryInformationStore
from chatbot.greeting_fsm import GreetingFSM
from chatbot.irc_client import IRC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COUNTRY_DATA_PATH = os.path.join(BASE_DIR, "data", "countries_clean.csv")
country_information_store = None

try:
    spacy.load("en_core_web_lg")
except OSError:
    spacy.cli.download("en_core_web_lg")


def parse_message(raw_text, botnick):
    """
    Extracts the sender and message text.
    Detects if message is addressed to the bot: botnick:
    """
    if " PRIVMSG " not in raw_text:
        return None, None, False

    try:
        sender = raw_text.split("!")[0].replace(":", "")
        message_text = raw_text.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()
    except Exception:
        return None, None, False

    is_addressed = message_text.lower().startswith(botnick.lower() + ":")
    if is_addressed:
        message_text = message_text[len(botnick) + 1:].strip()

    return sender, message_text, is_addressed


# Memory store (for forget command)
memory = {}

def handle_command(sender, message_text, irc_client, channel_name, botnick, auto_greeting_controller):
    message_lower = message_text.lower()

    # die
    if message_lower == "die":
        time.sleep(1)
        irc_client.send(channel_name, f"{sender}: I shall!")
        irc_client.command("QUIT")
        sys.exit()

    # forget
    elif message_lower == "forget":
        time.sleep(1)
        memory.clear()
        greeting_state_machine.reset()
        auto_greeting_controller.reset_on_join()
        irc_client.send(channel_name, f"{sender}: forgetting everything")
        return

    # who are you? / usage
    elif message_lower in ("who are you", "who are you?", "usage"):
        time.sleep(1)
        irc_client.send(channel_name, f"{sender}: My name is {botnick}. I was created by Braeden Alonge, Lucas Summers, Rory Smails, and Nathan Lim.")
        irc_client.send(channel_name, f"{sender}: I can answer questions about country stats (population, area, region, coastline, population density, "
        "GDP, literacy, cellular subscriptions, birthrate, deathrate). Nathan and Braeden worked on applying the cross-encoder model to detect "
        "the type of question, and Lucas and Rory worked on the the country lookup. All of us worked on putting everything together and final answer generation. ")

        irc_client.send(channel_name, f"Example question: \"How many people live in Italy?\"")
        return

    # users
    elif message_lower == "users":
        time.sleep(1)
        # send a list of users in the channel
        irc_client.command(f"NAMES {channel_name}")
        return "users"

    # greetings (handed off to FSM)
    elif "hi" in message_lower or "hello" in message_lower or "hey" in message_lower:
        greeting_state_machine.receive_greeting(sender, irc_client, channel_name)
        return

    smart_response = None
    if country_information_store:
        smart_response = country_information_store.answer_question(message_text)
    if smart_response:
        time.sleep(1)
        irc_client.send(channel_name, f"{sender}: {smart_response}")
        return

    # Greeting FSM may still need to consume the message if we are mid-conversation
    if greeting_state_machine.handle_conversation_message(sender, message_text, irc_client, channel_name):
        return


if os.path.exists(COUNTRY_DATA_PATH):
    try:
        country_information_store = CountryInformationStore(COUNTRY_DATA_PATH)
    except Exception as exc:
        print(f"Failed to initialize CountryInformationStore: {exc}")
        country_information_store = None
else:
    print(f"Country data file not found: {COUNTRY_DATA_PATH}")

## IRC Config
server = "irc.libera.chat"  # server IP/Hostname
port = 6667
channel = "#myowntestcsc482lobster"
botnick = "rando-bot" + str(random.randint(0, 1000))
botnickpass = ""  # for a registered nickname
botpass = ""  # for a registered bot

greeting_state_machine = GreetingFSM()
auto_greeting_controller = OutreachController(greeting_state_machine, botnick)

if __name__ == "__main__":
    irc_client = IRC()
    irc_client.connect(server, port, channel, botnick, botpass, botnickpass)

    auto_greeting_controller.reset_on_join()

    requesting_user = None

    while True:
        response_text = irc_client.get_response()
        if response_text:
            print("RECEIVED ==> ", response_text)

            for response_line in response_text.split("\n"):
                response_line = response_line.strip()
                if not response_line:
                    continue

                if " 353 " in response_line and channel in response_line:
                    auto_greeting_controller.update_users_from_names(response_line)
                    if requesting_user:
                        try:
                            raw_name_list = response_line.split(" :")[-1].strip().split()
                            filtered_names = []
                            for name_value in raw_name_list:
                                if name_value not in (requesting_user, botnick):
                                    filtered_names.append(name_value)
                            irc_client.send(channel, f"{requesting_user}: {' '.join(filtered_names)}")
                        except Exception:
                            pass

                if " 366 " in response_line and channel in response_line:
                    requesting_user = None

                sender, message_text, is_addressed = parse_message(response_line, botnick)
                if not message_text:
                    continue

                auto_greeting_controller.note_activity(sender)

                # Handle addressed commands
                if is_addressed:
                    if handle_command(sender, message_text, irc_client, channel, botnick, auto_greeting_controller) == "users":
                        requesting_user = sender
                    continue

        greeting_state_machine.check_timeout(irc_client, channel)
        auto_greeting_controller.attempt_auto_outreach(irc_client, channel)
