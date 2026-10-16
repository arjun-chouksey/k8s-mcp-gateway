# WooCommerce REST credential setup

T-008 uses WooCommerce's supported administrator UI to issue a read/write REST key. The credential is used only by the custom Woo MCP server and authenticates internal plain-HTTP requests with OAuth 1.0a.

1. Sign in to the local store at `http://shop.127.0.0.1.nip.io:8080/wp-admin/`.
2. Open **WooCommerce → Settings → Advanced → REST API**, then choose **Add key**.
3. Use description `k8s-mcp-gateway Woo MCP`, select the local administrator, choose **Read/Write**, and generate the key.
4. Run `make woo-api-secret` and paste the consumer key and secret into its hidden prompts. The script creates `mcp/woo-mcp`; it never prints or overwrites credentials.
5. Run `make woo-api-auth`. The test executes from a temporary Pod in `mcp`, proves anonymous access is denied, then verifies authenticated product GET and POST over `http://wordpress.store.svc.cluster.local`. OAuth signatures use the canonical local store URL because WooCommerce reconstructs its signature base from the configured WordPress home URL.

For rotation, generate a replacement key in WooCommerce, revoke the old key, explicitly delete `mcp/woo-mcp`, rerun `make woo-api-secret`, and restart the Woo MCP Deployment after it exists. Never commit the downloaded key file or paste either credential into logs, chat, Helm values, or shell history.
