import random
import time


class OutreachController:
    """Manages automatic outreach timing and channel presence data."""

    def __init__(self, greeting_fsm, botnick):
        self.greeting_fsm = greeting_fsm
        self.botnick = botnick
        self.channel_users = set()
        self.join_timestamp = None
        self.auto_outreach_deadline = None
        self.auto_outreach_done = False

    def reset_on_join(self):
        self.join_timestamp = time.time()
        self.auto_outreach_deadline = self.join_timestamp + random.uniform(10, 20)
        self.auto_outreach_done = False
        # Clear any record of prior completed greetings.
        if hasattr(self.greeting_fsm, "conversation_completed"):
            self.greeting_fsm.conversation_completed = False

    def update_users_from_names(self, names_line):
        try:
            raw_names = names_line.split(" :")[-1].strip().split()
        except Exception:
            return

        for name in raw_names:
            stripped_name = name.lstrip("@+%~&")
            if stripped_name and stripped_name != self.botnick:
                self.channel_users.add(stripped_name)

    def note_activity(self, nickname):
        if nickname and nickname != self.botnick:
            self.channel_users.add(nickname)

    def attempt_auto_outreach(self, irc_client, channel_name):
        if self.auto_outreach_done or not self.auto_outreach_deadline:
            return

        if time.time() < self.auto_outreach_deadline:
            return

        # If we've already completed a greeting conversation don't initiate auto outreach again
        if getattr(self.greeting_fsm, "conversation_completed", False):
            return

        if self.greeting_fsm.state != "START":
            return

        candidates = list(self.channel_users)
        if not candidates:
            return

        partner = random.choice(candidates)
        if self.greeting_fsm.initiate_greeting(partner, irc_client, channel_name):
            self.auto_outreach_done = True
