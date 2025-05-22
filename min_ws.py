import asyncio
import websockets

async def echo(websocket, path):
    await websocket.send(hello)

async def main():
    print(Starting minimal ws server...)
    async with websockets.serve(echo, 0.0.0.0, 8765):
        print(Minimal ws server started on 0.0.0.0:8765)
        await asyncio.Future()  # run forever

asyncio.run(main())
