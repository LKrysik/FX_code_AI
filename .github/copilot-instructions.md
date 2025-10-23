# AI Development Guidelines for Crypto Monitor Project

## 🎯 CORE PHILOSOPHY (Simplified for MVP)

### We are trading in futures - deals and order book only (no tickers)


# MANDATORY: 
- npm and node.exe are located in "C:\Users\lukasz.krysik\Desktop\FXcrypto\node-v22.19.0-win-x64\" folder
- python is located in ".venv\\Scripts\\python.exe"
- Always run backend server with: 'Start-Process powershell -ArgumentList "-Command", "python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload"'


# Project Development Guidelines

## 🎯 Production-First Development
- **Production-ready code focus** - write code intended for production use
- **Clean Architecture when building new** - proper structure from the start
- **Pragmatic solutions** - balance perfection with delivery timelines

---

## 🏗️ ARCHITECTURE PRINCIPLES

### Modular Architecture
- Use interfaces for key components (e.g., market data, trading)
- Avoid complex plugins for now; use direct implementations
- Prepare structure for future extensibility

### Basic Monitoring Architecture
- Use simple, modular components for core monitoring
- Focus on reliable data collection and basic signals first
- Advanced features as future phases

---

## 🛡️ CRITICAL ANTI-PATTERNS

### Memory Leak Prevention
- **NEVER use defaultdict for long-lived structures**
- **Explicit cache creation with business logic control**
- **WeakReferences for event handlers**
- **Mandatory cleanup with monitoring**
- **Add max sizes/TTLs to all dicts and queues**

### Architecture Violations
- **NO global Container access** - dependency injection only
- **NO business logic in Container** - pure assembly only
- **EventBus with monitoring for critical path** - direct calls preferred but allowed if latency <100ms
- **NO hardcoded values** - all parameters from configuration
- **NO code duplication** - same functionality must exist in exactly one place
- **NO backward compatibility workarounds** - create final, correct solutions immediately

---

## 🧪 DEVELOPMENT STANDARDS

### Code Quality
- **Interface-based design** - depend on abstractions
- **Container dependency injection** - no service locator
- **EventBus for non-critical paths** - direct calls for critical path where possible
- **STRICT NO TESTING CODE** - user handles all testing manually; NEVER create test suites

### No Testing Rule
User handles all testing manually through:
- Running backend server in one terminal window
- Running frontend tests in another terminal window
- Integration tests with both services running

---

## 🤖 AI AGENT WORKFLOW (Pre-Change Protocol)

### 1️⃣ Detailed Architecture Analysis
- Read relevant source files to understand current architecture
- Document the system design and principles
- Identify all architectural layers and their responsibilities

### 2️⃣ Impact Assessment
- Analyze how the proposed change will affect the entire program
- Evaluate consequences for other modules and components
- Use `list_code_definition_names()` to trace dependencies
- Map all related objects and their interactions

### 3️⃣ Assumption Verification
- Verify all assumptions—**never assume without validation**
- Challenge every premise against actual code
- Document what you verify and how you validated it
- No assumptions without explicit verification

### 4️⃣ Proposal Development
- Justify the proposed change in the context of the entire system
- **Eliminate code duplication** - consolidate identical functionality
- **Do NOT use backward compatibility workarounds** - create the final, correct solution immediately
- Ensure the solution maintains architectural consistency

### 5️⃣ Issue Discovery & Reporting
- If you discover architectural inconsistencies, design flaws, or structural problems:
  - Justify them in the context of the entire system
  - **Report them to user with full explanation BEFORE implementing**
  - Do not proceed until user acknowledges or approves

### 6️⃣ Implementation & Consistency
- Use `apply_diff` for targeted, well-reasoned changes
- Use `write_to_file` for new files
- Implement changes in a way that ensures architectural coherence
- Verify consistency across affected components

### 7️⃣ Atomic Testing
- Test each change individually
- Do not introduce multiple changes simultaneously
- Verify that each modification works in isolation

---

## 📋 DOCUMENTATION REFERENCES

### Development Standards
- **[Memory Safety](docs/development/MEMORY_LEAK_PREVENTION.md)** - Prevention patterns
- **[Coding Standards](docs/development/CODING_STANDARDS.md)** - Quality guidelines

---

## 🛠️ SETUP & EXECUTION

### Backend Server (Mandatory for Integration Tests)
```powershell
Start-Process powershell -ArgumentList "-Command", "python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload"
```

### AI Agent Commands
**Use `.roo/commands` as MANDATORY** for all agent commands

---

## 📌 SUMMARY

**MVP Focus:** Basic monitoring with simple, modular components. Advanced features as future phases.

**Agent Protocol:** Analyze → Verify → Propose → Report Issues → Implement with Consistency

**No Compromises:** No testing code, no backward compatibility, no code duplication, no assumptions.