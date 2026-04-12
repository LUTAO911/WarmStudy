# Agent Backend Service

暖学帮智能体后端服务 (WarmStudy Agent Backend)

## Overview

This is the AI agent backend for the WarmStudy (暖学帮) application, providing intelligent tutoring and study assistance features.

## Features

- RAG-based question answering
- Document loading and embedding
- Vector store integration
- OCR support
- Redis-based caching

## Installation

```bash
pip install -e .
```

## Development

```bash
pip install -e ".[dev]"
```

## Testing

```bash
pytest tests/ -v --cov=agent
```
