"""Anyo Arena local-only game server. Run: python3 server.py"""
import asyncio
import json
import random
import socket
import time
from pathlib import Path

from aiohttp import web, WSMsgType

ROOT = Path(__file__).parent
rooms = {}


def fighter(name, team, avatar="", style="neon"):
    return dict(name=name[:18], team=team, avatar=avatar[:45000], style=style,
                x=230 if team == 0 else 770, y=0, vx=0, hp=100, face=1 if team == 0 else -1,
                stance=0, meter=0, cooldown=0, stun=0, attack=0, guard=False,
                input={}, wins=0)


def public(room, include_avatars=False):
    return dict(type="state", code=room["code"], mode=room["mode"], arena=room["arena"],
                phase=room["phase"], timer=max(0, round(room["timer"], 1)),
                scores=room["scores"], message=room["message"],
                players=[dict(id=p["id"], **{k: v for k, v in p["fighter"].items()
                    if k not in ("input", "vx", "cooldown", "stun", "avatar", "shiftHeld")},
                    **({"avatar": p["fighter"]["avatar"]} if include_avatars else {})) for p in room["players"]])


async def send(ws, payload):
    if not ws.closed:
        await ws.send_json(payload)


async def broadcast(room, include_avatars=False):
    data = public(room, include_avatars)
    for p in list(room["players"]):
        if p.get("ws"):
            try:
                await send(p["ws"], data)
            except ConnectionError:
                pass


def reset_round(room):
    count = len(room["players"])
    for n, p in enumerate(room["players"]):
        f = p["fighter"]
        f.update(x=(180 + (n % 2) * 125 if f["team"] == 0 else 820 - (n % 2) * 125),
                 y=0, vx=0, hp=100, meter=0, cooldown=0, stun=0, attack=0,
                 guard=False, input={})
    room.update(phase="fight", timer=75, message="FIGHT!")


def ai_input(room, f, now):
    enemies = [p["fighter"] for p in room["players"] if p["fighter"]["team"] != f["team"] and p["fighter"]["hp"] > 0]
    if not enemies:
        return {}
    target = min(enemies, key=lambda e: abs(e["x"] - f["x"]))
    distance = abs(target["x"] - f["x"])
    return {"left": target["x"] < f["x"] - 68, "right": target["x"] > f["x"] + 68,
            "light": distance < 92 and int(now * 2.9) % 3 == 0,
            "heavy": distance < 100 and int(now * 2.9) % 5 == 0,
            "guard": distance < 108 and target["attack"] > 0 and int(now * 5) % 3 == 0,
            "special": distance < 130 and f["meter"] >= 45}


def tick(room, dt):
    if room["phase"] != "fight":
        return
    room["timer"] -= dt
    fighters = [p["fighter"] for p in room["players"]]
    now = time.monotonic()
    for p in room["players"]:
        f = p["fighter"]
        if f["hp"] <= 0:
            continue
        if p["id"] == "AI":
            f["input"] = ai_input(room, f, now)
        keys = f["input"]
        f["cooldown"] = max(0, f["cooldown"] - dt)
        f["stun"] = max(0, f["stun"] - dt)
        f["attack"] = max(0, f["attack"] - dt)
        f["guard"] = bool(keys.get("guard")) and f["stun"] == 0
        if f["stun"] == 0:
            direction = int(bool(keys.get("right"))) - int(bool(keys.get("left")))
            speed = 245 if f["stance"] == 0 else 175
            f["x"] = max(42, min(958, f["x"] + direction * speed * dt + f["vx"] * dt))
            if keys.get("shift") and not f.get("shiftHeld"):
                f["stance"] = 1 - f["stance"]
            f["shiftHeld"] = bool(keys.get("shift"))
        else:
            f["x"] = max(42, min(958, f["x"] + f["vx"] * dt))
        f["vx"] *= max(0, 1 - 10 * dt)
        enemies = [e for e in fighters if e["team"] != f["team"] and e["hp"] > 0]
        if enemies:
            nearest = min(enemies, key=lambda e: abs(e["x"] - f["x"]))
            f["face"] = 1 if nearest["x"] > f["x"] else -1
        if f["cooldown"] > 0 or f["stun"] > 0 or f["guard"]:
            continue
        move = next((m for m in ("special", "heavy", "light") if keys.get(m)), None)
        if not move or (move == "special" and f["meter"] < 45):
            continue
        damage, reach, delay = {"light": (7, 92, .32), "heavy": (13, 110, .62), "special": (20, 143, .85)}[move]
        if f["stance"] == 1:
            damage += 3
        if move == "special":
            f["meter"] -= 45
        f["cooldown"] = delay
        f["attack"] = .20
        for e in enemies:
            if abs(e["x"] - f["x"]) <= reach and (e["x"] - f["x"]) * f["face"] >= -15:
                hit = max(1, round(damage * (.22 if e["guard"] else 1)))
                e["hp"] = max(0, e["hp"] - hit)
                e["stun"] = .10 if e["guard"] else .22
                e["vx"] = f["face"] * (90 if e["guard"] else 230)
                f["meter"] = min(100, f["meter"] + 8)
                e["meter"] = min(100, e["meter"] + 5)
    alive = [sum(p["fighter"]["hp"] for p in room["players"] if p["fighter"]["team"] == t) for t in (0, 1)]
    if room["timer"] <= 0 or 0 in alive:
        winner = 0 if alive[0] > alive[1] else 1 if alive[1] > alive[0] else -1
        if winner >= 0:
            room["scores"][winner] += 1
        room["phase"] = "done"
        room["message"] = "DRAW!" if winner < 0 else f"TEAM {winner + 1} WINS THE ROUND!"
        if max(room["scores"]) >= 2:
            room["message"] = f"TEAM {room['scores'].index(max(room['scores'])) + 1} WINS THE MATCH!"


async def loop():
    frame = 0
    while True:
        await asyncio.sleep(1 / 30)
        frame += 1
        for room in list(rooms.values()):
            tick(room, 1 / 30)
            if frame % 2 == 0 and room["phase"] == "fight":
                await broadcast(room)


async def ws_handler(request):
    ws = web.WebSocketResponse(max_msg_size=65000, heartbeat=20)
    await ws.prepare(request)
    player = room = None
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                data = json.loads(msg.data)
            except (ValueError, TypeError):
                continue
            kind = data.get("type")
            if kind in ("create", "join") and not player:
                mode = data.get("mode", "1v1")
                if kind == "create":
                    if mode not in ("solo", "1v1", "2v2"):
                        mode = "1v1"
                    code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
                    while code in rooms:
                        code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
                    room = rooms[code] = dict(code=code, mode=mode, arena=data.get("arena", "rain"),
                        phase="lobby", timer=75, scores=[0, 0], message="WAITING FOR PLAYERS", players=[])
                else:
                    room = rooms.get(str(data.get("code", "")).upper().strip())
                if not room or room["phase"] not in ("lobby", "done") or len(room["players"]) >= (4 if room["mode"] == "2v2" else 2):
                    await send(ws, {"type": "error", "message": "Room unavailable or full."})
                    room = None
                    continue
                n = len(room["players"])
                team = n % 2 if room["mode"] != "2v2" else (0 if n in (0, 2) else 1)
                player = dict(id="P" + str(random.randrange(10000, 99999)), ws=ws,
                    fighter=fighter(str(data.get("name") or "Fighter"), team,
                        str(data.get("avatar") or "") if len(str(data.get("avatar") or "")) < 45000 else "",
                        str(data.get("style") or "neon")[:16]))
                room["players"].append(player)
                if room["mode"] == "solo":
                    room["players"].append(dict(id="AI", ws=None, fighter=fighter("Rival AI", 1, style="ember")))
                await send(ws, {"type": "welcome", "id": player["id"], "code": room["code"]})
                await broadcast(room, include_avatars=True)
            elif player and kind == "input":
                keys = data.get("keys", {})
                if isinstance(keys, dict):
                    player["fighter"]["input"] = {k: bool(keys.get(k)) for k in ("left", "right", "guard", "light", "heavy", "special", "shift")}
            elif player and kind == "start" and room["players"][0] is player:
                required = 2 if room["mode"] != "2v2" else 4
                if len(room["players"]) == required:
                    if max(room["scores"]) >= 2:
                        room["scores"] = [0, 0]
                    reset_round(room)
                    await broadcast(room, include_avatars=True)
            elif player and kind == "customize" and room["phase"] != "fight":
                player["fighter"]["name"] = str(data.get("name") or "Fighter")[:18]
                await broadcast(room)
    finally:
        if room and player:
            room["players"].remove(player)
            if room["phase"] == "fight":
                room.update(phase="lobby", message="PLAYER DISCONNECTED — WAITING")
            if not any(p.get("ws") for p in room["players"]):
                rooms.pop(room["code"], None)
            else:
                await broadcast(room)
    return ws


async def index(request):
    return web.FileResponse(ROOT / "index.html")


async def start_app(app):
    app["ticker"] = asyncio.create_task(loop())


async def stop_app(app):
    app["ticker"].cancel()


app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", ws_handler)
app.on_startup.append(start_app)
app.on_cleanup.append(stop_app)

if __name__ == "__main__":
    print("Anyo Arena: http://localhost:8080")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("192.0.2.1", 80))
        print(f"On the same Wi-Fi, open: http://{sock.getsockname()[0]}:8080")
        sock.close()
    except OSError:
        pass
    web.run_app(app, host="0.0.0.0", port=8080)
