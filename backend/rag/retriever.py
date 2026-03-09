import logging
from typing import Optional
from backend.rag.embedder import embedder
from backend.models.schemas import SourceChunk

logger = logging.getLogger(__name__)

LEVEL_RANGES = {
    "2.0": ["初级", "2.0", "2.5"],
    "2.5": ["初级", "2.0", "2.5"],
    "3.0": ["中级", "3.0", "3.5"],
    "3.5": ["中级", "3.0", "3.5"],
    "4.0": ["高级", "4.0", "4.5"],
    "4.5": ["高级", "4.0", "4.5"],
}


class KnowledgeRetriever:
    def retrieve(
        self,
        query: str,
        user_level: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> tuple[list[SourceChunk], bool]:
        from backend.config import settings

        k = top_k or settings.top_k
        col = embedder.get_collection()
        total = col.count()
        fetch_k = min(k * 2, total)
        if fetch_k == 0:
            return [], True

        results = col.query(
            query_texts=[query],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"],
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        chunks = [
            SourceChunk(
                text=d,
                source_file=m["source_file"],
                section_title=m["section_title"],
                skill_level=m["skill_level"],
                distance=dist,
            )
            for d, m, dist in zip(docs, metas, distances)
        ]

        if user_level and user_level in LEVEL_RANGES:
            keywords = LEVEL_RANGES[user_level]
            matched = [
                c for c in chunks
                if any(kw in c.skill_level for kw in keywords) or c.skill_level == "all"
            ]
            unmatched = [c for c in chunks if c not in matched]
            chunks = (matched + unmatched)[:k]
        else:
            chunks = chunks[:k]

        is_uncertain = len(chunks) == 0 or chunks[0].distance > settings.similarity_threshold

        best_dist = f"{chunks[0].distance:.3f}" if chunks else "N/A"
        logger.info(f"Retrieved {len(chunks)} chunks; best_distance={best_dist}; uncertain={is_uncertain}")
        return chunks, is_uncertain


retriever = KnowledgeRetriever()
