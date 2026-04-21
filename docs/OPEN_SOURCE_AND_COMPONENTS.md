# Open Source Code And Components Usage

## 1. Overall Statement

This project is independently designed and implemented by the team around the education-domain sub-scene of "assistive education and psychological support" in the competition brief, with a specific focus on adolescent mental health support.

During development, the team used a number of open source frameworks, open source libraries, and official SDKs to support backend service construction, agent orchestration, retrieval-augmented generation, vector storage, OCR, monitoring, and frontend interaction.

The project does not use a third-party open source business project as the main body of the system by direct copy. Instead, it builds its own product logic and system integration on top of standard open source dependencies and official platform SDKs.

## 2. Open Source Frameworks, Libraries, And Components

### 2.1 Backend Service Layer

1. Flask
   - Usage: backend web service, API routing, service entrypoint
   - Modules: `agent/app.py`, `agent/api_gateway.py`, `agent/agent/api/*`
   - License type: BSD-3-Clause
   - Source modified: No

2. Flask-CORS
   - Usage: cross-origin request support
   - Modules: backend API service layer
   - License type: MIT
   - Source modified: No

3. FastAPI
   - Usage: reserved for high-performance gateway and future service expansion; appears in dependency and architecture design
   - Modules: environment dependency and architecture planning
   - License type: MIT
   - Source modified: No

4. Uvicorn
   - Usage: ASGI runtime support for FastAPI-style deployment
   - Modules: dependency environment
   - License type: BSD-3-Clause
   - Source modified: No

### 2.2 Agent, RAG, And Data Processing

5. LangChain / LangChain Core / LangChain Text Splitters
   - Usage: agent workflow orchestration, prompt organization, tool calling, text splitting, RAG integration
   - Modules: `agent/agent/core/*`, `agent/loader.py`, `agent/vectorstore.py`, related orchestration and retrieval modules
   - License type: MIT
   - Source modified: No

6. ChromaDB
   - Usage: vector database for domain knowledge retrieval and RAG support
   - Modules: `agent/vectorstore.py`, RAG modules
   - License type: Apache-2.0
   - Source modified: No

7. Pydantic
   - Usage: request and response schema definition, parameter validation, data model constraints
   - Modules: `agent/agent/api/schemas.py`, API data structures
   - License type: MIT
   - Source modified: No

8. Python-Dotenv
   - Usage: loading environment variables such as API keys and runtime configuration
   - Modules: backend startup and configuration loading
   - License type: BSD-3-Clause
   - Source modified: No

### 2.3 Networking, Caching, And Monitoring

9. Requests
   - Usage: HTTP calls to third-party model APIs and internal services
   - Modules: `agent/app.py`, `agent/api_gateway.py`
   - License type: Apache-2.0
   - Source modified: No

10. Aiohttp
   - Usage: asynchronous networking support
   - Modules: dependency environment and reserved async capability
   - License type: Apache-2.0
   - Source modified: No

11. Redis / Aioredis
   - Usage: cache, session state, and future memory optimization support
   - Modules: `agent/redis_client.py`, cache-related modules
   - License type: MIT
   - Source modified: No

12. Prometheus Client
   - Usage: service metrics collection and monitoring
   - Modules: monitoring and performance statistics modules
   - License type: Apache-2.0
   - Source modified: No

13. Psutil
   - Usage: system resource metrics such as CPU and memory monitoring
   - Modules: monitoring modules
   - License type: BSD-3-Clause
   - Source modified: No

### 2.4 Document And OCR Components

14. PyMuPDF
   - Usage: PDF parsing and document text extraction
   - Modules: knowledge import and document processing
   - License type: AGPL / commercial dual license
   - Source modified: No

15. Pillow
   - Usage: image processing support
   - Modules: OCR and image handling support
   - License type: MIT-CMU
   - Source modified: No

16. Pytesseract
   - Usage: OCR wrapper for text recognition
   - Modules: `agent/ocr.py`
   - License type: Apache-2.0
   - Source modified: No

### 2.5 Frontend Environment

17. WeChat Mini Program Native Framework
   - Usage: frontend interaction for student side and parent side
   - Modules: `WarnStudty/pages/*`
   - Type: official runtime and development framework provided by the WeChat Mini Program platform
   - Source modified: No

## 3. Whether Open Source Component Source Code Was Modified

The team did not modify the source code of the third-party open source frameworks, libraries, or SDKs listed above.

All third-party components are integrated through standard dependency installation, official API access, or normal SDK invocation. The project’s business logic, frontend pages, backend services, agent flow, psychological support design, and system integration are independently completed by the team.

## 4. Whether Open Source Data Or Open Source Models Were Referenced

### 4.1 Open Source Data

At the current stage, the repository does not package a large third-party public dataset as part of the source code delivery.

The project knowledge content is mainly based on self-organized domain knowledge, publicly available educational and psychological materials that can be legally整理 and structured, and later extensible domain resources.

If a specific public dataset from platforms such as ModelScope or Hugging Face is introduced in the final competition submission, the team will supplement the corresponding data source, usage purpose, and compliance note in the final report.

### 4.2 Open Source Model

The project architecture follows the competition requirement that a mainstream large model acts as the core intelligence engine.

From the current implementation, the project supports the following model access patterns:

1. Qwen / Tongyi Qianwen
   - Access method: cloud API through DashScope / Model Studio
   - Type: model ecosystem is publicly available, but the current project implementation uses API invocation rather than bundling local weight files
   - Configuration: `DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL`

2. MiniMax
   - Access method: third-party commercial API
   - Type: commercial model service, no local model weights bundled in repository
   - Configuration: `MINIMAX_API_KEY`

## 5. Whether Third-Party Commercial Model APIs Were Called

Yes. The current project code uses third-party commercial model APIs.

Mainly including:

1. Qwen / DashScope
   - Usage: dialogue generation, agent reply generation, RAG-based answer generation
   - Invocation: official SDK / API call in backend service
   - Requirement: valid API key

2. MiniMax
   - Usage: dialogue generation and alternative model access path
   - Invocation: HTTP API call in backend service
   - Requirement: valid API key

## 6. Independently Developed Parts

The following key parts are independently developed by the team:

- project topic selection and problem definition
- system architecture design
- student-side and parent-side Mini Program pages
- backend API composition and service integration
- agent interaction process for psychological support
- RAG retrieval integration process
- user state recording, report generation, and early-warning related business logic
- deployment documentation, model selection documentation, commercialization documentation
- overall competition-oriented engineering integration

## 7. Additional Note

The license information above is organized according to the commonly published license types of the corresponding projects. If the competition organizer requires a stricter compliance appendix, the team can further provide version numbers, official URLs, and LICENSE file references for each component.
