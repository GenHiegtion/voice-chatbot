# Implementation Plan: Data Team for Food Ordering Chatbot (Text-based)

## 1) Finalized Scope and Objectives
- Focus exclusively on completing the text chat feature for the food ordering chatbot.
- Do not implement any ASR/voice-related content in this plan.
- Do not request or process any business logic related to user information.
- No image-based Q&A scripts will be developed (images are for illustrative purposes only).
- The chatbot will respond based on real data from the database, prioritizing accuracy and stability.

## 2) Mandatory Constraints
- Do not create any additional tables or entities in the database.
- Use only existing tables from database/db.txt to design queries.
- Strictly prohibited: Any operations to add, edit, or delete data in the DB.
- Only read-only queries using SELECT are permitted.
- When processing promotions by item, full verification is required:
  - products.is_selling = true
  - sale_offs.is_active = true
  - Current time falls within [start_date, end_date]
- Do not import directly from database/db.txt; the schema must be defined in the code for stable usage.

## 3) Alignment with Current Data
### 3.1 Tables for Direct Use by the Data Team
- catalog
- products
- sale_offs

### 3.2 Tables for Potential Future Extension
- orders
- order_items

Note:
- In the current scope, separate coupon management is not implemented.
- If a business requirement for "one coupon per order" arises later, it will be handled at the application layer according to business conventions without creating new tables.

## 4) Proposed Code Organization (Maintainability & Scalability)
Organizational Principles:
- Clearly separate layers: Repository (DB queries), Service (business logic), Tool (Agent interface), and Skill (standardization and output constraints).
- File names should be short, clear, and reflect their responsibility.
- The Data Team only calls the read-only layer.

### 4.1 New Files to be Created
- src/db_schema.py: Defines models/schemas based on existing tables in db.txt.
- src/repositories/menu_repo.py: Queries categories, items, item details, and filters by price/category.
- src/repositories/promo_repo.py: Queries item-specific promotions and active deals.
- src/services/menu_service.py: Processes item search logic and formats data returned to the tool.
- src/services/promo_service.py: Processes item promotion logic, filtering by time and status conditions.
- src/tools/menu_tools.py: Tool for the Menu Agent, utilizing menu_service.
- src/tools/promo_tools.py: Tool for the Promotion Agent, utilizing promo_service.
- src/skills/query_skill.py: Normalizes Vietnamese queries and extracts search constraints.
- src/skills/guard_skill.py: Blocks or redirects out-of-scope questions.
- src/skills/response_skill.py: Standardizes concise and consistent response formats.
- Unit and integration tests for all components above.

### 4.2 Existing Files Requiring Updates
- src/agents/menu_agent.py: Switch to using menu_tools.
- src/agents/promotion_agent.py: Switch to using promo_tools.
- src/teams/data_team.py: Update routing rules for menu, promotion, or mixed queries.
- src/agents/state.py: Add lightweight context for follow-up questions (e.g., last_topic).
- src/config.py: Add timezone and runtime parameters for Data Team.

## 5) Query and View Design (Optional)
### 5.1 Priority
- Initial phase prioritizes direct queries via the repository for easier logic control.

### 5.2 Optimization via Views
If needed, views can be created from existing tables:
- vw_sell_products: Products currently for sale.
- vw_active_sale_offs: Active promotions based on current time.
- vw_product_active_deals: Products for sale with active promotions.

## 6) Tool Design for Data Team
### 6.1 Menu Tools
- get_menu_categories(): Returns list of categories from catalog.
- search_menu(query, category, min_price, max_price): Searches for items by name/description with filters.
- get_dish_details(dish_name_or_id): Returns item details, original price, and discounted price.

### 6.2 Promotion Tools
- get_active_promotions(): Lists promotions active at the time of query.
- check_promotion_for_dish(dish_name_or_id): Returns specific promotions for an item.
- get_best_deals(limit=5): Returns top promotions based on highest discount.

## 7) Skill Design for Agent
- QuerySkill: Normalizes Vietnamese text and standardizes price units.
- GuardSkill: Redirects users if they ask about out-of-scope content or non-existent data.
- ResponseSkill: Standardizes format (Item, Price, Status, Promotion).

## 8) Implementation Roadmap
- Phase 0: Foundation & Data Safety (db_schema, Read-only mode).
- Phase 1: Repository and Service (Logic & Unit tests).
- Phase 2: Tool and Agent Integration (Tools, Agents, Skills).
- Phase 3: Integration Testing & Optimization (Mixed queries, Fallback).

## 9) Chatbot Test Scenarios (Text-only)
- Routing and Guardrails: Verify correct agent routing and out-of-scope blocking.
- Menu: List categories, search by name (accented/unaccented), and price filtering.
- Promotion: List active promos only, valid date checks, and item-specific promos.
- Reliability and Security: Long queries, SQL injection prevention, and timeout handling.

## 10) Definition of Done
- Data Team answers menu/promotion questions correctly based on the real DB.
- No DB write operations in the chat flow.
- Promotion logic always checks is_active, start_date/end_date, and is_selling.
- Unit and integration tests pass for the text chat scope.

## 11) Risks and Mitigations
- Risk: Unclean promotion data. Mitigation: Service-layer validation.
- Risk: Mixed query routing errors. Mitigation: Add routing examples to prompts.
- Risk: Discrepancies between mock and DB. Mitigation: Environment-based rollouts.