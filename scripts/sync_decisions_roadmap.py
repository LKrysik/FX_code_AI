#!/usr/bin/env python3
"""
Decision-to-Roadmap Synchronization Script

Automatically synchronizes DECISIONS.md changes with ROADMAP.md updates.
Ensures roadmap reflects binding decisions affecting scope, timeline, or priorities.

Usage: python scripts/sync_decisions_roadmap.py
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class DecisionRoadmapSync:
    def __init__(self):
        self.docs_dir = Path("docs")
        self.decisions_file = self.docs_dir / "DECISIONS.md"
        self.roadmap_file = self.docs_dir / "ROADMAP.md"

    def parse_decisions(self) -> List[Dict]:
        """Parse binding decisions from DECISIONS.md"""
        with open(self.decisions_file, 'r', encoding='utf-8') as f:
            content = f.read()

        decisions = []
        # Find decision sections
        decision_pattern = r'### DECISION: (.+?)\n\*\*Date\*\*: (.+?)\n(.+?)(?=\n### |\n## |\Z)'
        matches = re.findall(decision_pattern, content, re.DOTALL)

        for title, date, body in matches:
            decision = {
                'title': title.strip(),
                'date': date.strip(),
                'body': body.strip(),
                'scope_impact': 'SCOPE' in body.upper(),
                'timeline_impact': 'TIMELINE' in body.upper() or 'SPRINT' in body.upper(),
                'priority_impact': 'PRIORITY' in body.upper() or 'P0' in body.upper()
            }
            decisions.append(decision)

        return decisions

    def parse_roadmap(self) -> Dict:
        """Parse current roadmap structure"""
        with open(self.roadmap_file, 'r', encoding='utf-8') as f:
            content = f.read()

        roadmap = {
            'last_review': re.search(r'> Last reviewed: (.+)', content),
            'business_vision': re.search(r'## BUSINESS VISION(.+?)(?=\n## |\Z)', content, re.DOTALL),
            'current_sprint': re.search(r'### 🎯 Next Release - (.+?)\(Target:', content, re.DOTALL)
        }

        return roadmap

    def generate_roadmap_updates(self, decisions: List[Dict]) -> List[Tuple[str, str, str]]:
        """
        Generate roadmap update recommendations based on decisions

        Returns: List of (section, update_text, justification) tuples
        """
        updates = []

        # Check for scope-changing decisions
        scope_decisions = [d for d in decisions if d['scope_impact']]
        if scope_decisions:
            update_text = f"**Updated Scope Based on Decision Analysis**:\n"
            for decision in scope_decisions[-3:]:  # Last 3 scope decisions
                update_text += f"- **{decision['title']}**: {decision['body'][:100]}...\n"
            update_text += f"- **Rationale**: Recent binding decisions require scope adjustments\n"
            update_text += f"- **Benefits**: Ensures roadmap reflects current strategic direction\n"
            update_text += f"- **Consistency**: Aligns planning with executive decisions\n"
            update_text += f"- **Quality Enhancement**: Prevents misallocation of development effort\n"
            update_text += f"- **Risks**: May require timeline adjustments, but necessary for project success\n"

            updates.append(("Current Sprint Section", update_text,
                          "Scope decisions must be reflected in active sprint planning"))

        # Check for timeline-impacting decisions
        timeline_decisions = [d for d in decisions if d['timeline_impact']]
        if timeline_decisions:
            update_text = "**Timeline Adjustments Required**:\n"
            for decision in timeline_decisions[-2:]:
                update_text += f"- {decision['title']}: Potential timeline impact\n"
            update_text += "**Recommendation**: Review sprint dates and dependencies"

            updates.append(("Timeline Section", update_text,
                          "Timeline decisions require roadmap date updates"))

        return updates

    def apply_updates(self, updates: List[Tuple[str, str, str]]) -> str:
        """Apply updates to roadmap with change logging"""
        if not updates:
            return "No updates required - decisions don't impact roadmap"

        # Read current roadmap
        with open(self.roadmap_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update last reviewed timestamp
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        content = re.sub(r'> Last reviewed: .+', f'> Last reviewed: {timestamp} via automated sync', content)

        # Apply updates (simplified - would need more sophisticated logic for production)
        change_log = f"## Automated Updates ({timestamp})\n\n"
        for section, update_text, justification in updates:
            change_log += f"### {section}\n"
            change_log += f"**Justification**: {justification}\n\n"
            change_log += f"{update_text}\n\n"

        # Prepend change log to content
        content = change_log + "---\n\n" + content

        # Write back
        with open(self.roadmap_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Applied {len(updates)} updates to roadmap"

    def run_sync(self) -> str:
        """Main synchronization workflow"""
        try:
            decisions = self.parse_decisions()
            roadmap = self.parse_roadmap()
            updates = self.generate_roadmap_updates(decisions)
            result = self.apply_updates(updates)

            return f"Sync completed: {result}\nProcessed {len(decisions)} decisions, generated {len(updates)} updates"

        except Exception as e:
            return f"Sync failed: {str(e)}"

if __name__ == "__main__":
    sync = DecisionRoadmapSync()
    result = sync.run_sync()
    print(result)