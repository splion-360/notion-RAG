import asyncio
import json
import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import (
    WS_HEARTBEAT_INTERVAL,
    WS_IDLE_TIMEOUT,
    WS_MAX_CONNECTIONS_PER_USER,
    setup_logger,
)
from app.database.operations import ConversationOperations, MessageOperations
from app.services.chat_service import ChatService

logger = setup_logger("ws-chat")
router = APIRouter()

active_connections: dict[str, set[WebSocket]] = defaultdict(set)
connection_last_activity: dict[WebSocket, float] = {}
active_generations: dict[str, bool] = {}


chat_service = ChatService(
    active_generations=active_generations,
)


async def cleanup_connection(websocket: WebSocket, user_id: str):
    active_connections[user_id].discard(websocket)
    connection_last_activity.pop(websocket, None)

    if not active_connections[user_id]:
        del active_connections[user_id]


async def check_connection_limit(user_id: str) -> bool:
    return len(active_connections[user_id]) < WS_MAX_CONNECTIONS_PER_USER


async def is_connection_idle(websocket: WebSocket) -> bool:
    last_activity = connection_last_activity.get(websocket, time.time())
    return time.time() - last_activity > WS_IDLE_TIMEOUT


async def heartbeat_handler(websocket: WebSocket):
    try:
        while True:
            await asyncio.sleep(WS_HEARTBEAT_INTERVAL)

            if await is_connection_idle(websocket):
                await websocket.send_text(json.dumps({"type": "idle_timeout"}))
                await websocket.close(code=1000)
                break

            await websocket.send_text(json.dumps({"type": "ping"}))

    except Exception:
        pass


async def handle_stop_generation(websocket: WebSocket, message: dict):
    message_id = message.get("message_id")
    if message_id and message_id in active_generations:
        logger.info(f"Stopping generation for message {message_id}")
        active_generations[message_id] = False
        await websocket.send_text(
            json.dumps(
                {
                    "type": "generation_stopped",
                    "message_id": message_id,
                }
            )
        )


async def get_or_create_conversation(
    user_id: str, conversation_id: str | None, user_message: str, websocket: WebSocket
) -> str | None:
    if not conversation_id:
        conversation = ConversationOperations.create_conversation(
            user_id=user_id,
            title=user_message[:50] + "..." if len(user_message) > 50 else user_message,
        )
        if not conversation:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Failed to create conversation"})
            )
            return None

        conversation_id = conversation["id"]
        await websocket.send_text(json.dumps({"type": "conversation_id", "data": conversation_id}))
        return conversation_id

    conversation = ConversationOperations.get_conversation(conversation_id)
    if not conversation:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Conversation not found"})
        )
        return None

    if conversation["user_id"] != user_id:
        await websocket.send_text(json.dumps({"type": "error", "message": "Unauthorized"}))
        return None

    return conversation_id


async def stream_chat_response(
    websocket: WebSocket,
    user_id: str,
    user_message: str,
    conversation_id: str,
    message_id: str,
):
    messages = MessageOperations.get_conversation_messages(conversation_id)
    conversation_history = [
        {"role": msg["role"], "content": msg["content"]} for msg in messages[:-1]
    ]

    await websocket.send_text(json.dumps({"type": "stream_start", "message_id": message_id}))

    full_message = ""
    retrieved_chunks = []

    async for chunk in chat_service.generate_streaming_response(
        user_id, user_message, conversation_history, message_id
    ):
        if not active_generations.get(message_id, False):
            logger.info(f"Generation stopped for message {message_id}")
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "generation_stopped",
                        "message_id": message_id,
                    }
                )
            )
            break
        chunk_type = chunk.get("type")
        chunk_data = chunk.get("data")

        if chunk_type == "chunks":
            retrieved_chunks = chunk_data
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "chunks",
                        "data": chunk_data,
                        "message_id": message_id,
                    }
                )
            )
        elif chunk_type == "token":
            full_message += chunk_data
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "stream",
                        "content": chunk_data,
                        "message_id": message_id,
                    }
                )
            )
        elif chunk_type == "done":
            MessageOperations.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_message,
                chunks=retrieved_chunks if retrieved_chunks else None,
            )
            await websocket.send_text(json.dumps({"type": "complete", "message_id": message_id}))

    active_generations.pop(message_id, None)


async def handle_chat_message(websocket: WebSocket, user_id: str, message: dict):
    user_message = message.get("message", "").strip()
    conversation_id = message.get("conversation_id")

    if not user_message:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Empty message received"})
        )
        return

    try:
        conversation_id = await get_or_create_conversation(
            user_id, conversation_id, user_message, websocket
        )

        if not conversation_id:
            return

        MessageOperations.create_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        incoming_id = message.get("message_id")
        message_id = incoming_id if incoming_id else str(uuid.uuid4())
        active_generations[message_id] = True

        logger.info(f"Starting stream for message ID: {message_id}", "BLUE")

        await stream_chat_response(websocket, user_id, user_message, conversation_id, message_id)

    except Exception as e:
        logger.error(f"Error generating response for user {user_id}: {e}")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Failed to generate response: {e}",
                }
            )
        )


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, user_id: str = Query(...)):

    try:
        logger.info(f"Opening WebSocket for {user_id}")
        if not user_id:
            await websocket.close(code=4000, reason="Invalid user ID")
            return

        if not await check_connection_limit(user_id):
            await websocket.close(code=1008, reason="Connection limit exceeded")
            return

        await websocket.accept()

    except Exception as e:
        logger.error(f"WebSocket accept failed for user {user_id}: {str(e)}")
        return

    active_connections[user_id].add(websocket)
    connection_last_activity[websocket] = time.time()
    heartbeat_task = asyncio.create_task(heartbeat_handler(websocket))

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            connection_last_activity[websocket] = time.time()

            message_type = message.get("type")

            if message_type == "pong":
                continue

            if message_type == "stop_generation":
                await handle_stop_generation(websocket, message)
                continue

            if message_type == "chat":
                await handle_chat_message(websocket, user_id, message)
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid message type"})
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        heartbeat_task.cancel()
        await cleanup_connection(websocket, user_id)


@router.get("/test")
async def chat_test():
    return {
        "message": "Chat service is active",
        "websocket_path": "/chat/ws",
    }
