import fastapi
import websockets
import typing
import orjson
import time
import socket
import pydantic

async def test_connection(
    host: str,
    port: int=80,
    password: typing.Union[str, bytes, None] = None,
    ssl: bool = False,
):
    try:
        ws = await websockets.connect(
            f'ws{"s" if ssl else ""}://{host}:{port}/',
            extra_headers={
                "Authorization": password,
                "Client-Name": "Python connection tester",
                "User-Id": 1,
            },
        )
    except Exception as e:
        print(e)
        return (False,0,{},"timeout or got binary")
    message = await ws.recv()  # kinda expected it
    try:
        j = orjson.loads(message)
    except orjson.JSONDecodeError:
        await ws.close()
        return (False, 0,{},"not lavalink")
    ping = await ws.ping()
    pong = time.time()
    await ping
    pong = time.time() - pong
    await ws.close()
    return (True, pong, j,None)


class TestConnection(pydantic.BaseModel):
    host: str = pydantic.Field(example="lavalink.api.rukchadisa.live")
    port: int = pydantic.Field(example=80)
    password: typing.Union[str, bytes, None] = pydantic.Field(
        default=None, example="youshallnotpass"
    )
    ssl: bool = False


class Return_Response(pydantic.BaseModel):
    alive: bool
    ping: float = 0
    error: typing.Optional[str] = None
    stuff: TestConnection
    stats: dict


@app.get(
    "/test",
    response_model=Return_Response,
    response_class=fastapi.responses.JSONResponse,
)
async def test(stuff: TestConnection = fastapi.Depends()):
    """Test lavalink connection
    Args:
        stuff (TestConnection, optional): _description_. Defaults to fastapi.Depends().
    Returns:
        JSONResponse
    """
    try:
        alive, ping, stats, error = await test_connection(
            stuff.host, stuff.port, stuff.password, stuff.ssl
        )
    except websockets.exceptions.InvalidStatusCode:
        return {
            "error": "Invalid status code (likely password is incorrect or host is down)",
            "alive": False,
            "ping": 0,
            "stuff": stuff,
            "stats": {},
        }
    except socket.gaierror:
        return {
            "error": "Invalid host",
            "alive": False,
            "ping": 0,
            "stuff": stuff,
            "stats": {},
        }
    except OSError:
        return {
            "error": "Invalid port or host is down",
            "alive": False,
            "ping": 0,
            "stuff": stuff,
            "stats": {},
        }
    return {"error": error, "alive": alive, "ping": ping, "stuff": stuff, "stats": stats}

@app.post("/test_bulk")
async def test_bulk(
    stuff: typing.List[TestConnection]
):
    result = []
    for x in stuff:
        alive, ping, stats, error = await test_connection(
            x.host, x.port, x.password, x.ssl
        )
        result.append(
            {
                "error": error,
                "alive": alive,
                "ping": ping,
                "stuff": x,
                "stats": stats,
            }
        )
    return result

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
                alive, ping, stats,error = await test_connection(
                    recv["host"], recv["port"], recv["password"]
                )
            except websockets.exceptions.InvalidStatusCode:
                await ws.send_json(
                    {
                        "error": "Invalid status code (likely password is incorrect or host is down)",
                        "alive": False,
                        "ping": 0,
                        "stuff": recv,
                    }
                )
            except socket.gaierror:
                await ws.send_json(
                    {"error": "Invalid host", "alive": False, "ping": 0, "stuff": recv}
                )
            except OSError:
                await ws.send_json(
                    {
                        "error": "Invalid port or host is down",
                        "alive": False,
                        "ping": 0,
                        "stuff": recv,
                    }
                )
            else:
                await ws.send_json(
                    {"error": error, "alive": alive, "ping": ping, "stuff": recv,"stats":stats}
                )
        elif recv["type"] == "disconnect":
            await ws.send_json({"error": "Disconnected.\nSee you next time!"})
            await ws.close(reason="Disconnected by client")
            break
        else:
            await ws.send_json(
                {"error": "Invalid type", "alive": False, "ping": 0, "stuff": recv}
            )

