# Plan: @-File Reference with Backend Injection

## 1. Task Understanding

Enable users to reference workspace files via `@` in the chat input, sending the referenced file paths to the backend, which injects the file content as system context messages. The existing FileTreePanel already supports a "reference" (⊕) mechanism, but the ChatInput doesn't have an `@`-file picker, and the backend doesn't accept/process referenced files.

**Core flow:**
1. User types `@` in ChatInput → file picker dropdown appears → user selects a file → file path added to `referencedFiles`
2. User sends message → `referenced_files` array sent in the SSE request
3. Backend API endpoints accept `referenced_files` field → pass to service layer
4. Service layer reads each referenced file's content from DataStore and injects it as system context message before the LLM call

## 2. Changes Summary

### Backend (3 files)
- **`app/models/pm.py`** — Add `referenced_files: list[str]` to `ChatRequest` and `AgentRequest`
- **`app/services/pm_agent_service.py`** — Add `referenced_files` param to `chat()` and `handle()`; inject file content after workspace_context
- **`app/api/pm.py`** — Pass `referenced_files` from request to service calls in `pm_chat` and `pm_agent`

### Frontend (4 files)
- **`reqcollect-web/src/components/chat/ChatInput.vue`** — Add `@`-detection, file picker dropdown, referenced file tags
- **`reqcollect-web/src/components/chat/ChatArea.vue`** — Add `referencedFiles` and `workspaceId` props; pass to ChatInput; emit reference events
- **`reqcollect-web/src/views/ChatView.vue`** — Inject `referencedFiles` from AppLayout; pass to ChatArea; include `referenced_files` in SSE body; clear after send
- **`reqcollect-web/src/components/layout/AppLayout.vue`** — Provide `referencedFiles` ref via provide/inject so ChatView can access it

## 3. Data Model Changes

### ChatRequest (app/models/pm.py)
```python
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    use_knowledge: bool = False
    workspace_id: str = ""
    referenced_files: list[str] = []
```

### AgentRequest (app/models/pm.py)
```python
class AgentRequest(BaseModel):
    message: str
    session_id: str = "default"
    mode: str = "one_shot"
    use_knowledge: bool = False
    workspace_id: str = ""
    referenced_files: list[str] = []
```

## 4. Acceptance Criteria

- [ ] P0: `ChatRequest` and `AgentRequest` accept `referenced_files` field (backend model)
- [ ] P0: Backend `PMAgentService.chat()` accepts `referenced_files` and injects file contents as system context
- [ ] P0: Backend `PMAgentService.handle()` passes `referenced_files` through to `chat()`
- [ ] P0: API endpoints `/api/pm/chat` and `/api/pm/agent` pass `referenced_files` from request to service
- [ ] P0: ChatInput detects `@` and shows file picker dropdown; selecting a file adds it to referenced files
- [ ] P0: Referenced file tags shown in ChatInput with remove capability
- [ ] P0: SSE request includes `referenced_files` array; files cleared after send
- [ ] P1: File picker shows workspace files fetched from API with search filter

## 5. Risk and Dependencies

- Depends on existing `DataStore.read_workspace_file()` — confirmed available
- Depends on existing `fetchWorkspaceFiles()` API — confirmed available
- ❗ `readSSEStream` in `client.ts` posts to `/api/pm/agent` — the `referenced_files` field will be included in the JSON body, no client.ts changes needed since it passes `body` directly
- Frontend uses provide/inject pattern — AppLayout already has `referencedFiles` ref, we just need to add `provide()`

## 6. Implementation Steps (ordered)

1. Edit `app/models/pm.py` — add `referenced_files` to ChatRequest and AgentRequest
2. Edit `app/services/pm_agent_service.py` — add `referenced_files` to `chat()` and `handle()`, implement injection logic
3. Edit `app/api/pm.py` — pass `referenced_files` in `pm_chat` and `pm_agent` endpoints
4. Edit `reqcollect-web/src/components/chat/ChatInput.vue` — add `@`-file picker with referenced file tags
5. Edit `reqcollect-web/src/components/chat/ChatArea.vue` — add `referencedFiles` and `workspaceId` props, wire events
6. Edit `reqcollect-web/src/components/layout/AppLayout.vue` — add `provide('referencedFiles', referencedFiles)`
7. Edit `reqcollect-web/src/views/ChatView.vue` — inject referencedFiles, pass to ChatArea, include in SSE body
8. Verify Python syntax
9. Verify TypeScript types
10. Commit
