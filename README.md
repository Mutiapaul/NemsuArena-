# Anyo Arena — local fighting prototype

Playable modes: Solo vs AI, local 1v1, and local 2v2 with four simultaneous fighters. Players can upload a photo for a face-on-fighter preview, choose an accent color, switch between Bilis and Bigat stance, and use light, heavy, guard, and skill actions. Nine arenas are included: three original vector stages, four original illustrated arcade stages, and two NEMSU Tandag-inspired campus concepts. The default fighters use two original illustrated martial arts characters.

## Start

Requires Python 3.10+ and `aiohttp`.

```bash
python3 -m pip install -r requirements.txt
python3 server.py
```

Open `http://localhost:8080` on the host. Other devices connected to the **same Wi-Fi or hotspot** open the host's displayed local address (for example `http://192.168.1.5:8080`). The host creates a room and shares its five-character code. No external game server or Internet connection is required after dependencies are installed. The host machine must remain running. If devices cannot connect, check the host firewall and whether the Wi-Fi permits device-to-device traffic.

On a phone, play with the on-screen controls. On a keyboard: A/D or arrows to move, J light, K heavy, L skill, S guard, Shift to switch stance. The skill costs 45 meter. First team to win two rounds wins the match. The host clicks **Next Round / Rematch** between rounds.

## Current scope

The game displays original illustrated fighter art with a small idle motion and attack/guard effects. These are static poses; separate attack, walk, hit and fall frame art has not been created yet. A player may upload a centered face photo to see a local preview and overlay its small crop on the illustrated fighter's face. This is a simple composite, not a generated full-body fighter. The photo stays in the local room's memory while the room is active; it is shared with participants on the LAN, so use an image you have permission to share. The four selectable colors change the accent, while the illustrated outfits are fixed. Arena images are original concept illustrations, including two based on user-provided photos of NEMSU Tandag buildings; they are not exact reproductions.

The combat server owns health, positions, hits and round results. The local network implementation is intended for trusted players on the same Wi-Fi. There is no Bluetooth mode, account system, persistence, or ranked play yet. This is an early playable prototype with simple combat and AI; it is not a finished competitive fighting game.

## Android installation

The `android/` folder contains an Android app project that opens this game on phones and supports choosing a fighter photo. See `android/README.md` for build and install steps. The Android app connects to the Python host; it does not run the server itself. This source package does not contain a compiled APK.
