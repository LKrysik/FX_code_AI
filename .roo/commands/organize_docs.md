---
description: "Analyze and reorganize project documentation to eliminate duplicates, improve clarity, and ensure consistency across all artifacts."
---

# /organize_docs - Documentation Organization and Cleanup

**Purpose**: Analyze project documentation, identify duplicates and inconsistencies, reorganize content for better clarity and maintainability, and ensure all tasks and tests are well-defined.

**Usage**: /organize_docs

## Steps

### 1. Documentation Inventory and Analysis
- **Read all documentation files**: docs/MVP.md, docs/STATUS.md, docs/SPRINT_BACKLOG.md, docs/BUSINESS_GOALS.md, docs/ROADMAP.md, docs/DECISIONS.md, docs/KNOWLEDGE_BANK.md, and all feature docs in docs/features/, docs/sprints/, docs/evidence/
- **Identify duplicates**: Find overlapping content between files (e.g., same acceptance criteria in multiple places, repeated task descriptions)
- **Assess completeness**: Check if all tasks have proper acceptance criteria, testing requirements, and evidence references
- **Evaluate clarity**: Review if sections are well-organized, terminology is consistent, and navigation is intuitive
- **Decision impact analysis**: Review binding decisions in DECISIONS.md and assess their impact on MVP.md and ROADMAP.md content that may no longer be relevant

### 2. Duplicate Elimination and Consolidation
- **Merge redundant sections**: Combine similar content from different files (e.g., consolidate MVP requirements scattered across multiple docs)
- **Remove outdated content**: Eliminate completed tasks that are no longer relevant or references to removed features
- **Standardize terminology**: Ensure consistent use of terms across all documents (e.g., "P0" vs "MVP_CRITICAL", "acceptance criteria" vs "requirements")

### 2.5 MVP and Roadmap Updates Based on Decisions
- **Analyze binding decisions**: Review DECISIONS.md for decisions that invalidate sections of MVP.md or ROADMAP.md
- **Identify obsolete content**: Flag MVP/roadmap sections that are no longer relevant due to:
  - Completed features that exceeded original scope
  - Changed priorities from strategic decisions
  - Deprecated requirements from updated user feedback
  - Scope reductions or feature removals
- **Update with justification**: For each modification to MVP.md or ROADMAP.md:
  - **Benefits**: Explain how the change improves focus, reduces confusion, aligns with current reality
  - **Consistency improvements**: How it ensures all documents reflect the same project state
  - **Quality enhancements**: Better prioritization, clearer dependencies, more accurate timelines
  - **Risks**: Potential impact on stakeholder expectations or existing commitments
- **Apply to other documents**: Extend the same logic to BUSINESS_GOALS.md, KNOWLEDGE_BANK.md, and feature docs where decisions impact content

### 3. Content Reorganization
- **Logical grouping**: Reorganize sections within files for better flow (e.g., group related tasks together, put prerequisites before dependent tasks)
- **Priority-based ordering**: Sort tasks by priority (P0 first) and dependencies within each priority level
- **Execution sequence analysis**: Identify and document task dependencies, ensuring prerequisite tasks come before dependent ones
- **Cross-reference improvement**: Add proper links between related documents and sections
- **Status synchronization**: Ensure task statuses are consistent across STATUS.md and SPRINT_BACKLOG.md

### 4. Task and Test Definition Enhancement
- **Task refinement**: Ensure all tasks have clear user stories, acceptance criteria, testing requirements, and estimates
- **Test coverage verification**: Check that all features have corresponding test definitions
- **Evidence requirements**: Ensure all tasks specify what evidence is needed for completion

### 5. Decision Analysis and Cleanup
- **Review DECISIONS.md**: Analyze all decisions for relevance and current applicability
- **Identify obsolete decisions**: Flag decisions that are no longer relevant due to completed work, changed scope, or resolved issues
- **Critical evaluation for removal**: For each potentially obsolete decision:
  - Assess if the decision still impacts current work
  - Evaluate if the rationale is still valid
  - Consider if the decision has been superseded by newer ones
  - Determine if historical context is still valuable for future reference
- **Removal justification**: Provide detailed reasoning for removing obsolete decisions, including:
  - Why the decision is no longer relevant
  - What has changed since the decision was made
  - Impact of removal on documentation integrity
  - Preservation of any still-valuable historical context

### 6. Change Justification and Impact Assessment
For each proposed change:
- **Justification**: Explain why the change is needed (e.g., "Eliminates confusion caused by duplicate task definitions")
- **Impact on quality**: Assess if it improves clarity, reduces maintenance burden, or enhances traceability
- **Impact on readability**: Evaluate if it makes documents easier to navigate and understand
- **Potential drawbacks**: Identify any risks (e.g., "May require updating references in other documents")

### 7. Critical Evaluation of Proposed Changes
- **Consistency check**: Verify that changes maintain consistency with existing document structures and conventions
- **Completeness assessment**: Ensure no important information is lost in consolidation
- **Maintainability evaluation**: Assess if reorganized structure will be easier to maintain long-term
- **User impact**: Consider how changes affect different stakeholders (developers, product owners, testers)

### 7.5 Information Preservation Safeguards
- **Archival mechanism**: Before removing any content, create archived versions in docs/archive/ with timestamp and removal rationale
- **Historical context preservation**: For decisions and content being removed, extract and preserve:
  - Key learnings and insights that might be valuable for future projects
  - Rationale behind original decisions that influenced project direction
  - Metrics or evidence that demonstrated why certain approaches were chosen
- **Cross-reference validation**: Before removal, verify that no other documents reference the content being removed
- **Stakeholder notification**: Document what information is being archived and why, ensuring transparency
- **Recovery mechanism**: Maintain git history and provide clear paths to recover archived content if needed
- **Importance assessment**: For each piece of content under consideration for removal:
  - Evaluate if it contains unique insights not available elsewhere
  - Assess if it provides context for understanding current decisions
  - Determine if it has educational value for future team members
  - Consider if it supports compliance or audit requirements

### 9. Alternative Organization Proposals
- **Modular structure**: Propose breaking large documents into smaller, focused files
- **Template standardization**: Suggest standardized formats for common document types
- **Automation opportunities**: Identify areas where document generation could be automated
- **Navigation improvements**: Propose table of contents, indexes, or cross-reference systems

### 9.5 Automation Implementation Recommendations
- **Decision-to-Roadmap Sync Script**: Create Python script to automatically update ROADMAP.md when DECISIONS.md changes
  - Parse DECISIONS.md for binding decisions affecting scope/timeline
  - Auto-update roadmap sections with decision rationale and impact
  - Generate change logs with justification for transparency
- **Cross-Document Validation**: Implement validation scripts to check consistency between related documents
  - Verify task statuses match between STATUS.md and SPRINT_BACKLOG.md
  - Ensure roadmap goals align with BUSINESS_GOALS.md
  - Flag inconsistencies for manual review
- **Template-Based Generation**: Use Jinja2 templates for standardized document sections
  - Auto-populate task templates with required fields
  - Generate decision documentation with consistent formatting
  - Reduce manual formatting errors and ensure completeness

## Output
- **Change Summary**: List all changes made with justifications and impact assessments
- **Quality Metrics**: Before/after comparison of document clarity, duplicate reduction, and consistency
- **Recommendations**: Suggestions for ongoing documentation maintenance
- **Updated Files**: List of all modified documentation files

## When to Use
- After major feature integrations that add new documentation
- Before sprint planning to ensure backlog clarity
- When documentation feels disorganized or hard to navigate
- After feedback reveals documentation gaps or inconsistencies
- During project retrospectives to improve documentation practices