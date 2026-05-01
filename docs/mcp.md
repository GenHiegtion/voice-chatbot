# MCP Integration Plan (Model Context Protocol)

## 1) Goals
- Standardize how tools and context are exposed to LLMs via MCP.
- Reuse existing logic (tools, services, repositories) without rewriting.
- Keep FastAPI + LangGraph behavior unchanged and add MCP as a parallel channel.

## 2) Current System Snapshot
- FastAPI entrypoint in main.py, primary APIs: /api/chat, /api/chat/stream, /api/speech-to-text, /api/voice-chat.
- Chat flow uses LangGraph: coordinator -> data_team/action_team -> menu_agent/promotion_agent/order_agent.
- Existing tools:
  - Menu: menu_tools (get_menu_categories, search_menu, get_dish_details, get_dishes_by_category, get_best_selling_products)
  - Promotion: promo_tools (get_active_promotions, check_promotion_for_dish, get_best_deals)
  - Order: order_tools (add_to_cart, remove_from_cart, view_cart, update_cart_quantity, place_order)
- Session history: local uses RAM, Docker build uses Redis (session_history.py + redis_client.py).
- Cart is in-memory per session (order_tools._carts) and synced from request current_cart.
- Data access is read-only via repositories/services and schema in src/db_schema.py.
- Docker/Compose is available (docker/, scripts/redeploy.sh) with Redis + MySQL for dev/prod.

## 3) MCP Integration Direction
### 3.1 MCP Role
- MCP Server exposes existing tools to MCP clients (LLM IDEs, external agents, orchestrators).
- MCP Client is not implemented in this plan.

### 3.2 Initial Scope
- Implement MCP Server for the existing menu/promotion/order tools only.
- Do not change current FastAPI endpoints or LangGraph flow.

## 4) High-Level Design
### 4.1 Proposed Architecture
- Add a dedicated MCP module under src/mcp/:
  - server.py: initialize MCP server, register tools
  - tools/: adapters for existing tools
  - context.py: normalize context (session_id, current_cart, history)
- Run MCP as a standalone CLI server (no FastAPI mounting).
- Reuse session_history for MCP context (Redis when enabled).

### 4.2 Tool Mapping to MCP
- Menu tools -> MCP tool group "menu":
  - get_menu_categories
  - search_menu
  - get_dish_details
  - get_dishes_by_category
  - get_best_selling_products
- Promotion tools -> MCP tool group "promotion":
  - get_active_promotions
  - check_promotion_for_dish
  - get_best_deals
- Order tools -> MCP tool group "order":
  - add_to_cart
  - remove_from_cart
  - view_cart
  - update_cart_quantity
  - place_order

### 4.3 MCP Context Rules
- Every tool call requires session_id.
- current_cart can be supplied by the client and is synced into in-memory cart.
- History is loaded via session_history (Redis if enabled, otherwise RAM).
- Session TTL follows redis_ttl_seconds.

## 5) Configuration Changes
- Add to config.py/.env:
  - MCP_ENABLED: true/false
  - MCP_TRANSPORT: http
  - MCP_HOST / MCP_PORT (required)
  - MCP_AUTH_TOKEN (required)
  - MCP_LOG_LEVEL
- Reuse existing Redis config for MCP history:
  - REDIS_ENABLED, REDIS_URL, REDIS_TTL_SECONDS

## 6) Implementation Phases
### Phase 0: Preparation
- Use the official MCP Python SDK.
- Use HTTP transport only (no stdio in this plan).
- Define tool naming conventions and output schema rules.

### Phase 1: MCP Server Skeleton
- Create src/mcp/server.py and entrypoint script (scripts/run_mcp_server.py).
- Initialize server and register tools.
- Align logging with current app logging.

### Phase 2: Tool Adapters
- Create MCP wrappers that call menu_tools, promo_tools, order_tools.
- Normalize input/output per MCP spec.
- Sync session_id and current_cart before cart operations.

### Phase 3: Context and Behavioral Parity
- Connect session_history for tools that need history.
- Apply timeout and retry similar to current API flow.
- Add guardrails for out-of-scope data tool queries.

### Phase 4: Security and Operations
- HTTP transport with bearer token auth.
- Run MCP in the same Docker network, not public in this phase.
- Add MCP healthcheck.
- Add a dedicated MCP service in Docker Compose (shared Redis/MySQL/cache volumes).

### Phase 5: Testing and Rollout
- Unit tests for MCP tool adapters.
- Integration test for MCP auth and handshake.
- Internal rollout before exposing to external clients.

## 7) Risks and Mitigations
- Tool output instability -> enforce schema and regression tests.
- Session/cart conflicts -> sync session_id and current_cart on each call.
- Load increase -> set concurrency limits and timeouts.

## 8) Definition of Done
- MCP server runs standalone and lists/calls tools.
- Menu/promotion/order tools return the same results as current FastAPI flow.
- Chatbot flow remains unchanged.
- Minimum MCP tests pass (auth + tool adapters).
