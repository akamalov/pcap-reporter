# Standard project directory structure.

## 🗺️ Directory Structure

```mermaid
flowchart TD
    Root[Project Root]
    Root --> Docs[docs/]
    Root --> Tasks[tasks/]
    Root --> Gemini[.gemini/rules/]
    Root --> CLINE[.clinerules]
    Root --> SourceCode[src/]
    Root --> Test[test/]
    Root --> Utils[utils/]
    Root --> Config[config/]
    Root --> Data[data/]
    Root --> Other[Other Directories]
```

*   **Memory Files:** Specific documentation files are maintained within `docs/` and `tasks/` (See `documentation-memory.mdc`).
*   **Rules:** AI guidance rules are kept in `.gemini/rules/`.
*   **Fixes:** Document complex bug fixes in `fixes/`.
