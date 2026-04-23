# Open Source Code And Components Usage

## 1. Overall Statement

This project is independently designed and implemented by the team around the education-domain psychological support scenario in the competition brief.

The team uses open source frameworks, libraries, and official SDKs for backend services, agent orchestration, retrieval-augmented generation, vector storage, OCR, monitoring, and frontend interaction. The project does not directly copy a third-party business project as the main body of the system.

## 2. Main Open Source Frameworks And Components

1. Flask
2. Flask-CORS
3. FastAPI
4. Uvicorn
5. LangChain / LangChain Core / Text Splitters
6. ChromaDB
7. Pydantic
8. Python-Dotenv
9. Requests
10. Aiohttp
11. Redis / Aioredis
12. Prometheus Client
13. Psutil
14. PyMuPDF
15. Pillow
16. Pytesseract
17. Native frontend framework based on WeChat Mini Program technology

## 3. Whether Open Source Component Source Code Was Modified

The team did not modify the source code of the third-party open source frameworks, libraries, or SDKs listed above. Business logic and system integration are independently developed.

## 4. Whether Open Source Data Or Open Source Models Were Referenced

### 4.1 Open Source Data

The repository does not package a large third-party public dataset as part of source delivery. Knowledge content is based on self-organized domain material and later-importable domain resources.

### 4.2 Model Access

The current implementation keeps one model access pattern:

1. Qwen / Tongyi Qianwen
   - Access method: cloud API through DashScope / Model Studio
   - Type: API invocation, no local model weights bundled in repository
   - Configuration: `DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL`

## 5. Whether Third-Party Commercial Model APIs Were Called

Yes.

1. Qwen / DashScope
   - Usage: dialogue generation, agent reply generation, RAG-based answer generation
   - Invocation: official SDK / API call in backend service
   - Requirement: valid API key

## 6. Independently Developed Parts

- project topic selection and problem definition
- system architecture design
- student-side and parent-side App frontend pages built with WeChat Mini Program technology
- backend API composition and service integration
- agent interaction flow for psychological support
- RAG retrieval integration
- user state recording, report generation, and early-warning related business logic
- deployment and competition documents

## 7. Additional Note

If the competition organizer requires a stricter compliance appendix, the team can further provide version numbers, official URLs, and LICENSE file references for each component.
