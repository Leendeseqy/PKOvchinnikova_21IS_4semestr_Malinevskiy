import websockets
import json
import asyncio
from threading import Thread
from PyQt5.QtCore import QObject, pyqtSignal

class MessengerWebSocket(QObject):
    message_received = pyqtSignal(dict)  # Сигнал для передачи сообщений в UI
    
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.ws = None
        self.reconnect_attempts = 0
        self.is_connected = False
        self.running = True

    def connect(self):
        """Запускает WebSocket в отдельном потоке"""
        def websocket_thread():
            asyncio.run(self._websocket_listener())
        
        thread = Thread(target=websocket_thread, daemon=True)
        thread.start()

    async def _websocket_listener(self):
        """Основной цикл WebSocket"""
        while self.running and self.reconnect_attempts < 5:
            try:
                uri = f"ws://192.168.0.48:8000/ws/{self.user_id}"
                async with websockets.connect(uri) as websocket:
                    self.ws = websocket
                    self.is_connected = True
                    self.reconnect_attempts = 0
                    print("WebSocket connected")
                    
                    while self.running:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=30)
                            await self._handle_message(message)
                        except asyncio.TimeoutError:
                            # Отправляем ping для поддержания соединения
                            await websocket.send('ping')
                        except Exception as e:
                            print(f"WebSocket receive error: {e}")
                            break
                            
            except Exception as e:
                print(f"WebSocket connection error: {e}")
                self.is_connected = False
                self.reconnect_attempts += 1
                await asyncio.sleep(min(3000 * self.reconnect_attempts, 10000) / 1000)

    async def _handle_message(self, message):
        """Обработка входящих сообщений"""
        try:
            if message == 'pong':
                return
                
            data = json.loads(message)
            # Отправляем данные в UI через сигнал
            self.message_received.emit(data)
            
        except json.JSONDecodeError:
            print(f"Non-JSON message: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")

    def send_message(self, data):
        """Отправка сообщения через WebSocket"""
        if self.is_connected and self.ws:
            asyncio.run(self._send_async(data))

    async def _send_async(self, data):
        """Асинхронная отправка сообщения"""
        try:
            await self.ws.send(json.dumps(data))
        except Exception as e:
            print(f"Error sending message: {e}")

    def disconnect(self):
        """Отключение WebSocket"""
        self.running = False
        if self.ws:
            asyncio.run(self.ws.close())