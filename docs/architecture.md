# Architecture

This project is a mini AI-powered learning ecosystem with six core systems:

## A. Client App (Frontend)

What the learner sees and uses.

Responsibilities:
- Read e-books in the app
- Select text
- Click: Simplify, Explain more, Ask AI
- Do flashcards and quizzes
- View progress dashboard

Tech options:
- Mobile: Flutter (one codebase for Android and iOS)
- Web: React or Next.js

Note: Since the current focus is Android, Flutter is a strong choice.

## B. Backend API (Main Brain)

Handles:
- User accounts
- Books
- Progress tracking
- Assessments
- Calls to AI models

Tech options:
- Python + FastAPI (excellent for AI integration)
- Node.js + NestJS

Why FastAPI:
- Very fast
- Easy AI integration
- Clean API design

## C. E-Book Processing System

You need to:
- Upload books (PDF or EPUB)
- Extract text
- Break into chunks
- Save for AI use

Flow:
- Book upload
- Text extraction
- Chunking
- Store in DB or vector DB

Tools:
- PDF: pdfplumber, PyMuPDF
- EPUB: ebooklib
- Text chunking: custom Python logic

## D. AI Layer (Core Intelligence)

What AI will do:
- Simplify text
- Explain selected passages
- Give extra info
- Improve student prompts
- Suggest best prompts
- Generate flashcards
- Create quiz questions

How:
- Send structured prompts to LLMs

Options:
- OpenAI API (GPT-4.1 or GPT-4o-mini)
- Open-source models via Ollama or HuggingFace Inference API

Start with OpenAI API for faster prototyping.

## E. Retrieval System (Book-Aware AI)

RAG: Retrieval Augmented Generation for book-based answers.

Flow:
- User selects text or topic
- Find related chunks from the book
- Send to AI with prompt
- AI answers based on that context

Tools:
- Vector DB: Pinecone, Weaviate, Chroma (local)
- Embeddings: OpenAI embeddings or SentenceTransformers

This enables:
- Explain chapter 3
- Summarize this section
- Test me from this topic

## F. Learning and Analytics System

Tracking progress and personalization.

Data to store:
- Books read (percent progress)
- Flashcard attempts
- Quiz scores
- Topics struggled with
- Strength and weakness profile

Features:
- Spaced repetition for flashcards
- Adaptive difficulty
- Personalized prompt suggestions

Database:
- PostgreSQL (main DB)
- Redis (caching sessions)
