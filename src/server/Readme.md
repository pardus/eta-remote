# WebSocket Chat Server

A simple WebSocket server that supports multiple chat rooms.

## Features

- Multiple rooms support
- Message broadcasting to all clients in a room
- Automatic room cleanup when empty

### Connect to a room

```javascript
const socket = new WebSocket("ws://localhost:8765/your-room-name");

socket.onmessage = function(event) {
    console.log("Received:", event.data);
};

socket.send("Hello everyone!");
```

### Test interface

Open `test.html` in a browser to test the server manually.

## API

- **WebSocket URL**: `ws://localhost:8765/{room-name}`
- **Messages**: Any text message is broadcast to all other clients in the same room
