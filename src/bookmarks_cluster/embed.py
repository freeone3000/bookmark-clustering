from typing import NamedTuple, Tuple

import lmstudio as lms
import psycopg
import numpy as np

from .summarize import Summary

EMBED_MODEL = "text-embedding-qwen3-embedding-8b"
EmbeddingSet = dict[str, Tuple[str, np.ndarray]]

def _embed_chunk(summary_batch: list[Summary]) -> list[list[float]]:
    """
    Given a batch of summaries, uses a local LLM to generate a batch of embeddings for the vector
    :return: A list of embedding vectors, with length equal to the input batch. Indexes are kept consistent.
        Second dimension is 4096.
    """
    import logging
    from openai import Client

    lms.embedding_model(EMBED_MODEL) # ensures embedding model is loaded

    tf = lambda summary: f"# {summary.title}\n\n{summary.summary}"

    try:
        client = Client(base_url="http://localhost:1234/v1", api_key="lm-studio")
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=[tf(s) for s in summary_batch],
        )
        embedding_vectors = [d.embedding for d in response.data]
        logging.info(f"Successfully generated embedding using LM Studio")
        return embedding_vectors
    except Exception as e:
        logging.error(f"Failed to generate embedding using LM Studio: {e}")
        raise

def embed_all(summaries: list[Summary], conn: psycopg.Connection) -> EmbeddingSet:
    from .db import get_embeddings, write_embedding

    embeddings: EmbeddingSet = {k: (v[0], np.array(v[1])) for k, v in get_embeddings(conn).items()}
    # TODO magic number
    _BATCH_SIZE = 4 # from lms
    summaries = [summary for summary in summaries if summary.url not in embeddings]
    summary_chunks: list[list[Summary]] = [summaries[i:i+_BATCH_SIZE] for i in range(0, len(summaries), _BATCH_SIZE)]
    del summaries

    while summary_chunks:
        summary_chunk: list[Summary] = summary_chunks.pop(0)
        embedding_chunk: list[list[float]] = _embed_chunk(summary_chunk)
        for (summary, embedding) in zip(summary_chunk, embedding_chunk):
            write_embedding(summary.url, summary.title, embedding, conn)
            embeddings[summary.url] = (summary.title, np.array(embedding))
    return embeddings