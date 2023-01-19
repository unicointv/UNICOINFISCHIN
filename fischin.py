import irc.bot
import irc.strings
import ssl
import random
import yaml
from datetime import datetime
from tinydb import TinyDB, Query

class FishingBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6697):
        ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname, connect_factory = ssl_factory)
        self.channel = channel
        self.db = TinyDB('money.json')
        self.User = Query()
        self.nickname = nickname
        self.players = {}
        self.items = {}
        self.events = {}
        self.load_content()

    def load_content(self):
        with open("content.yaml", 'r') as stream:
            data = yaml.safe_load(stream)
            self.items = data['items']
            self.events = data['events']
            stream.close()

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_pubmsg(self, c, e):
        nick = e.source.nick
        message = e.arguments[0]
        if message.startswith("cast"):
            self.cast(c, nick)
        elif message.startswith("reel"):
            self.reel(c, nick)
        elif message.startswith("money"):
            self.check_money(c, nick)
    
    def cast(self, c, nick):
        self.players[nick] = {"status": "casting", "cast_time": datetime.now()}
        self.send_response(c, nick, random.choice(self.events["cast"]["responses"]).format(n = nick))
        c.execute_delayed(random.randint(5, 10), self.bite, (c, nick))

    def bite(self, c, nick):
        self.players[nick]["status"] = "biting"
        self.players[nick]["biting_time"] = datetime.now()
        self.send_response(c, nick, random.choice(self.events["bite"]["responses"]).format(n = nick))

    def reel(self, c, nick):
        if nick in self.players:
            if self.players[nick]["status"] == "biting":
                if self.players[nick]["biting_time"] - self.players[nick]["cast_time"] < 15:
                        items = self.items
                        item = random.choices(items,weights=[1 for item in items],k=1)
                        if random.randint(0,100)< 50:
                            self.players[nick]["status"] = "idle"
                            self.players[nick]["money"] += item[0]["value"]
                            self.send_response(c, nick, random.choice(self.item[0]["responses"]).format(n = nick))
                        else:
                            self.players[nick]["status"] = "idle"
                            self.send_response(c, nick, random.choice(self.events["fail_catch"]["responses"]))
                else:
                    self.players[nick]["status"] = "idle"
                    self.send_response(c, nick, random.choice(self.events["fail_catch"]["responses"]).format(n = nick))
            else:
                self.send_response(c, nick, random.choice(self.events["premature_reel"]["responses"]).format(n = nick))
        else:
            pass

    def check_money(self, c, nick):
        with self.db.tiny('money') as money_db:
            user_data = money_db.search(self.User.nick == nick)
            if user_data:
                self.send_response(nick, random.choice(self.events["check_money"]["responses"]).format(money=user_data[0]["balance"], n=nick))
            else:
                self.send_response(nick, random.choice(self.events["check_money"]["responses"]).format(money=0, n=nick))

    def send_response(self, c, response):
        c.privmsg(self.channel, response)
        
    def on_ping(self, c, e):
        c.pong(e.arguments[0])
    
def main(self):
        bot = FishingBot(channel="#gamme", nickname="unicoin", server="irc.libera.chat")
        bot.start()

if __name__ == "__main__":
    main()