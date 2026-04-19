# test_websocket.py
import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8000/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected!")
            data = await ws.recv()
            print(f"Received: {data[:200]}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())