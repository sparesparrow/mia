Run the API contract drift check.

1. If LIBERTIN_API_URL is set: fetch the live OpenAPI spec and diff it against
   contracts/openapi.snapshot.yaml. Report added/removed/changed paths and schemas.
2. If no URL: verify that packages/api/src/client.ts types are consistent with
   contracts/openapi.snapshot.yaml (static check only).
3. Exit 1 if any breaking changes detected (removed paths, changed required fields,
   changed response types).

Print a summary table: path | status (ok/added/removed/changed).
