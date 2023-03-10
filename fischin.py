import irc.bot
import irc.strings
import ssl
import random
import yaml
import logging
from datetime import datetime, timedelta
from tinydb import TinyDB, Query
from flask import Flask, make_response
from threading import Thread

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

class FishingBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6697):
        ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname, connect_factory = ssl_factory)
        self.channel = channel
        self.db = TinyDB('money.json')
        self.User = Query()
        self.nickname = nickname
        self.players = {}
        with open('content.yaml', 'r', encoding='utf-8') as yaml_file:
            self.content = yaml.safe_load(yaml_file)

    def start_http_server(self):
        @app.route('/health', methods=['GET'])
        def health():
            return make_response('', 200)
        server_thread = Thread(target=app.run, kwargs={'host':'0.0.0.0', 'port':8000})
        server_thread.start()

    def on_welcome(self, c, e):
        c.join(self.channel)
        self.start_http_server()

    def on_pubmsg(self, c, e):
        nick = e.source.nick
        message = e.arguments[0]
        if message.startswith("cast") or message.startswith("spin") or message.startswith("fish") or message.startswith("fisch"):
            self.cast(c, nick)
        elif message.startswith("reel") or message.startswith("catch"):
            self.reel(c, nick)
        elif message.startswith("money") or message.startswith("muney"):
            self.check_money(c, nick)
        elif message.startswith(f"bowl"):
            if len(message) == 4:
                self.bowl(c, nick)
            else:
                self.bowl(c, message[5:])

    def on_join(self, c, e):
        nick = e.source.nick
        greeting = "\x0304,11" + str.upper(f"welcome to table, {nick}")
        c.privmsg(self.channel,greeting)


    def bowl(self, c, nick):
        for event in self.content["events"]:
                    if event["name"] == "bowl":
                        response = random.choice(event["responses"]).format(n = nick)
                        response = "\x03" + "04" + "," + "01" + response
                        c.privmsg(self.channel, response)

    def cast(self, c, nick):
        self.players[nick] = {"status": "casting", "cast_time": datetime.now()}
        for event in self.content["events"]:
            if event["name"] == "cast":
                self.send_response(c, random.choice(event["responses"]).format(n = nick))
        self.reactor.scheduler.execute_after(random.randint(5,10),lambda: self.bite(c,nick))

    def bite(self, c, nick):
        self.players[nick].update({"status": "biting", "bite_time": datetime.now()})
        for event in self.content["events"]:
            if event["name"] == "bite":
                self.send_response(c, random.choice(event["responses"]).format(n = nick))



    def reel(self, c, nick):
        if nick in self.players:
            if self.players[nick]["status"] == "biting":
                if (self.players[nick]["bite_time"] - self.players[nick]["cast_time"]) < timedelta(seconds=15):
                        items = self.content["items"]
                        item = random.choices(items,weights=[1 for item in items],k=1)
                        if random.randint(0,100)< 80:
                            self.players[nick]["status"] = "idle"
                            user_data = self.db.search(self.User.nick == nick)
                            if user_data:
                                current_balance = user_data[0]["balance"]
                                new_balance = current_balance + item[0]["value"]
                                self.db.update({"balance": new_balance}, self.User.nick == nick)
                            else:
                                self.db.insert({"nick":nick, "balance": item[0]["value"]})
                            self.send_response(c, random.choice(item[0]["responses"]).format(n = nick))
                        else:
                            self.players[nick]["status"] = "idle"
                            for event in self.content["events"]:
                                if event["name"] == "fail_catch":
                                    self.send_response(c, random.choice(event["responses"]).format(n = nick))
                else:
                    self.players[nick]["status"] = "idle"
                    for event in self.content["events"]:
                        if event["name"] == "fail_catch":
                            self.send_response(c, random.choice(event["responses"]).format(n = nick))
            else:
                for event in self.content["events"]:
                    if event["name"] == "premature_reel":
                        self.send_response(c, random.choice(event["responses"]).format(n = nick))
        else:
            pass

    def check_money(self, c, nick):
            user_data = self.db.search(self.User.nick == nick)
            if user_data:
                for event in self.content["events"]:
                    if event["name"] == "check_money":
                        self.send_response(c,  random.choice(event["responses"]).format(money=user_data[0]["balance"], n=nick))
            else:
                for event in self.content["events"]:
                    if event["name"] == "check_money":
                        self.db.insert({"nick":nick, "balance": 0})
                        self.send_response(c, random.choice(event["responses"]).format(money=0, n=nick))

    def send_response(self, c, response):
        color_pairs = [("01","07"),("03","08"),("02","10"),("06","09"),("11","07"),("03","05"),("08","12")]
        color_pair = random.choice(color_pairs)
        text_color, bg_color = color_pair
        response = "\x03" + text_color + "," + bg_color + response
        c.privmsg(self.channel, response)
        
    def on_ping(self, c, e):
        c.pong(e.arguments[0])
    

if __name__ == "__main__":
    bot = FishingBot(channel="#gamme", nickname="unicoin", server="irc.buttes.org")
    bot.start()
