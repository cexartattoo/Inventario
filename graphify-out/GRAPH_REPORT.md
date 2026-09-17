# Graph Report - InventarioInteligente  (2026-09-16)

## Corpus Check
- 6 files · ~4,551 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 70 nodes · 85 edges · 8 communities (7 shown, 1 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e6ad6387`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]

## God Nodes (most connected - your core abstractions)
1. `processCommand()` - 6 edges
2. `get_db_connection()` - 4 edges
3. `fetchAllProducts()` - 4 edges
4. `get_system_prompt()` - 3 edges
5. `generate_invoice_preview()` - 3 edges
6. `create_invoice_from_preview()` - 3 edges
7. `create_tables()` - 3 edges
8. `init_db_with_examples()` - 3 edges
9. `find_product_by_name()` - 3 edges
10. `addMessageToLog()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `generate_invoice_preview()` --calls--> `find_product_by_name()`  [INFERRED]
  billing.py → inventory.py
- `create_invoice_from_preview()` --calls--> `update_stock()`  [INFERRED]
  billing.py → inventory.py

## Communities (8 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (19): allProducts, assistantTab, billingTab, chatInput, conversationHistory, conversationLog, editButton, editProductModal (+11 more)

### Community 1 - "Community 1"
Cohesion: 0.16
Nodes (9): create_invoice_from_preview(), generate_invoice_preview(), Crea la factura final en la BD a partir de los datos de la vista previa     y d, Genera una vista previa de la factura sin guardarla en la BD.     Verifica el s, add_product(), delete_product(), find_product_by_name(), Elimina un producto de la base de datos por su ID. (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.38
Nodes (6): create_tables(), get_db_connection(), init_db_with_examples(), Crea las tablas necesarias en la base de datos si no existen., Puebla la base de datos con datos de ejemplo si está vacía., Crea y retorna una conexión a la base de datos.     La conexión está configurad

### Community 4 - "Community 4"
Cohesion: 0.38
Nodes (7): addInvoiceActionListeners(), addMessageToLog(), fetchAllProducts(), processCommand(), renderInventory(), renderInvoicePreview(), speak()

### Community 5 - "Community 5"
Cohesion: 0.67
Nodes (3): get_system_prompt(), process_user_prompt(), Genera el prompt del sistema que instruye al LLM sobre su rol y capacidades.

## Knowledge Gaps
- **19 isolated node(s):** `voiceButton`, `statusText`, `conversationLog`, `inventoryTableBody`, `searchInventoryInput` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Genera el prompt del sistema que instruye al LLM sobre su rol y capacidades.`, `Genera una vista previa de la factura sin guardarla en la BD.     Verifica el s`, `Crea la factura final en la BD a partir de los datos de la vista previa     y d` to the rest of the system?**
  _26 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._