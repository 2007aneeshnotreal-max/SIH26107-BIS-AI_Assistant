# API notes

Interactive OpenAPI documentation is generated at `/api/docs/` and the schema at
`/api/schema/`. UUID chat session IDs are public opaque identifiers. Production
deployments should require ownership authentication for loading or deleting saved
sessions and rotate request IDs through an edge proxy.

