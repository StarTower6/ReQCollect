# Tasks: @-File Reference with Backend Injection

## Task List
- [x] 1. Backend model: add `referenced_files` to ChatRequest and AgentRequest — commit: e29d981
- [x] 2. Backend service: add `referenced_files` to `chat()` and `handle()`, inject file content — commit: e29d981
- [x] 3. Backend API: pass `referenced_files` in pm_chat and pm_agent endpoints — commit: e29d981
- [x] 4. Frontend ChatInput: add @-file picker with referenced file tags — commit: 818122e
- [x] 5. Frontend ChatArea: add referencedFiles/workspaceId props + events — commit: 818122e
- [x] 6. Frontend AppLayout: provide referencedFiles — commit: 818122e
- [x] 7. Frontend ChatView: inject referencedFiles, pass to ChatArea, include in SSE body — commit: 818122e
- [x] 8. Verify Python syntax — OK
- [x] 9. Verify TypeScript types — OK
- [x] 10. Commit everything — done (2 commits: e29d981, 818122e)
