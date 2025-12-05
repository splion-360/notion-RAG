from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL, setup_logger

logger = setup_logger(__name__)


class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            cls._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully", "GREEN")
        return cls._model

    @classmethod
    def generate_embedding(cls, text: str) -> list[float]:
        model = cls.get_model()
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    @classmethod
    def generate_embeddings_batch(cls, texts: list[str]) -> list[list[float]]:
        model = cls.get_model()
        embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=True)
        return [emb.tolist() for emb in embeddings]


embedding_service = EmbeddingService()
