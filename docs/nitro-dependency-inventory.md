# Nitro Dependency Inventory

**Status:** Read-only Discovery
**Date:** 2026-08-12

## Findings
1. **Source Code Inventory**: A scan of the `kirk-mcp` repository reveals no active AWS Nitro SDK integrations, API calls, or NSM (Nitro Secure Module) dependencies in the codebase itself. The repository serves primarily as the MCP API configuration and client examples for the hosted endpoint.
2. **Path D Dependencies**: AWS Nitro Enclave AMI is documented as "Path D" for enterprise customers requiring PCR0 attestation. Path A (this MCP endpoint) does not inherently require Nitro unless the backend service uses it to generate the `engine_sha` attestation.
3. **External Dependencies**: Without SSH or AWS IAM access, we cannot inspect the running `kirk-nitro` EC2 instance or enclave. However, from the client perspective, there are no Nitro-specific headers or protocols beyond standard HTTPS/JSON-RPC.

## Conclusion
Migrating the MCP endpoint to GNR will not break the `kirk-mcp` client integration, provided the new endpoint fulfills the `kirk_healthz` engine SHA attestation using Intel TDX or a static binary hash.
