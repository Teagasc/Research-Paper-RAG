import asyncio
import os
import re
from typing import Any, Dict, List, Set

from dotenv import load_dotenv
import reflex as rx
from ragflow_sdk import RAGFlow

load_dotenv()

# Retrieve configuration from environment variables for RAGFlow.
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY")
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL")
AGENT_NAME = os.getenv("AGENT_NAME") or os.getenv("RAGFLOW_AGENT_NAME")
ACRES_DATABASE = os.getenv("ACRES_DATABASE")  # New env var for the database name

if not RAGFLOW_API_KEY:
    raise Exception("Please set RAGFLOW_API_KEY environment variable.")
if not ACRES_DATABASE:
    raise Exception("Please set ACRES_DATABASE environment variable.")

# Initialize the RAGFlow object.
rag_object = RAGFlow(api_key=RAGFLOW_API_KEY, base_url=RAGFLOW_BASE_URL)
assistant_list = rag_object.list_chats(name=AGENT_NAME)
if not assistant_list:
    raise Exception(f"No chat agent found with name '{AGENT_NAME}'")
assistant = assistant_list[0]

# Create (or get) the ACRES dataset.
try:
    acres_dataset = rag_object.create_dataset(name=ACRES_DATABASE)
except Exception as e:
    if "Duplicated dataset name" in str(e):
        datasets = rag_object.list_datasets()  # Assumes a list_datasets method exists.
        acres_dataset = next((ds for ds in datasets if ds.name == ACRES_DATABASE), None)
        if acres_dataset is None:
            raise Exception(f"Dataset '{ACRES_DATABASE}' exists but could not be retrieved.")
    else:
        raise e

def remove_duplicate_trailing(text: str, min_length: int = 5) -> str:
    n = len(text)
    if n < 2 * min_length:
        return text
    for l in range(n // 2, min_length - 1, -1):
        if text[-2 * l:-l] == text[-l:]:
            return text[:-l]
    return text

def clean_response(text: str) -> str:
    cleaned = re.sub(r"##\d+\$\$", "", text)
    return remove_duplicate_trailing(cleaned, min_length=5)

def serialize_chunk(chunk) -> dict:
    return {
        "id": chunk.id,
        "content": chunk.content,
        "document_id": getattr(chunk, "document_id", None),
        "document_name": getattr(chunk, "document_name", None),
        "position": getattr(chunk, "position", None),
        "dataset_id": getattr(chunk, "dataset_id", None),
        "similarity": getattr(chunk, "similarity", None),
        "vector_similarity": getattr(chunk, "vector_similarity", None),
        "term_similarity": getattr(chunk, "term_similarity", None),
    }

def extract_source_links_from_chunks(chunks: List[Dict[str, Any]]) -> Set[str]:
    links = set()
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        if doc_id:
            doc_name = chunk.get("document_name", "")
            ext = ""
            if doc_name and "." in doc_name:
                ext = doc_name.split(".")[-1]
            link = f"https://hcux402.teagasc.net//document/{doc_id}?ext={ext}&prefix=document"
            links.add(link)
    return links

class QA(rx.Base):
    question: str
    answer: str
    sources: List[str] = []       # Field for storing source links.
    show_sources: bool = False    # Controls the dropdown visibility.
    hide_answer: bool = False     # Temporary flag to hide the answer while cleaning.

class State(rx.State):
    chats: Dict[str, List[QA]] = {}
    current_chat: str = ""
    question: str = ""
    processing: bool = False
    new_chat_name: str = ""
    show_sources: bool = False
    _rag_session: Any = None

    # Variables for document selection.
    selected_document: Dict[str, Any] = None
    document_chunks: List[Dict[str, Any]] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chats = {"Default": []}
        self.current_chat = "Default"
        opener = QA(
            question="",
            answer="Hi, I'm your Research Paper Assistant. Ask me any question about published Teagasc Research Papers.",
            sources=[],
            show_sources=False,
            hide_answer=False,
        )
        self.chats["Default"].append(opener)
        self._rag_session = assistant.create_session()

    def create_chat(self):
        self.current_chat = self.new_chat_name
        self.chats[self.new_chat_name] = []

    def delete_chat(self):
        del self.chats[self.current_chat]
        if not self.chats:
            self.chats = {"Default": []}
        self.current_chat = list(self.chats.keys())[0]

    def set_chat(self, chat_name: str):
        self.current_chat = chat_name

    @rx.var(cache=False)
    def chat_titles(self) -> List[str]:
        return list(self.chats.keys())

    @rx.var(cache=False)
    def document_names(self) -> List[str]:
        docs = acres_dataset.list_documents(page=1, page_size=100)
        return [doc.name for doc in docs]

    @rx.var(cache=False)
    def documents(self) -> List[Dict[str, Any]]:
        docs = acres_dataset.list_documents(page=1, page_size=100)
        return [{"id": doc.id, "name": doc.name} for doc in docs]

    async def process_question(self, form_data: Dict[str, Any]):
        self.show_sources = False
        question = form_data["question"]
        if question == "":
            return
        async for _ in self.ragflow_process_question(question):
            yield

    async def similarity_search_knowledge1(self, question: str) -> List[Dict[str, Any]]:
        """
        Performs a similarity search using the RAGFlow.retrieve API and returns the serialized chunks.
        """
        try:
            chunks = await asyncio.to_thread(lambda: rag_object.retrieve(
                question=question,
                dataset_ids=[acres_dataset.id],
                page=1,
                page_size=30,
                similarity_threshold=0.3,
                vector_similarity_weight=0.3,
                top_k=1024,
                rerank_id=None,
                keyword=False
            ))
            serialized_chunks = [
                serialize_chunk(chunk)
                for chunk in chunks
                if chunk is not None and getattr(chunk, "content", None) is not None
            ]
            return serialized_chunks
        except Exception as e:
            print(f"Error in similarity_search_knowledge1: {e}")
            return []

    async def ragflow_process_question(self, question: str):
        qa = QA(question=question, answer="", sources=[], show_sources=False, hide_answer=False)
        self.chats[self.current_chat].append(qa)
        self.processing = True
        yield
        accumulated_answer = ""
        source_links = set()
        try:
            kwargs = {}
            if self.selected_document and self.document_chunks:
                print("Passing selected_doc context only.")
                kwargs["selected_doc"] = self.document_chunks
                kwargs["knowledge1"] = ""  # disable full knowledge search when a specific document is selected
                # Use sources from the selected document
                source_links = extract_source_links_from_chunks(self.document_chunks)
            else:
                print("No specific document selected; performing similarity search for knowledge1.")
                all_chunks = await self.similarity_search_knowledge1(question)
                kwargs["knowledge1"] = all_chunks
                kwargs["selected_doc"] = ""
                source_links = extract_source_links_from_chunks(all_chunks)

            # Ask the assistant with the additional context in kwargs.
            for message in self._rag_session.ask(question, stream=True, **kwargs):
                if hasattr(message, "content") and message.content:
                    new_part = message.content[len(accumulated_answer):]
                    accumulated_answer = message.content
                    filtered_part = re.sub(r"##\d+\$\$", "", new_part)
                    self.chats[self.current_chat][-1].answer += filtered_part
                    if hasattr(message, "reference") and message.reference:
                        for chunk in message.reference:
                            document_id = None
                            document_name = None
                            if isinstance(chunk, dict):
                                document_id = chunk.get("document_id")
                                document_name = chunk.get("document_name")
                            else:
                                document_id = getattr(chunk, "document_id", None)
                                document_name = getattr(chunk, "document_name", None)
                            if document_id:
                                ext = ""
                                if document_name and "." in document_name:
                                    ext = document_name.split(".")[-1]
                                link = f"https://hcux402.teagasc.net//document/{document_id}?ext={ext}&prefix=document"
                                source_links.add(link)
                    self.chats = self.chats
                    yield
        except Exception as e:
            self.chats[self.current_chat][-1].answer += f"\nError: {e}"
            self.chats = self.chats

        self.chats[self.current_chat][-1].hide_answer = True
        self.chats = self.chats
        final_answer = clean_response(self.chats[self.current_chat][-1].answer)
        await asyncio.sleep(0.1)
        self.chats[self.current_chat][-1].answer = final_answer
        self.chats[self.current_chat][-1].hide_answer = False
        self.chats = self.chats

        # Set sources based on which branch was used.
        # If using similarity search (knowledge1), show those sources.
        # If a document is selected, show the selected document's sources.
        if self.selected_document and self.document_chunks:
            self.chats[self.current_chat][-1].sources = list(extract_source_links_from_chunks(self.document_chunks))
        else:
            self.chats[self.current_chat][-1].sources = list(source_links)
        self.chats = self.chats

        self.processing = False
        await asyncio.sleep(1)
        self.chats[self.current_chat][-1].show_sources = True
        self.chats = self.chats

    async def select_document(self, doc: Dict[str, Any]):
        """
        Select a document and retrieve its chunks.
        """
        self.selected_document = doc
        documents = await asyncio.to_thread(lambda: acres_dataset.list_documents(id=doc["id"]))
        if not documents:
            self.document_chunks = []
        else:
            document_obj = documents[0]
            chunks = await asyncio.to_thread(lambda: document_obj.list_chunks(page=1, page_size=200))
            self.document_chunks = [
                serialize_chunk(chunk)
                for chunk in chunks
                if chunk is not None and getattr(chunk, "content", None) is not None
            ]
            for chunk in self.document_chunks:
                print("Chunk content:", chunk["content"])

    def clear_selected_document(self):
        self.selected_document = None
        self.document_chunks = []

    @rx.var(cache=False)
    def valid_document_chunks(self) -> List[Dict[str, Any]]:
        """Return only chunks that have a non-null 'content' property."""
        return [chunk for chunk in self.document_chunks if chunk.get("content") is not None]

    @rx.var(cache=False)
    def selected_document_text(self) -> str:
        if self.selected_document:
            return f"Using document: {self.selected_document.get('name', '')}"
        return ""
