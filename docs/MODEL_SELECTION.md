# Model Selection

## 1. Current Conclusion

The current WarmStudy repository is standardized on a single model path:

- Qwen via DashScope API

This keeps deployment, debugging, and competition demo preparation simpler and more stable.

## 2. Recommended Default Setup

Use the following configuration in the current project:

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
```

Recommended model choice:

- default interactive model: `qwen-plus`
- higher-quality upgrade model: `qwen-max`

## 3. Why Qwen Is Kept

- already integrated across the current backend and RAG workflow
- easier to explain in competition materials
- lower maintenance cost than keeping multiple providers in parallel
- enough for the current student support, parent guidance, and RAG answer generation scenarios

## 4. Suggested Routing Strategy

### 4.1 Daily Dialogue

- use `qwen-plus`

### 4.2 More Complex Responses

- switch to `qwen-max`

### 4.3 RAG-Based Answers

- keep the same Qwen path for consistency

## 5. Engineering Recommendation

The repository should keep one clear provider path unless there is a strong product reason to add another one later. For the current competition version, Qwen / DashScope is the only retained interface.
