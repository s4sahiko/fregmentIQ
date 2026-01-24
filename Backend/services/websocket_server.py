"""
WebSocket Server - Streams comparison results to frontend
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import websockets
from typing import Set, Dict, Any
from datetime import datetime


class WebSocketServer:
    """
    WebSocket server that broadcasts comparison results to connected clients
    """
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.server = None
        self.is_running = False
        
        # Store latest data for each batch
        self.latest_data: Dict[int, Dict] = {}
    
    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        print(f"[WebSocket] Client connected. Total clients: {len(self.clients)}")
        
        # Send current state to new client
        if self.latest_data:
            await websocket.send(json.dumps({
                "type": "initial_state",
                "data": self.latest_data
            }))
    
    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client connection"""
        self.clients.discard(websocket)
        print(f"[WebSocket] Client disconnected. Total clients: {len(self.clients)}")
    
    async def handler(self, websocket: websockets.WebSocketServerProtocol, path: str = None):
        """Handle WebSocket connections"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # Handle incoming messages (if needed)
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        
        # Send to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    def broadcast_sync(self, message: Dict[str, Any]):
        """Synchronous wrapper for broadcast (for use in non-async code)"""
        if self.is_running and self.clients:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(message),
                self.loop
            )
    
    async def send_batch_update(self, batch_num: int, data_point: Dict, comparison: Dict):
        """Send batch update to all clients"""
        self.latest_data[batch_num] = {
            "data_point": data_point,
            "comparison": comparison,
            "timestamp": datetime.now().isoformat()
        }
        
        message = {
            "type": "batch_update",
            "batch_number": batch_num,
            "data_point": data_point,
            "comparison": comparison,
            "server_time": datetime.now().isoformat()
        }
        
        await self.broadcast(message)
    
    def send_batch_update_sync(self, batch_num: int, data_point: Dict, comparison: Dict):
        """Synchronous wrapper for send_batch_update"""
        if self.is_running:
            asyncio.run_coroutine_threadsafe(
                self.send_batch_update(batch_num, data_point, comparison),
                self.loop
            )
    
    async def start(self):
        """Start the WebSocket server"""
        self.is_running = True
        self.loop = asyncio.get_event_loop()
        
        self.server = await websockets.serve(
            self.handler,
            self.host,
            self.port
        )
        
        print(f"[WebSocket] Server started on ws://{self.host}:{self.port}")
        
        # Keep server running
        await self.server.wait_closed()
    
    async def stop(self):
        """Stop the WebSocket server"""
        self.is_running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print("[WebSocket] Server stopped")


# Singleton instance for global access
_websocket_server: WebSocketServer = None


def get_websocket_server() -> WebSocketServer:
    """Get or create WebSocket server instance"""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer()
    return _websocket_server


# For testing
if __name__ == "__main__":
    async def test_server():
        server = WebSocketServer()
        print("Starting WebSocket server...")
        await server.start()
    
    asyncio.run(test_server())
