# User Interface Specification — Program Operation from User's Perspective **[VISION DOCUMENT]**

**Date:** 24.05.2024
**Author:** Roo (Crypto Application Developer)
**Status:** MVP Complete - Strategy Builder implemented, other UI components planned
**Current Reality:** Sprint 5 completed with Strategy Builder MVP. Full UI suite planned for Sprint 6-7.
**Purpose:** To provide a comprehensive, user-centric description of the application's user interface. This document details the visual components, user workflows, and interaction models, ensuring they align with the project's core architectural principles (MVP v2) and technical implementation plan. It serves as the blueprint for the frontend development team.

---

## 1. Overview

**Core Design Principles:**

- **Real-Time & Reactive:** The UI is not a static dashboard; it's a living entity. All data—from market prices to indicator values and P&L—updates in real-time via WebSocket streams. This is critical for the volatile crypto market.
  - **Justification:** Aligns with the async, event-driven backend. The `TECHNICAL_IMPLEMENTATION_PLAN`'s focus on non-blocking I/O and the `MVP.md`'s definition of WebSocket streams make this possible.

- **Visual & Intuitive:** Complex trading logic is represented visually. The core of the application is the **Strategy Builder Canvas**, where users build strategies like flowcharts, not like code.
  - **Justification:** Directly maps to the `StrategyEvaluator`'s graph-based (DAG) model described in the `MVP.md`. This minimizes the cognitive leap between what the user sees and what the backend executes.

- **Resilient & Trustworthy:** The UI is designed to be a reliable partner. It provides clear feedback, prevents user errors, and handles backend or network issues gracefully.
  - **Justification:** Leverages the `TECHNICAL_IMPLEMENTATION_PLAN`'s pillars of stability, including state persistence with Redis (for session recovery) and robust security layers (JWT). The "Tryb Pracy Offline" from the `MVP.md` is a key feature here.

- **Modular & Scalable:** Every component, from an indicator to a full strategy, is treated as a reusable block. This promotes consistency and efficiency.
  - **Justification:** Reflects the backend's modular architecture (refactoring of `WebSocketAPIServer`) and the concept of reusable `Nodes` in the strategy graph.

---

## 2. Main UI Components

### 2.1 Dashboard (Main Hub)
- **Purpose:** To provide a "mission control" overview of all trading activities and system health at a glance.
- **Appearance:** A clean, modern grid of Material-UI cards. A persistent top bar displays critical system health indicators (e.g., WebSocket connection status, API health). A collapsible sidebar provides navigation to all major sections.
- **Features**:
  - **Active Sessions Card:** Lists all running sessions (live, paper, backtest) with real-time P&L, status (`running`, `stopped`, `error`), and a progress bar for backtests.
  - **Portfolio Overview Card:** Displays total portfolio value, daily P&L, and risk exposure, pulling data from the `WalletService` and `RiskManager`.
  - **System Health Card:** Shows the status of backend services, WebSocket connection, and key metrics like latency and message queue depth, fed by the `Prometheus` integration outlined in the `TECHNICAL_IMPLEMENTATION_PLAN`.
  - **Alerts Feed:** A chronological list of critical notifications (e.g., "Emergency Exit triggered for ALU_USDT", "Budget cap reached").
- **Interactions**:
  - Clicking a session card navigates directly to the detailed **Sessions and Execution Panel**.
  - Start/Stop buttons on the session card send idempotent commands (`session_start`/`session_stop`) to the backend, preventing duplicate sessions.
- **Why This Design:** A centralized hub reduces navigation friction and provides immediate situational awareness, which is crucial in trading. The real-time nature justifies the WebSocket-first approach over polling.

### 2.2 Strategy Builder Canvas (Core Feature)
- **Purpose:** To be the creative heart of the application, where users can design, validate, and test complex trading strategies visually and intuitively.
- **Appearance:** A professional, three-panel layout:
  - **Left Panel (Node Library):** A searchable and categorized library of all available nodes (`DataSource`, `Indicator`, `Condition`, etc.).
  - **Center Panel (Canvas):** An infinite, zoomable canvas with an optional grid where users build their strategy graph. Nodes are represented as distinctively colored blocks with input/output ports. Connections are represented as animated "glowing" lines, indicating the flow of data.
  - **Right Panel (Configuration Panel):** A context-aware panel that displays the parameters for the currently selected node. It includes input fields, sliders, and real-time validation feedback.
- **Node Types (as per `MVP.md` and `INDICATORS.md`):**
  - **DataSource:** The starting point. User selects an exchange (e.g., MEXC) and a symbol (e.g., `BTC_USDT`).
  - **Indicator:** The calculation engine. User drags this node and configures it, e.g., `TWPA` with parameters `t1=300`, `t2=0`.
  - **Condition:** The decision-maker. Compares an indicator's output to a value, e.g., `Velocity > 20.0`.
  - **Composition:** The logic hub. Combines multiple conditions using `AND`, `OR`, `SEQUENCE` operators.
  - **Action:** The trigger. Executes an action like `OPEN_SHORT` or `SEND_ALERT` when its input becomes `TRUE`.
- **User Workflow (Creating a "Flash Pump" Strategy):**
  1.  User navigates to "Strategies" and clicks "Create New Strategy". They can start from a blank canvas or a pre-built template (e.g., "Basic Pump & Dump").
  2.  They drag a `DataSource` node, select `MEXC` and `ALU_USDT`.
  3.  They drag an `Indicator` node, select `Velocity`, and connect it to the `DataSource`. In the right panel, they configure its parameters: `current_window=(0,0)`, `baseline_window=(300,60)`, `price_method="TWPA"`.
  4.  They add a `Condition` node, connect it to the `Velocity` node, and set the condition to `> 15.0`. The connection line glows green when the condition is met in real-time (if in simulation mode).
  5.  They add another chain for volume: `DataSource` -> `Volume_Surge` -> `Condition (> 5.0)`.
  6.  They drag a `Composition` node, select `AND`, and connect the two `Condition` nodes to it.
  7.  Finally, they drag an `Action` node, select `OPEN_SHORT`, and connect it to the `AND` node's output.
  8.  **Validation:** As they build, the UI provides instant feedback (e.g., red highlight on an unconnected port). Clicking "Validate" sends the graph to the backend (`POST /strategies` with `validate_only=true`), which returns a detailed report of any logical inconsistencies.
  9.  **Saving:** Once valid, the strategy is saved. The visual graph is compiled into a JSON DAG and stored.
- **Advanced Features:**
  - **Offline Editing:** If the connection is lost, the UI caches the strategy in `localStorage` and displays a "Sync" button upon reconnection, as per the `MVP.md`'s resilience goals.
  - **Templates:** The system provides pre-built graphs for common scenarios, lowering the barrier to entry.
- **Why This Design:** This visual paradigm is a direct reflection of the backend's graph-based engine, making it powerful and intuitive. Progressive validation and offline capabilities make the experience robust and user-friendly, addressing key risks identified in the project analysis.

### 2.3 Indicators Management Panel
- **Purpose:** A centralized catalog for managing all indicators, both system-defined and user-created. This is where the building blocks for strategies are forged.
- **Appearance:** A filterable, sortable table of all indicator instances. A modal form is used for creating new indicators. A key feature is the "Dependency View," which visualizes how indicators are used across different strategies.
- **Features**:
  - **Indicator Catalog:** Lists all base indicators available in the system (from `INDICATORS_TO_IMPLEMENT.md`), complete with descriptions and required parameters.
  - **Custom Indicator Creation:** A form allows users to create new, composite indicators. For example, a user can create `My_Pump_Score` by combining `Velocity` and `Volume_Surge` with custom weights.
  - **Real-Time Monitoring:** The list view shows the current value of each indicator for subscribed symbols, updated via WebSocket.
- **Workflow (Creating a Custom Indicator):**
  1.  User navigates to the "Indicators" tab and clicks "Create New".
  2.  They select a type: "Basic" (an instance of a system indicator) or "Composite" (a formula).
  3.  For a "Basic" indicator, they select `TWPA` from a dropdown, set `t1=300`, `t2=0`, and name it `My_TWPA_5min`.
  4.  This new indicator `My_TWPA_5min` now appears in the Node Library within the Strategy Builder, ready to be used.
- **Why This Design:** Centralized management prevents duplication and promotes reuse. The dependency view is crucial for performance optimization, as it helps users understand the impact of their choices, aligning with the `TECHNICAL_IMPLEMENTATION_PLAN`'s emphasis on a shared cache.

### 2.4 Sessions and Execution Panel
- **Purpose:** To launch, monitor, and manage all trading sessions (backtesting, paper trading, and live trading).
- **Appearance:** A wizard-style interface for session creation to guide the user. Once a session is running, it presents a tabbed view with real-time data streams.
- **Features**:
  - **Session Creation Wizard:** A step-by-step process: 1. Select Mode (Backtest/Live), 2. Select Strategy, 3. Select Symbols, 4. Configure Parameters (e.g., virtual balance for backtests, risk limits).
  - **Execution Controls:** Prominent "Start", "Pause", and "Stop" buttons that trigger idempotent backend commands.
  - **Real-Time Data Streams:** A tabbed interface showing live feeds for:
    - **Market Data:** Raw trades and order book updates.
    - **Indicators:** Values of all indicators used in the strategy.
    - **Signals:** A log of when conditions are met and actions are triggered.
    - **Trades:** A list of all executed trades with P&L.
- **Why This Design:** The wizard simplifies the complex process of launching a session, reducing user error. The tabbed real-time view provides complete transparency into the strategy's execution, building user trust.

### 2.5 Results and Analytics Panel
- **Purpose:** To provide deep, actionable insights into the performance of trading strategies.
- **Appearance:** A hierarchical, drill-down interface. It starts with a list of all completed sessions and allows the user to dive deeper into strategies, symbols, and individual trades. Performance is visualized with interactive charts.
- **Features**:
  - **Hierarchical View:** Session -> Strategy -> Symbol -> Trades.
  - **Key Metrics:** P&L, Sharpe Ratio, Max Drawdown, Win/Loss Rate, etc.
  - **Interactive Charts:** Users can overlay indicator values, signals, and trade entry/exit points on the price chart to understand *why* a strategy behaved the way it did.
  - **Export Functionality:** All data can be exported to CSV or JSON for external analysis.
- **Why This Design:** A hierarchical drill-down is the most logical way to analyze complex results. Interactive charts are essential for visual correlation and debugging strategies.

### 2.6 Settings and Configuration
- **Purpose:** A secure area for managing user-specific settings, API keys, and global risk parameters.
- **Appearance:** A simple, tabbed form interface.
- **Features**:
  - **API Key Management:** Input fields for exchange API keys. These fields are write-only, and the values are sent directly to a secure backend vault (as per the `TECHNICAL_IMPLEMENTATION_PLAN`'s security layer).
  - **Notification Settings:** Configure alerts for Telegram, Discord, or email.
  - **Global Risk Limits:** Set overall portfolio budget caps and default risk parameters.
- **Why This Design:** Centralizes all sensitive and global configurations in one secure, easy-to-manage location.

### 2.7 Multi-Tenant Support
- **Purpose:** To ensure isolated user experiences in a shared environment, preventing data leakage and conflicts.
- **Appearance:** Integrated into all panels via a "Scope" selector in the top bar; settings tab for scope management.
- **Features**:
  - **Scope Selection:** Users select or create a scope (e.g., personal workspace) that prefixes all operations (strategies, indicators, sessions).
  - **Isolation:** Data is scoped via Redis namespaces (from `TECHNICAL_IMPLEMENTATION_PLAN`); UI filters content by active scope.
  - **Collaboration:** Optional sharing within scope, with permission controls.
- **Workflow:** On login, user selects scope; all subsequent actions (e.g., creating indicators) are scoped automatically.
- **Why This Design:** Directly supports `MVP.md`'s multi-tenant architecture and `UI_GUIDE.md`'s scope-based operations, ensuring security and scalability.

---

## 3. User Workflows Summary

This section summarizes the end-to-end user journey for the most common tasks.

- **Onboarding & First Strategy:** A new user logs in, is greeted by a welcome tour, and is guided to the Strategy Builder. They select a template, make minor adjustments, validate it, and run their first backtest—all within minutes.
- **Strategy Optimization Cycle:** An experienced user reviews the results of a backtest in the Analytics Panel. They notice a false signal and dive into the chart, overlaying indicators. They identify a flawed condition, navigate back to the Strategy Builder, tweak the graph, and launch a new backtest to compare performance.
- **Going Live:** After several successful backtests, the user navigates to the Settings panel to securely enter their exchange API keys. They then launch a new session in "Live Trading" mode, using the same strategy graph they perfected in backtesting. They monitor its performance from the main Dashboard.

---

## 4. Technical Integration (UI ↔ Backend)

The UI is a "smart client" that communicates with the backend via two primary channels, as defined in `WS_REST_OPIS.md`.

- **WebSocket:** The lifeline for all real-time data. The UI subscribes to streams for market data, indicator values, signals, and session statuses. All messages are wrapped in the standard envelope (`version`, `timestamp`, etc.).
- **REST API:** Used for transactional, state-changing operations like creating/updating strategies, managing indicators, and starting/stopping sessions. This provides a clear, stateless interface for core commands.
- **Error Handling:** When the backend returns a structured error (e.g., `{"type": "error", "error_code": "session_conflict"}`), the UI translates this into a user-friendly notification (e.g., "Session conflict: A session with these symbols is already running.").

---

## 5. Critical Enhancements from MVP/Technical Plan

This UI specification is not just a concept; it is the direct, user-facing manifestation of the core architectural decisions made in our planning documents.

- **From Mocks to Reality:** The UI is built with the assumption that all indicators provide real, calculated values, fulfilling the primary goal of the `TECHNICAL_IMPLEMENTATION_PLAN`.
- **Graph-Powered Flexibility:** The Strategy Builder Canvas is the direct counterpart to the `StrategyEvaluator` service. Its flexibility is a direct result of moving away from a rigid JSON structure.
- **Security by Design:** The UI's handling of API keys and user sessions is designed around the JWT and Vault integration specified in the `MVP.md`.
- **A Resilient Experience:** Features like offline editing and clear error messages are the tangible results of the backend's focus on reliability, state persistence, and structured error handling.

---

## 6. Technical Implementation Details

To enable precise code changes and interface behavior, the following details specify how UI components interact with backend, state management, and error handling.

### 6.1 API Integration Specifications
- **WebSocket Messages:**
  - Envelope: `{version: "1.0", timestamp: "2025-09-24T21:00:00Z", id: "uuid", session_id: "optional", type: "data", payload: {...}}`
  - Key streams: `market_data` (deals/orderbook), `indicators` (values per symbol), `signals` (condition triggers), `session_status` (running/paused/error).
  - Commands: `session_start` payload: `{strategy_id: "uuid", symbols: ["BTC_USDT"], mode: "backtest|live", params: {balance: 1000}}`
- **REST Endpoints:**
  - POST /strategies: Body `{validate_only: true, graph: {...}}` Response: `{valid: true, errors: []}`
  - GET /indicators?scope=user1&symbol=BTC_USDT: Response array of indicator objects.
  - POST /sessions/start: Idempotent via sha256 hash of config.

### 6.2 State Management
- **Client State:** Use React Context/Redux for scope, active session, cached strategies. Persist to localStorage for offline.
- **Real-time Sync:** WebSocket subscriptions auto-reconnect with exponential backoff (initial 1s, max 30s).
- **Validation State:** Local syntax check (immediate), server logical check (async), visual feedback via CSS classes (valid/invalid).

### 6.3 Error Handling and Recovery
- **Error Taxonomy:** Map backend codes to UI: `validation_error` -> red highlight + tooltip, `session_conflict` -> modal dialog.
- **Recovery Flows:** Network errors -> retry button, auth errors -> redirect to login, data errors -> fallback to cached values.
- **Performance:** UI updates <100ms latency, handle 1000+ indicators via virtualization (react-window).

### 6.4 Security Implementation
- **Authentication:** HttpOnly cookies for access and refresh tokens, automatic refresh on 401.
- **API Keys:** Encrypt in transit, store in Vault, UI shows masked fields.
- **Scope Isolation:** All requests include scope header, UI filters data by active scope.

This ensures UI is implementable with clear code paths and testable behaviors.

---

## 7. Implementation Roadmap & Iterative Development

### **Current Status: Sprint 5 MVP Complete**
- **Backend Status:** Sprint 5 completed - Strategy Builder MVP operational
- **UI Status:** ✅ Strategy Builder implemented with blueprint storage and validation
- **Limitations:** No deployment pipeline, approval workflows, or operational monitoring

### **Phase 1: Strategy Builder MVP (Sprint 5 - COMPLETED)**
**Goal:** Visual strategy creation and blueprint storage
- **Components:** Drag-and-drop canvas, node library, real-time validation, blueprint API
- **Scope:** Strategy design, validation, and storage (no execution or deployment)
- **Success Criteria:** ✅ Users can create, validate, and save strategy blueprints

### **Phase 2: Deployment Pipeline (Sprint 6)**
**Goal:** Connect blueprints to live execution
- **Components:** Approval workflows, staging deployment, session management integration
- **Scope:** Paper trading, live deployment, operational monitoring
- **Success Criteria:** Strategies can be deployed from blueprints to live trading

### **Phase 3: Operations Dashboard (Sprint 6)**
**Goal:** Complete operational visibility and control
- **Components:** Real-time P&L, position monitoring, incident management, kill switches
- **Scope:** Full operations workflow with dashboard and controls
- **Success Criteria:** Operators can manage all trading activities through UI

### **Phase 4: Enterprise Features (Sprint 7-8)**
**Goal:** Production-ready enterprise platform
- **Components:** Multi-tenant isolation, JWT auth, audit trails, advanced analytics
- **Scope:** Security hardening, compliance features, enterprise workflows
- **Success Criteria:** Commercial production deployment ready

### **Critical Dependencies:**
1. **Sprint 2 API Infrastructure** - REST + WebSocket foundation
2. **Sprint 3 Indicator Validation** - Proven business value before UI investment
3. **Business Validation Gates** - No UI expansion without statistical proof

**This vision document represents the complete product. Implementation follows ROADMAP.md phases with business validation gates.**