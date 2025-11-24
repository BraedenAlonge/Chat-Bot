import random
import time


class GreetingFSM:
    """Implements the Phase II greeting finite state machine."""

    TIMEOUT_RANGE = (20, 30)
    PENDING_OUTREACH_STATES = {"1_INITIAL_OUTREACH", "1_SECONDARY_OUTREACH"}  # during outreach, bot can still receive greetings from other users

    def __init__(self):
        self.state = "START"
        self.partner = None
        self.channel = None
        self.irc_client = None
        self.role = None
        self.wait_deadline = None
        self.last_time = 0
        self.timeout_inquiry_prompted = False
        # Tracks whether a full greeting conversation has completed; will avoid outreach if so
        self.conversation_completed = False
        self.state_1_initial_outreach_prompts = [
            "Hello!",
            "Hi!",
        ]
        self.state_1_secondary_outreach_prompts = [
            "I said HI!",
            "Excuse me, hello?",
            "Hellllloooooo!",
        ]
        self.state_2_outreach_reply_phrases = [
            "Hello back at you!",
            "Hi",
            "Howdy there, pardner! 🤠",
        ]
        self.state_1_inquiry_prompts = [
            "How are you?",
            "How are you doing?",
            "What's happening?",
        ]
        self.state_2_inquiry_prompts = [
            "How about you?",
            "And yourself?",
        ]
        self.state_2_inquiry_reply_phrases = [
            "I'm fine.",
            "I'm good.",
            "I'm great, thanks for asking.",
        ]
        self.state_1_inquiry_reply_phrases = [
            "I'm good.",
            "I'm fine, thanks for asking.",
            "Not too shabby.",
        ]
        self.state_1_giveup_frustrated_messages = [
            "Ok, forget you.",
            "Whatever.",
            "Screw you!",
            "Whatever, fine. Don't answer."
        ]
        self.state_2_inquiry_prompt_messages = [
            "Feel free to ask how I'm doing!",
            "Don't you think you should ask how I'm doing?",
            "Oh, I guess my feelings don't matter. 😒"
        ]

    def reset(self):
        self.state = "START"
        self.partner = None
        self.channel = None
        self.irc_client = None
        self.role = None
        self.wait_deadline = None
        self.last_time = 0
        self.timeout_inquiry_prompted = False

    def initiate_greeting(self, partner, irc_client, channel_name):
        """Bot starts the greeting sequence as Speaker 1."""
        if self.state != "START":
            return False

        self.partner = partner
        self.irc_client = irc_client
        self.channel = channel_name
        self.role = 1
        greeting = random.choice(self.state_1_initial_outreach_prompts)
        self.state = "1_INITIAL_OUTREACH"
        self.send_message_to_partner(greeting)
        self.start_timer()
        return True

    def receive_greeting(self, sender, irc_client, channel_name):
        if self.state != "START":
            if self.state in self.PENDING_OUTREACH_STATES and sender != self.partner:
                self.reset()
            else:
                if sender == self.partner:
                    self.handle_conversation_message(sender, "hello", irc_client, channel_name)
                return

        self.partner = sender
        self.irc_client = irc_client
        self.channel = channel_name
        self.role = 2
        self.state = "2_OUTREACH_REPLY"
        self.send_message_to_partner(random.choice(self.state_2_outreach_reply_phrases))
        self.start_timer()

    def handle_conversation_message(self, sender, message, irc_client, channel_name):
        if self.state == "START" or sender != self.partner:
            return False

        self.update_context(irc_client, channel_name)
        clean_message = (message or "").strip()
        if not clean_message:
            return True

        time.sleep(1)

        if self.state in ("1_INITIAL_OUTREACH", "1_SECONDARY_OUTREACH"):
            self.handle_speaker1_outreach_reply()
        elif self.state == "1_INQUIRY":
            self.handle_speaker1_status_reply(clean_message)
        elif self.state == "1_INQUIRY_REPLY":
            self.complete_conversation()
        elif self.state == "2_OUTREACH_REPLY":
            if self.looks_like_inquiry(clean_message):
                self.handle_speaker2_inquiry()
            else:
                self.prompt_for_inquiry()
        elif self.state == "2_INQUIRY_REPLY" and self.role == 1:
            self.handle_speaker1_partner_inquiry(clean_message)
        elif self.state == "2_INQUIRY":
            self.handle_speaker2_reply()
        return True

    def check_timeout(self, irc_client, channel_name):
        if self.state == "START" or not self.wait_deadline:
            return

        self.update_context(irc_client, channel_name)
        if time.time() < self.wait_deadline:
            return

        if self.state == "1_INITIAL_OUTREACH":
            self.send_secondary_outreach()
        elif self.state == "2_INQUIRY_REPLY":
            # On first timeout in 2_INQUIRY_REPLY, prompt once; on second timeout, give up.
            if not self.timeout_inquiry_prompted:
                self.timeout_inquiry_prompted = True
                self.prompt_for_inquiry()
            else:
                self.enter_giveup_state()
        elif self.state in {"1_SECONDARY_OUTREACH", "1_INQUIRY", "1_INQUIRY_REPLY", "2_OUTREACH_REPLY", "2_INQUIRY"}:
            self.enter_giveup_state()

    def update_context(self, irc_client, channel_name):
        if irc_client:
            self.irc_client = irc_client
        if channel_name:
            self.channel = channel_name

    def start_timer(self):
        self.wait_deadline = time.time() + random.uniform(*self.TIMEOUT_RANGE)

    def clear_timer(self):
        self.wait_deadline = None

    def send_message_to_partner(self, text):
        if not self.irc_client or not self.channel:
            return
        if self.partner:
            message = f"{self.partner}: {text}"
        else:
            message = text
        self.irc_client.send(self.channel, message)
        self.last_time = time.time()

    def handle_speaker1_outreach_reply(self):
        self.state = "1_INQUIRY"
        inquiry = random.choice(self.state_1_inquiry_prompts)
        self.send_message_to_partner(inquiry)
        self.start_timer()

    def handle_speaker1_inquiry_response(self):
        self.state = "1_INQUIRY_REPLY"
        acknowledgment = random.choice(self.state_1_inquiry_reply_phrases)
        self.send_message_to_partner(acknowledgment)
        self.complete_conversation()

    def handle_speaker1_status_reply(self, message):
        # If message ALSO includes an inquiry about us, treat it as both the status reply and the partner inquiry in one
        if self.looks_like_inquiry(message):
            self.state = "2_INQUIRY"
            self.handle_speaker1_inquiry_response()
        else:
            # Otherwise, wait for follow up
            self.state = "2_INQUIRY_REPLY"
            self.timeout_inquiry_prompted = False
            self.start_timer()

    def handle_speaker1_partner_inquiry(self, message):
        if not self.looks_like_inquiry(message):
            self.prompt_for_inquiry()
            return
        self.state = "2_INQUIRY"
        self.handle_speaker1_inquiry_response()

    def handle_speaker2_inquiry(self):
        reply = random.choice(self.state_2_inquiry_reply_phrases)
        followup = random.choice(self.state_2_inquiry_prompts)
        self.state = "2_INQUIRY_REPLY"
        self.send_message_to_partner(reply)
        time.sleep(1)
        self.state = "2_INQUIRY"
        self.send_message_to_partner(followup)
        self.start_timer()

    def handle_speaker2_reply(self):
        self.state = "1_INQUIRY_REPLY"
        self.complete_conversation()

    def prompt_for_inquiry(self):
        self.send_message_to_partner(random.choice(self.state_2_inquiry_prompt_messages))
        self.start_timer()

    def send_secondary_outreach(self):
        self.state = "1_SECONDARY_OUTREACH"
        self.send_message_to_partner(random.choice(self.state_1_secondary_outreach_prompts))
        self.start_timer()

    def enter_giveup_state(self):
        self.state = "GIVEUP_FRUSTRATED"
        self.send_message_to_partner(random.choice(self.state_1_giveup_frustrated_messages))
        self.complete_conversation()

    def complete_conversation(self):
        self.conversation_completed = True
        self.state = "END"
        self.clear_timer()
        self.reset()

    def looks_like_inquiry(self, message):
        text = message.lower()
        inquiry_tokens = [
            "how are",
            "how",
            "hows",
            "how's",
            "what's up",
            "what is up",
            "how is it going",
            "how are you",
        ]
        if any(token in text for token in inquiry_tokens):
            return True
        elif text.endswith("?") and "you" in text:
            return True
        else:
            return False
