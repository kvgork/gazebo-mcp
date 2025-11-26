# Architecture Diagrams

This directory contains source files for all architecture diagrams used in the project documentation.

## Diagrams

All diagrams are written in Mermaid format and are embedded directly in `docs/ARCHITECTURE.md`.

### Available Diagrams

1. **System Architecture** - Complete system overview showing all layers
2. **Component Interaction** - How tool modules interact with utilities and bridge
3. **Tool Category Breakdown** - Mind map of all 18 MCP tools
4. **Model Spawning Workflow** - Sequence diagram for spawning models
5. **Sensor Data Reading Workflow** - Sequence diagram for reading sensor data
6. **World Generation Workflow** - Sequence diagram for creating worlds
7. **Connection Management Workflow** - Sequence diagram for ROS2 connection lifecycle
8. **Error Handling Flow** - Sequence diagram showing error propagation

## Viewing Diagrams

### In GitHub

GitHub automatically renders Mermaid diagrams in markdown files. Simply view `docs/ARCHITECTURE.md` on GitHub.

### Locally

Use any of these tools to view Mermaid diagrams:

1. **VS Code Extension**: Install "Markdown Preview Mermaid Support"
2. **Mermaid Live Editor**: https://mermaid.live/
3. **Online Viewers**: Most markdown viewers support Mermaid

### Exporting to Images

To export diagrams as PNG/SVG for presentations:

```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Export to PNG
mmdc -i docs/ARCHITECTURE.md -o diagrams/architecture.png

# Export to SVG
mmdc -i docs/ARCHITECTURE.md -o diagrams/architecture.svg
```

## Editing Diagrams

1. Find the diagram in `docs/ARCHITECTURE.md`
2. Edit the Mermaid code between \`\`\`mermaid and \`\`\`
3. Preview changes using one of the viewing methods above
4. Commit changes to documentation

## Mermaid Syntax Reference

- **Graph/Flowchart**: `graph TB` (top-bottom), `graph LR` (left-right)
- **Sequence Diagram**: `sequenceDiagram`
- **Mind Map**: `mindmap`
- **Class Diagram**: `classDiagram`

Full documentation: https://mermaid.js.org/

## Phase 8 Enhancement

These diagrams were created as part of Phase 8 (Production Hardening) to provide visual documentation of the system architecture, component interactions, and key workflows.

**Created**: 2025-11-20
**Status**: Complete
