---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - "_bmad-output/prd.md"
  - "_bmad-output/analysis/brainstorming-session-2025-12-18.md"
  - "docs/UI_INTERFACE_SPECIFICATION.md"
  - "docs/UI_BACKLOG.md"
  - "docs/PRODUCT.md"
  - "docs/TRADER_ASSESSMENT.md"
  - "docs/STRATEGY_FLOW.md"
documentCounts:
  prd: 1
  briefs: 0
  brainstorming: 1
  research: 0
  ui_docs: 5
elicitationMethods:
  - "User Persona Focus Group"
  - "Cross-Functional War Room"
  - "First Principles Analysis"
  - "SCAMPER Method"
  - "Pre-mortem Analysis"
workflowType: 'ux-design'
lastStep: 4
project_name: 'FX Agent AI'
user_name: 'Mr Lu'
date: '2025-12-20'
---

# UX Design Specification - FX Agent AI

**Author:** Mr Lu
**Date:** 2025-12-20

---

## Executive Summary

### Project Vision

FX Agent AI is a **Pump & Dump Detection Platform** - a trading automation tool that helps cryptocurrency traders detect market pumps, enter short positions at the peak, and exit with profit. The system uses a sophisticated **5-section state machine** (S1→O1→Z1→ZE1→E1) controlling the complete trading lifecycle.

**Core Philosophy:** "Build a TOOL, not a strategy" - traders configure and optimize their own parameters.

**Current State:** Brownfield project with most features built, but UI suffers from poor information architecture - too much complexity, unclear hierarchy, and suboptimal information density.

**Core UX Problem:** UI exists but is difficult, unreadable, unclear. Not missing features - missing clarity.

### Target Users

**Primary Persona: Intermediate Trader (Trader B)**
- Understands trading concepts, not a programmer
- Wants: Transparency, confidence, speed
- Key need: "Show me what matters NOW, hide what doesn't"
- Success: Glance → Understand → Act in under 5 seconds

**Secondary Persona: Beginner Trader (Trader A)**
- Learning pump/dump patterns
- Wants: Guidance, templates, explanations
- Key need: "Hold my hand until I get it"
- Success: Complete first profitable backtest with guidance

**Tertiary Persona: Advanced Trader (Trader C)**
- Power user, wants maximum control
- Wants: Data access, customization, API
- Key need: "Give me tools, get out of my way"
- Success: Custom setup that matches personal workflow

### User Needs Priority Matrix

| Need | Beginner | Intermediate | Advanced | Priority |
|------|----------|--------------|----------|----------|
| State-aware UI | Nice | **CRITICAL** | Nice | P1 |
| Glanceable status | Nice | **CRITICAL** | Expected | P1 |
| Human labels | **CRITICAL** | Important | Optional | P1 |
| Onboarding wizard | **CRITICAL** | Nice | Skip | P2 |
| Keyboard shortcuts | Don't care | Important | **CRITICAL** | P2 |
| Expert mode | Don't care | Nice | **CRITICAL** | P3 |

### Key Design Challenges

1. **Information Overload vs. Clarity** - Need optimal density, not maximum features
2. **5-Section System Complexity** - Powerful but confusing terminology
3. **State Machine Visibility** - Users must see WHAT and WHY
4. **No Onboarding Path** - Users don't know where to start
5. **Power User Retention** - Can't sacrifice depth for simplicity

### Design Opportunities

1. **"One Question Dashboard"** - Every element answers "What should I do now?"
2. **State-Driven Information Density** - Context determines content
3. **Journey Bar Navigation** - Visual progress through trading flow
4. **Hide-First Design** - Clean default, power on demand
5. **Human Vocabulary** - Replace S1/Z1/E1 with action words

---

## Design Philosophy

### Core Question

**"What should I do right now?"**

Every UI element must help answer this question. If it doesn't → remove it.

### Five States of User Attention

1. **WAIT** - Nothing happening, low attention (👀 Watching)
2. **ALERT** - Something detected, attention rising (🔥 Found!)
3. **DECIDE** - Action may be needed, full attention (🎯 Entering)
4. **MONITOR** - Position active, watching outcome (📈 Monitoring)
5. **REVIEW** - Session ended, learning mode (✅ Done)

### Vocabulary Transformation

| Technical | Human | Icon |
|-----------|-------|------|
| MONITORING | Watching | 👀 |
| S1 (Signal Detection) | Found! | 🔥 |
| O1 (Signal Cancellation) | False Alarm | ❌ |
| Z1 (Entry Conditions) | Entering | 🎯 |
| POSITION_ACTIVE | Monitoring | 📈 |
| ZE1 (Close Order) | Taking Profit | 💰 |
| E1 (Emergency Exit) | Stopping Loss | 🛑 |

---

## Design Principles

### 1. State-Driven Information Density

Each state machine state defines its own UI mode:

- **MONITORING Mode:** Calm, minimal (3-4 key metrics)
- **SIGNAL_DETECTED Mode:** Alert, focused (countdown, conditions)
- **POSITION_ACTIVE Mode:** Intense, P&L-centric

### 2. Progressive Disclosure with Consistent Anchors

- **Level 1 (Always visible):** State badge, primary metric
- **Level 2 (Context-dependent):** Relevant details for current state
- **Level 3 (On-demand):** Expandable panels for deep dive
- **Anchor points:** Same position regardless of mode

### 3. Glanceability First, Details Second

- **2-second rule:** Understand situation in 2 seconds
- **Visual hierarchy:** Size + Color + Position = Importance
- **White space as feature, not waste**

### 4. Expert Mode as First-Class Citizen

- Not an afterthought toggle
- Keyboard shortcuts from day one
- Technical labels available as preference option
- Customizable layouts for power users

### 5. Error Visibility > Aesthetics

- Never sacrifice error visibility for clean look
- Connection status always prominent when unhealthy
- Sound alerts for critical issues
- Error states impossible to miss

---

## Innovation Opportunities

### High-Impact Quick Wins

| Innovation | Description | Effort | Impact |
|------------|-------------|--------|--------|
| **Status Hero Component** | State + P&L combined in one prominent element | Medium | High |
| **Journey Bar Navigation** | Watching → Found → Enter → Monitor → Exit | Medium | High |
| **Condition Progress Bars** | Visual progress, not checkboxes | Low | Medium |
| **Human Vocabulary** | Replace S1/Z1/E1 throughout | Low | High |

### Medium-Term Innovations

| Innovation | Description | Effort | Impact |
|------------|-------------|--------|--------|
| **Now Trading Bar** | Spotify-style persistent footer when position active | Medium | High |
| **Gaming Adaptations** | P&L as health bar, celebration animations | Medium | Medium |
| **Sound Alerts** | Audio signals for state changes | Low | Medium |

### Paradigm Shifts

| Innovation | Description | Effort | Impact |
|------------|-------------|--------|--------|
| **Reverse Learning Flow** | Try first, configure later | High | High |
| **Hide-First Design** | Clean default, reveal power on demand | Medium | High |

---

## UX Risk Prevention

### Critical Design Rules

1. **Error states MUST be impossible to miss** - Full-screen if critical
2. **Every transition shows reason inline** - Not click-to-reveal
3. **Color-code exits:** 💚 Profit / 🔴 Stop Loss / 🟡 Manual
4. **Performance tested under load** - Simulate pump conditions
5. **Onboarding is the experience** - Can't be skipped

### Pre-launch Checklist

- [ ] Beta test with 3+ advanced traders
- [ ] Load test during simulated pump (1000+ ticks/sec)
- [ ] Disconnect test: user notices within 3 seconds
- [ ] New user test: completes first backtest without help
- [ ] Mobile test: can close position on phone
- [ ] Transition test: user explains why each transition happened

### Risk Prevention Matrix

| Risk | Prevention | Priority |
|------|------------|----------|
| Power users feel abandoned | Expert mode first-class, beta test with advanced traders | P1 |
| Errors hidden by clean design | Error states impossible to miss, sound alerts | P1 |
| Transition reasons unclear | Inline explanation, color-coded exits | P1 |
| Performance during high activity | Load test during simulated pumps, throttling | P1 |
| Onboarding skipped | Make it the experience, not optional | P2 |
| No mobile fallback | Emergency panel responsive | P2 |

---

## Core User Experience

### Defining Experience

**The Core Loop:**

```
👀 Watch → 🔥 Detect → 🎯 Enter → 📈 Monitor → 💰/🛑 Exit → 👀 Watch again
```

**Primary User Action:** Monitor state machine and react to trading opportunities.

**Critical Interaction:** The 60-second window from "Signal Detected" to "Entry Decision" - this is where user trust is built or broken. The system must:
- Show clear signal strength and confidence
- Display countdown to decision deadline
- Visualize which conditions are met/pending
- Explain WHY this signal was detected

**Core Question Every Screen Must Answer:** "What should I do right now?"

### Platform Strategy

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Primary Platform** | Desktop Web (1920x1080+) | Complex trading interface, multi-panel layout |
| **Browsers** | Chrome, Firefox, Edge (latest) | Modern JS, WebSocket, no legacy support |
| **Primary Input** | Mouse + Keyboard | Quick actions, power user shortcuts |
| **Mobile Support** | Emergency-only responsive | Close position, view P&L - not full trading |
| **Offline Support** | Not required | Real-time trading requires live connection |
| **Multi-monitor** | Future consideration | Pop-out panels for advanced users |

**Platform Priorities:**
1. Desktop Chrome - primary development target
2. Desktop Firefox/Edge - tested, supported
3. Mobile emergency panel - responsive fallback
4. Tablet - not explicitly supported

### Effortless Interactions

**Zero-Friction Actions (must feel instant and natural):**

| Action | Implementation | Success Metric |
|--------|----------------|----------------|
| **Understand current state** | Status Hero component - state + P&L in one glance | < 2 seconds to comprehend |
| **See position P&L** | Largest element on screen when position active | Impossible to miss |
| **Know why transition happened** | Inline reason badge with every state change | No log-digging required |
| **Emergency close position** | Esc key or prominent red button | < 1 second to execute |
| **Start new session** | One-click with smart defaults | Single action to begin |
| **Navigate trading flow** | Journey Bar always visible | Always know where you are |

**Friction to Eliminate:**
- Reading technical jargon (S1/Z1/E1) - replaced with human words
- Hunting for P&L information - made prominent
- Understanding state machine state - visualized clearly
- Finding relevant indicators - context-aware display
- Confirming destructive actions - smart confirmation only when needed

### Critical Success Moments

**Moment 1: First Signal Detection**
- User sees 🔥 "Found!" badge for the first time
- Success feeling: "Wow, it actually works!"
- Design requirement: Make this moment celebratory, clear, exciting

**Moment 2: First Profitable Exit**
- Position closes with 💰 green P&L
- Success feeling: "I made money with this system!"
- Design requirement: Celebration animation, clear summary

**Moment 3: Understanding "Why"**
- User reads inline transition explanation
- Success feeling: "I understand what the system is doing"
- Design requirement: Every transition has visible, human-readable reason

**Moment 4: Trusting Automation**
- User lets system run without constant manual checking
- Success feeling: "I can rely on this"
- Design requirement: Consistent, predictable, transparent behavior

**Moment 5: Error Recovery**
- Connection drops and system handles gracefully
- Success feeling: "It recovered without losing my position"
- Design requirement: Visible status, auto-reconnect, clear recovery

### Experience Principles

1. **Answer "What Now?" Instantly**
   - Every screen state answers the user's primary question
   - No hunting for information, no interpretation needed

2. **State Drives Everything**
   - Current state machine state determines UI mode
   - Context-appropriate information density
   - Relevant actions for current situation

3. **Celebrate Success, Explain Failure**
   - Profitable exits get visual celebration
   - Losses get clear explanation of what happened
   - Every transition has visible reasoning

4. **Speed Over Polish**
   - Performance under load is non-negotiable
   - Quick actions (keyboard) before pretty animations
   - Response time < 100ms for user actions

5. **Trust Through Transparency**
   - Never hide what system is doing
   - Always show connection status
   - Log everything, make logs accessible

---

## Desired Emotional Response

### Emotional Context

Trading inherently triggers strong emotions that UX must actively manage:

| Trigger | Natural Emotion | UX Challenge |
|---------|-----------------|--------------|
| Money at stake | Anxiety, fear | Create calm confidence |
| Time pressure | Stress, rushing | Enable decisive action |
| Uncertainty | Doubt, paralysis | Provide clarity |
| Success | Euphoria, overconfidence | Celebrate but ground |
| Failure | Frustration, blame | Redirect to learning |

### Primary Emotional Goals

| Priority | Emotion | Description | Design Driver |
|----------|---------|-------------|---------------|
| P1 | **Confidence** | "I understand what's happening" | Transparency, human language |
| P1 | **Control** | "I can act when I need to" | Quick actions, visible options |
| P1 | **Clarity** | "I see what matters now" | State-driven density |
| P2 | **Calm Focus** | "I'm alert but not stressed" | Minimal UI, muted base colors |
| P2 | **Trust** | "The system does what it says" | Explained transitions |

### Emotional Journey Map

| Stage | Problem Emotion | Target Emotion | Design Response |
|-------|-----------------|----------------|-----------------|
| **First Visit** | Overwhelmed | Curious, guided | Onboarding wizard |
| **Learning** | Frustrated | Confident | Progressive disclosure |
| **Watching** | Bored | Calm, alert | Minimal UI, subtle pulse |
| **Signal Detected** | Anxious | Excited, prepared | Clear countdown, conditions |
| **Entering** | Nervous | Decisive | Confirmation feedback |
| **Monitoring** | Stressed | Calm, trusting | Prominent P&L, progress bar |
| **Profit Exit** | Relief | Pride, celebration | Animation, summary |
| **Loss Exit** | Angry | Understanding | Explanation, no blame |
| **Error** | Panic | Informed | Clear status, recovery path |

### Micro-Emotions

**Actively Create:**
- ✅ Confidence through visible system state
- ✅ Trust through explained decisions
- ✅ Accomplishment through progress tracking
- ✅ Delight through celebration moments

**Actively Prevent:**
- ❌ Confusion through jargon elimination
- ❌ Helplessness through always-visible actions
- ❌ Distrust through inline explanations
- ❌ Blame through neutral language on losses

### Design Implications

| Emotion | UX Implementation |
|---------|-------------------|
| **Confidence** | Human vocabulary, no S1/Z1/E1 jargon, "why" visible always |
| **Control** | Esc = emergency close, keyboard shortcuts, manual override |
| **Calm** | Muted colors during monitoring, white space, no blinking |
| **Excitement** | Animated 🔥 on signal, sound alert option, visual pop |
| **Trust** | Every transition badge explains reason, consistent patterns |
| **Pride** | Confetti on profit, session summary stats, streak counter |
| **Learning** | "What happened" breakdown on loss, indicator replay, no blame |

### Emotional Design Principles

1. **Manage Trading Anxiety**
   - Default state = calm, minimal, reassuring
   - Intensity increases only when action needed
   - Return to calm immediately after action

2. **Celebrate Wins, Explain Losses**
   - Profitable exits get visual celebration (confetti, sound)
   - Losses get clear, neutral explanation
   - Never use blame language ("failed", "error in your strategy")

3. **Build Trust Through Transparency**
   - Every system decision is visible and explained
   - No "magic" - user can trace any outcome
   - Connection status always visible

4. **Enable Decisive Action**
   - When action is needed, make it obvious
   - Reduce choices to essentials in critical moments
   - Confirm actions, but don't over-confirm

5. **Progress Creates Pride**
   - Track user achievements (first signal, first profit, streak)
   - Show improvement over time
   - Celebrate milestones

---

<!-- Next sections will be added in subsequent workflow steps -->
