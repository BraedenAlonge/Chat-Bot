import socket
import time


class IRC:
    def __init__(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def command(self, command_text):
        self.connection.send(bytes(command_text + "\n", "UTF-8"))

    def send(self, channel_name, message_text):
        self.command("PRIVMSG " + channel_name + " :" + message_text)

    def connect(self, server, port, channel_name, botnick, botpass, botnickpass):
        print("Connecting to: " + server)
        self.connection.connect((server, port))
        self.connection.settimeout(1.0)
        self.command("USER " + botnick + " " + botnick + " " + botnick + " :python")
        self.command("NICK " + botnick)
        if botnickpass and botpass:
            credential_command = "NICKSERV IDENTIFY " + botnickpass + " " + botpass
            self.connection.send(bytes(credential_command + "\n", "UTF-8"))
        time.sleep(5)
        self.command("JOIN " + channel_name)

    def get_response(self):
        try:
            response = self.connection.recv(2040).decode("UTF-8")
        except socket.timeout:
            return ""

        if not response:
            return ""

        if response.find("PING") != -1:
            self.command("PONG " + response.split()[1] + "\r")

        return response
