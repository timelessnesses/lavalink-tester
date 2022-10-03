# lavalink-tester
A simple fastapi http/ws lavalink detector if it is up or down

## How can I check?

OpenAPI in fastapi should explain lots of things for you but if you're here for websocket here's how

1. Connect to websocket at /ws url

2. You can send json response which only accept

```json
{
  "type":"test",
  "host":"lavalink.api.rukchadisa.live",
  "port":80,
  "password":"youshallnotpass"
}
```
which this returns
```json
{
  "error": string or null
  "alive": bool
  "ping": float
  "stuff": request that you sent
}
```
