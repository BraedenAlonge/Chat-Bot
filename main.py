import socket
import sys
import time
import random


def parse_message(raw, botnick):
    """
    Extracts the sender and message text.
    Detects if message is addressed to the bot: botnick:
    """
    if "PRIVMSG" not in raw:
        return None, None, False

    try:
        sender = raw.split("!")[0].replace(":", "")
        msg = raw.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()
    except:
        return None, None, False

    addressed = msg.lower().startswith(botnick.lower() + ":")
    if addressed:
        msg = msg[len(botnick) + 1:].strip()

    return sender, msg, addressed


# Memory store (for forget command)
memory = {}

def handle_command(sender, msg, irc, channel, botnick):
    m = msg.lower()

    # die
    if m == "die":
        irc.send(channel, f"{sender}: I shall!")
        irc.command("QUIT")
        sys.exit()

    # forget
    elif m == "forget":
        memory.clear()
        irc.send(channel, f"{sender}: forgetting everything")
        return

    # who are you? / usage
    elif m in ("who are you?", "usage"):
        irc.send(channel, f"{sender}: My name is {botnick}. I was created by the greatest 482 group of all time. 6-7!")
        irc.send(channel, f"{sender}: I can answer questions about populations. Example: \"What is the population of France?\"")
        return

    # users
    elif m == "users":
        irc.command(f"NAMES {channel}")
        return

    # greetings (handed off to FSM)
    elif m in ("hi", "hello"):
        greeting_manager.receive_greeting(sender, irc, channel)
        return

    # What is the population of X?
    elif m.startswith("what is the population of "):
        country = m.replace("what is the population of", "").strip(" ?")
        pop = pop_lookup(country)
        irc.send(channel, f"{sender}: The population of {country.title()} is {pop}.")
        return


population_data = {
    "france": "67 million",
    "germany": "83 million",
    "japan": "125 million",
    "italy": "59 million",
    "usa": "331 million",
    "united states": "331 million",
}

def pop_lookup(country):
    c = country.lower()
    if c in population_data:
        return population_data[c]
    return "unknown (not in my database)"

class IRC:
    irc = socket.socket()

    def __init__(self):
        # Deefine the socket
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def command(self, msg):
        self.irc.send(bytes(msg + "\n", "UTF-8"))

    def send(self, channel, msg):
        # Transfer data
        self.command("PRIVMSG " + channel + " :" + msg)

    def connect(self, server, port, channel, botnick, botpass, botnickpass):
        # Connect to the server
        print("Connecting to: " + server)
        self.irc.connect((server, port))

        # Perform user authentication
        self.command("USER " + botnick + " " + botnick + " " + botnick + " :python")
        self.command("NICK " + botnick)
        # self.irc.send(bytes("NICKSERV IDENTIFY " + botnickpass + " " + botpass + "\n", "UTF-8"))
        time.sleep(5)

        # join the channel
        self.command("JOIN " + channel)

    def get_response(self):
        time.sleep(1)
        # Get the response
        resp = self.irc.recv(2040).decode("UTF-8")

        if resp.find('PING') != -1:
            self.command('PONG ' + resp.split()[1] + '\r')

        return resp

# GREETINGS
class GreetingFSM:
    def __init__(self):
        self.state = "START"
        self.partner = None
        self.last_time = 0

    def reset(self):
        self.state = "START"
        self.partner = None

    # --- when someone says hi/hello TO THE BOT ---
    def receive_greeting(self, sender, irc, channel):
        # Case 1: idle → they greeted us first
        if self.state == "START":
            self.partner = sender
            self.state = "2_OUTREACH_REPLY"
            irc.send(channel, f"{sender}: hello back at you!")
            self.last_time = time.time()
            return

        # (Other transitions optional for now — minimal FSM works)

    # timeouts for frustration
    def check_timeout(self, irc, channel):
        if self.state != "START":
            if time.time() - self.last_time > 20:
                irc.send(channel, f"{self.partner}: whatever, fine. Don't answer.😒")
                self.reset()

greeting_manager = GreetingFSM()



## IRC Config
server = "irc.libera.chat"  # server IP/Hostname
port = 6667
channel = "#CSC482"
botnick = "rando-bot" + str(random.randint(0, 1000))
botnickpass = ""  # for a registered nickname
botpass = ""  # for a registered bot

irc = IRC()
irc.connect(server, port, channel, botnick, botpass, botnickpass)

while True:
    text = irc.get_response()
    print("RECEIVED ==> ", text)

    sender, msg, addressed = parse_message(text, botnick)
    if not msg:
        continue

    # Handle addressed commands
    if addressed:
        handle_command(sender, msg, irc, channel, botnick)
        continue

    # Check greeting FSM timeout
    greeting_manager.check_timeout(irc, channel)

    # General greetings NOT addressed to bot? ignore or extend later
