# Project Information Summary Form

The following text is prepared in a competition-friendly format and can be directly adapted into the required summary form.

## 1. Project Name

WarmStudy（暖学帮）- 青少年心理关怀智能体系统

## 2. Competition Direction

Education direction

## 3. Selected Sub-Scene

Assistive education with emphasis on “助育” and psychological support for adolescents

## 4. Project Background

Adolescent mental health issues have become an increasingly prominent problem in school and family settings. Students often lack low-threshold emotional expression channels, parents have difficulty identifying emotional trends in time, and schools need more efficient tools for early support and light intervention. Based on this pain point, the project designs an intelligent agent system for adolescent psychological care.

## 5. Core Problem To Solve

The project aims to solve the following practical problems:

1. students have no convenient, continuous, and low-pressure channel for emotional expression
2. parents cannot easily understand long-term emotional trends or obtain structured communication suggestions
3. schools lack digital tools for lightweight psychological support, early discovery, and follow-up observation

## 6. Project Positioning

WarmStudy is positioned as an adolescent psychological care AI assistant platform for school and family scenarios, rather than a diagnostic or treatment tool.

## 7. Core Functions

1. student-side psychological support dialogue
2. daily emotional check-in and status recording
3. parent-side AI dialogue and trend view
4. domain knowledge retrieval based on psychological knowledge base
5. crisis clue detection and warning support
6. report and follow-up information support

## 8. Technical Route

The project adopts the following technical route:

- large model as the intelligence core
- RAG for domain knowledge retrieval enhancement
- tool calling and workflow orchestration for functional integration
- frontend and backend integrated prototype with WeChat Mini Program frontend and Python backend service

## 9. Main Technical Components

- frontend: WeChat Mini Program
- backend: Flask-based service architecture
- agent framework: LangChain-related components
- vector database: ChromaDB
- model access: Qwen / DashScope API, MiniMax API
- deployment: local Python environment and Docker-oriented deployment path

## 10. Innovation Highlights

1. focuses on the educational sub-scene of adolescent psychological care rather than generic Q&A
2. forms a student-parent-school support loop
3. combines domain knowledge retrieval, emotional support, and warning capability in one prototype
4. keeps both engineering deliverability and future commercialization potential

## 11. Deployment Form

The current version supports local deployment or cloud server deployment. The main recommendation for competition demo is API-based model access with backend service startup through Python environment.

## 12. Expected Value

- improve the accessibility of adolescent emotional support
- help parents understand emotional change trends
- provide schools with a digital support tool for lightweight psychological care
- demonstrate the practical value of large model plus agent technology in educational scenarios
