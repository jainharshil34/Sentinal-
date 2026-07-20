<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Dynamic JSX Component Safeguards
- **Never render an unguarded dynamic component tag**: When accessing dynamic components by index (e.g. `[IconA, IconB][i]`), always supply a default fallback (`const Component = list[i] || FallbackComponent`) so React never receives `undefined` as an element type.
- **Export/Import Check**: Ensure named vs default exports match expected imports for all UI components.
