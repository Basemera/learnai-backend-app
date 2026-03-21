"""add pgvector extension and embedding tables

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Dimension for text-embedding-3-small (OpenAI default = 1536)
_DIMS = 1536


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enable pgvector extension
    # Required for the vector column type and ANN index operators.
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # embedding_models – registry of supported embedding models
    # ------------------------------------------------------------------
    op.create_table(
        "embedding_models",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_embedding_models_name"),
    )

    # ------------------------------------------------------------------
    # book_embedding_jobs – per-book, per-model indexing job status
    # ------------------------------------------------------------------
    op.create_table(
        "book_embedding_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("book_id", sa.String(), nullable=False),
        sa.Column("embedding_model_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("chunk_size_words", sa.Integer(), nullable=False),
        sa.Column("overlap_words", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_models.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "embedding_model_id", name="uq_book_embedding_job"),
    )

    # ------------------------------------------------------------------
    # book_embedding_chunks_1536 – chunk text + vector(1536) embeddings
    #
    # One table per dimension keeps vector(N) type-safe and allows an
    # efficient ANN index per model family.
    # ------------------------------------------------------------------
    op.create_table(
        "book_embedding_chunks_1536",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("book_id", sa.String(), nullable=False),
        sa.Column("embedding_model_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(_DIMS), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # B-tree index for fast lookup by (book, model, chunk)
    op.create_index(
        "ix_book_embedding_chunks_1536_book_model_chunk",
        "book_embedding_chunks_1536",
        ["book_id", "embedding_model_id", "chunk_index"],
    )

    # ANN vector index for similarity search.
    # HNSW (requires pgvector >= 0.5.0) gives better recall and query speed
    # than IVFFLAT and does not require a pre-ANALYZE step.
    # If your managed Postgres ships an older pgvector, swap the CREATE INDEX
    # statement below for the IVFFLAT alternative in the comment.
    #
    # IVFFLAT fallback (tune `lists` to ~sqrt(num_rows)):
    #   CREATE INDEX … USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    try:
        op.execute(
            "CREATE INDEX book_embedding_chunks_1536_embedding_hnsw_idx "
            "ON book_embedding_chunks_1536 "
            "USING hnsw (embedding vector_cosine_ops)"
        )
    except Exception:
        # Older pgvector installations (< 0.5.0) do not support HNSW.
        # Fall back to IVFFLAT so that migrations still complete cleanly.
        op.execute(
            "CREATE INDEX book_embedding_chunks_1536_embedding_ivfflat_idx "
            "ON book_embedding_chunks_1536 "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS book_embedding_chunks_1536_embedding_hnsw_idx")
    op.execute("DROP INDEX IF EXISTS book_embedding_chunks_1536_embedding_ivfflat_idx")
    op.drop_index(
        "ix_book_embedding_chunks_1536_book_model_chunk",
        table_name="book_embedding_chunks_1536",
    )
    op.drop_table("book_embedding_chunks_1536")
    op.drop_table("book_embedding_jobs")
    op.drop_table("embedding_models")
