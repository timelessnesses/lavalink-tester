import fastapi
import websockets
import typing
import orjson
import time
import socket
import pydantic
async def test_connection(host: str, port:int, password:typing.Union[str,bytes,None]=None):
    ws = await websockets.connect(f'ws://{host}:{port}/',extra_headers={'Authorization':password,'Client-Name':'Python connection tester','User-Id':1})
    message = await ws.recv()
    try:
        print(orjson.loads(message))
    except orjson.JSONDecodeError:
        await ws.close()
        return (False,None)
    ping = await ws.ping()
    pong = time.time()
    await ping
    pong = time.time() - pong
    await ws.close()
    return (True,pong)

app = fastapi.FastAPI(docs_url="/", redoc_url="/redoc",debug=True,title="Lavalink Tester",description="A lavalink tester that can be used in html so you can test lavalink connectivity with this rest api",version="1.0.0")

class TestConnection(pydantic.BaseModel):
    host: str = pydantic.Field(example="lavalink.api.rukchadisa.live")
    port: int = pydantic.Field(example=80)
    password: typing.Union[str,bytes,None] = pydantic.Field(default=None,example="youshallnotpass")

class Return_Response(pydantic.BaseModel):
    alive: bool
    ping: float = 0
    error: typing.Optional[str] = None
    stuff: TestConnection
    
@app.get("/test",response_model=Return_Response,response_class=fastapi.responses.JSONResponse)
async def test(stuff:TestConnection = fastapi.Depends()):
    """Test lavalink connection

    Args:
        stuff (TestConnection, optional): _description_. Defaults to fastapi.Depends().

    Returns:
        JSONResponse
    """
    try:
        alive, ping = await test_connection(stuff.host, stuff.port, stuff.password)
    except websockets.exceptions.InvalidStatusCode:
        return {
            "error": "Invalid status code (likely password is incorrect or host is down)",
            "alive": False,
            "ping": 0,
            "stuff": stuff
        }
    except socket.gaierror:
        return {
            "error": "Invalid host",
            "alive": False,
            "ping": 0,
            "stuff": stuff
        }
    except OSError:
        return {
            "error": "Invalid port or host is down",
            "alive": False,
            "ping": 0,
            "stuff": stuff
        }
    return {
        "error": None,
        "alive": alive,
        "ping": ping,
        "stuff": stuff
    }

@app.websocket("/ws")
async def ws_endpoint(ws: fastapi.WebSocket):
    """
    Websocket endpoint to update if lavalink is alive or not instantly!  
    You should send a json object with the following keys:  
    type: str (either "test" or "disconnect")  
    host: str  
    port: int  
    password: str (optional)  
    With return type of Return_Response
    """
    await ws.accept()
    while True:
        recv = orjson.loads(await ws.receive_text())
        if "type" not in recv.keys():
            await ws.send_json({"error": "Invalid request"})
            continue
        if recv["type"] == "test":
            try:
                alive, ping = await test_connection(recv["host"], recv["port"], recv["password"])
            except websockets.exceptions.InvalidStatusCode:
                await ws.send_json({
                    "error": "Invalid status code (likely password is incorrect or host is down)",
                    "alive": False,
                    "ping": 0,
                    "stuff": recv
                })
            except socket.gaierror:
                await ws.send_json({
                    "error": "Invalid host",
                    "alive": False,
                    "ping": 0,
                    "stuff": recv
                })
            except OSError:
                await ws.send_json({
                    "error": "Invalid port or host is down",
                    "alive": False,
                    "ping": 0,
                    "stuff": recv
                })
            else:
                await ws.send_json({
                    "error": None,
                    "alive": alive,
                    "ping": ping,
                    "stuff": recv
                })
        elif recv["type"] == "disconnect":
            await ws.send_json({"error": "Disconnected.\nSee you next time!"})
            await ws.close(reason="Disconnected by client")
            break
        else:
            await ws.send_json({
                "error": "Invalid type",
                "alive": False,
                "ping": 0,
                "stuff": recv
            })
