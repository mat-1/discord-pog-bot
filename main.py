import discordbot
from threading import Thread
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
  return 'pog'

def flask_thread():
	app.run(host='0.0.0.0')

Thread(None, flask_thread).start()


discordbot.start_bot()