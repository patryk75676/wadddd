import logging
from flask import Flask, request, jsonify
from state import STATE

logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)
app.logger.disabled = True


@app.post("/api/register")
def register():
    STATE.register(request.get_json(force=True))
    return {"status": "ok"}


@app.post("/api/heartbeat")
def heartbeat():
    cmd = STATE.heartbeat(request.get_json(force=True))
    return jsonify({"status": "ok", **cmd})


@app.get("/api/devices")
def devices():
    return jsonify(STATE.get_devices())


@app.post("/api/devices/<device_id>/command")
def command(device_id):
    STATE.command(device_id, request.get_json(force=True))
    return {"status": "queued"}


@app.delete("/api/devices/<device_id>")
def delete_device(device_id):
    STATE.delete_device(device_id)
    return {"status": "deleted"}


@app.post("/api/broadcast")
def broadcast():
    STATE.broadcast(request.get_json(force=True))
    return {"status": "queued"}


@app.get("/api/summary")
def summary():
    return jsonify(STATE.summary())


def run_server(host="0.0.0.0", port=8000):
    app.run(host=host, port=port, debug=False, use_reloader=False)
