import logging
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIBuilderEmbeddingFunction(EmbeddingFunction):
    """Chroma-compatible embedding function using ai-builders-coach API."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:
        response = self._client.embeddings.create(model=self._model, input=input)
        return [item.embedding for item in response.data]


class KnowledgeEmbedder:
    def __init__(self):
        self._client = None
        self._collection = None

    def _get_client(self):
        if self._client is None:
            from backend.config import settings
            self._client = chromadb.PersistentClient(
                path=str(settings.chroma_db_path)
            )
        return self._client

    def _get_ef(self):
        from backend.config import settings
        return AIBuilderEmbeddingFunction(
            api_key=settings.ai_builder_token,
            base_url=settings.ai_builder_base_url,
            model=settings.embedding_model,
        )

    def init_collection(self, force_reload: bool = False) -> int:
        from backend.config import settings
        client = self._get_client()
        ef = self._get_ef()

        if force_reload:
            try:
                client.delete_collection(settings.chroma_collection_name)
                logger.info("Deleted existing collection for reload")
            except Exception:
                pass
            self._collection = None

        self._collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )

        count = self._collection.count()
        if count == 0:
            logger.info("Collection empty, loading knowledge base...")
            from backend.rag.loader import KnowledgeLoader
            loader = KnowledgeLoader(settings.knowledge_base_path)
            chunks = loader.load_all()
            self._index_chunks(chunks)
            logger.info(f"Indexed {len(chunks)} chunks")
            return len(chunks)

        logger.info(f"Collection has {count} existing chunks, skipping load")
        return count

    def _index_chunks(self, chunks):
        BATCH = 50
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i : i + BATCH]
            self._collection.add(
                ids=[c.chunk_id for c in batch],
                documents=[c.text for c in batch],
                metadatas=[
                    {
                        "source_file": c.source_file,
                        "section_title": c.section_title,
                        "skill_level": c.skill_level,
                    }
                    for c in batch
                ],
            )
            logger.info(f"Indexed batch {i // BATCH + 1}: {len(batch)} chunks")

    def get_collection(self):
        if self._collection is None:
            raise RuntimeError("Call init_collection() first")
        return self._collection


embedder = KnowledgeEmbedder()
