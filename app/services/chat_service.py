import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE, setup_logger
from app.database.operations import PageChunkOperations
from app.services.embedding_service import embedding_service

logger = setup_logger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str


class ChatService:

    def __init__(
        self,
        active_generations: dict[str, bool],
        model: str = OLLAMA_MODEL,
        base_url: str = OLLAMA_BASE_URL,
    ):
        self.base_url = base_url
        self.model_name = model
        self.active_generations = active_generations
        logger.info(f"ChatService initialized with {model}", "GREEN")

    def _create_search_tool(self, user_id: str, chunks_callback):

        @tool
        def search_notion_pages(query: str) -> str:
            """
            Search through user's Notion pages using similarity.

            Args:
            - query: str - The search query to find relevant Notion page content

            Returns:
            - str - Formatted search results with page titles and content snippets
            """
            logger.info(f"Tool called: search_notion_pages with query: {query}", "CYAN")

            query_embedding = embedding_service.generate_embedding(query)

            chunks = PageChunkOperations.search_similar_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=5,
            )

            chunks_callback(chunks)

            if not chunks:
                return "No relevant information found in your Notion pages."

            result_parts = []
            for i, chunk in enumerate(chunks, 1):
                result_parts.append(
                    f"[Result {i}]\n"
                    f"Page: {chunk['page_title']}\n"
                    f"Content: {chunk['chunk_content']}\n"
                    f"Relevance: {chunk['similarity_score']:.1%}\n"
                )

            logger.info(f"Found {len(chunks)} relevant chunks", "GREEN")
            return "\n".join(result_parts)

        return search_notion_pages

    def _create_agent_graph(self, user_id: str, chunks_callback):
        search_tool = self._create_search_tool(user_id, chunks_callback)
        tools = [search_tool]

        llm = ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=OLLAMA_TEMPERATURE,
        )
        llm_with_tools = llm.bind_tools(tools)

        def should_continue(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        def call_model(state: AgentState):
            messages = state["messages"]
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        workflow = StateGraph(AgentState)

        workflow.add_node("agent", call_model)
        workflow.set_entry_point("agent")
        workflow.add_node("tools", ToolNode(tools))

        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")
        return workflow.compile()

    async def generate_streaming_response(
        self,
        user_id: str,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
        message_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:

        if not message_id:
            message_id = str(uuid.uuid4())

        logger.info(f"Processing chat for user {user_id}, message: {message_id}", "CYAN")

        system_prompt = """You are a helpful assistant that answers questions based on the user's Notion pages.

                        When a user asks a question:
                        1. Use the search_notion_pages (if necessary) tool to find relevant information
                        2. Based on the search results, provide a helpful answer
                        3. Cite which pages you're referencing

                        INSTRUCTIONS:
                        1. Base your answers strictly on the provided context when available.
                        2. If the context lacks the answer but it is a universal fact, provide the fact.
                        3. Otherwise reply: "I'm sorry, but I couldn't find any relevant information in the provided documents."
                        4. Keep responses concise, professional, and ALWAYS use MARKDOWN formatting.

                       """

        messages = [SystemMessage(content=system_prompt)]

        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        initial_state = AgentState(
            messages=messages,
            user_id=user_id,
        )

        retrieved_chunks = []

        def chunks_callback(chunks):
            nonlocal retrieved_chunks
            retrieved_chunks = chunks

        graph = self._create_agent_graph(user_id, chunks_callback)
        full_response = ""
        chunks_sent = False

        async for event in graph.astream(initial_state, stream_mode="values"):
            last_message = event["messages"][-1]

            if isinstance(last_message, ToolMessage):
                logger.info("Tool execution completed", "GREEN")
                if retrieved_chunks and not chunks_sent:
                    yield {"type": "chunks", "data": retrieved_chunks}
                    chunks_sent = True
                continue

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                logger.info(f"Agent calling {len(last_message.tool_calls)} tool(s)", "CYAN")
                continue

            if isinstance(last_message, AIMessage) and last_message.content:
                if not full_response:
                    yield {"type": "stream_start", "data": None}

                content = last_message.content
                if content != full_response:
                    new_content = content[len(full_response) :]
                    full_response = content

                    for char in new_content:
                        if not self.active_generations.get(message_id, True):
                            logger.info(f"Generation stopped for message {message_id}")
                            yield {"type": "generation_stopped", "data": None}
                            return

                        yield {"type": "token", "data": char}

        if self.active_generations.get(message_id, True):
            yield {"type": "done", "data": None}
