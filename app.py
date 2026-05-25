from flask import Flask
import socket

app = Flask(__name__)


@app.route("/")
def index():
    return f"""
    <h1>CICD Test App</h1>
    <p>Server: {socket.gethostname()}</p>
    <p>Status: Running</p>
    """
