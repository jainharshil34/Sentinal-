# Sentinal Workspace Agent Rules

## React Component & Dynamic JSX Safeguards
1. **Dynamic Component Guard**: When indexing into arrays or lookups to render dynamic JSX components (e.g. `[IconA, IconB][index]`), ALWAYS provide a safe default fallback component (`const Icon = iconList[idx] || DefaultIcon`) to ensure the JSX tag is never `undefined`.
2. **Export / Import Integrity**: Verify all imported subcomponents are valid functions/classes before rendering to prevent React `Element type is invalid: ... got: undefined` runtime errors.
