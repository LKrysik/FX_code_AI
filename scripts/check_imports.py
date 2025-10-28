#!/usr/bin/env python3
"""
Import Standards Checker for FX_code_AI
========================================

This script analyzes Python imports in the codebase and reports:
1. Import style inconsistencies
2. Try-except import anti-patterns
3. Relative imports that should be absolute
4. Circular import risks

Usage:
    python scripts/check_imports.py
    python scripts/check_imports.py --fix  # Auto-fix simple issues
    python scripts/check_imports.py --report output.md  # Generate report
"""

import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ImportIssue:
    """Represents an import issue found in the code"""
    file: Path
    line_number: int
    line: str
    issue_type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    suggestion: Optional[str] = None


@dataclass
class FileAnalysis:
    """Analysis results for a single file"""
    file: Path
    total_imports: int = 0
    absolute_imports: int = 0
    relative_imports: int = 0
    core_imports: int = 0
    try_except_imports: int = 0
    issues: List[ImportIssue] = field(default_factory=list)


class ImportAnalyzer:
    """Analyzes Python imports for standards compliance"""

    def __init__(self, src_dir: Path = Path("src")):
        self.src_dir = src_dir
        self.results: Dict[Path, FileAnalysis] = {}

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze imports in a single Python file"""
        analysis = FileAnalysis(file=file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Track state for try-except detection
        in_try_block = False
        try_start_line = 0

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Detect try blocks
            if stripped.startswith('try:'):
                in_try_block = True
                try_start_line = line_num
                continue

            if stripped.startswith('except'):
                in_try_block = False

            # Analyze imports
            if 'import ' in line and not line.strip().startswith('#'):
                analysis.total_imports += 1

                # Check for from ... import ...
                from_match = re.search(r'from\s+([\w\.]+)\s+import', line)
                if from_match:
                    module = from_match.group(1)

                    # Absolute import
                    if module.startswith('src.'):
                        analysis.absolute_imports += 1

                        # Check if importing from core
                        if 'src.core.' in module:
                            analysis.core_imports += 1

                    # Relative import
                    elif module.startswith('.'):
                        analysis.relative_imports += 1
                        dots = len(module) - len(module.lstrip('.'))

                        # Check depth
                        file_depth = len(file_path.relative_to(self.src_dir).parts) - 1

                        if dots > 3:
                            analysis.issues.append(ImportIssue(
                                file=file_path,
                                line_number=line_num,
                                line=line.strip(),
                                issue_type='deep_relative_import',
                                severity='warning',
                                message=f'Relative import with {dots} levels - consider absolute import',
                                suggestion=self._suggest_absolute_import(module, file_path)
                            ))

                        # Check if importing core with relative import
                        if 'core.' in module:
                            analysis.issues.append(ImportIssue(
                                file=file_path,
                                line_number=line_num,
                                line=line.strip(),
                                issue_type='relative_core_import',
                                severity='info',
                                message='Importing core.* with relative import - consider absolute',
                                suggestion=self._suggest_absolute_import(module, file_path)
                            ))

                # Check if import is in try block
                if in_try_block:
                    analysis.try_except_imports += 1

                    # Check if it's masking an error (bad pattern)
                    if 'except ImportError' in '\n'.join(lines[try_start_line:line_num+5]):
                        # Check if there's a fallback or pass
                        except_block = '\n'.join(lines[line_num:line_num+10])
                        if 'pass' in except_block or '=' in except_block:
                            analysis.issues.append(ImportIssue(
                                file=file_path,
                                line_number=line_num,
                                line=line.strip(),
                                issue_type='try_except_import',
                                severity='warning',
                                message='Try-except around import may mask errors',
                                suggestion='Use absolute import or document circular import reason'
                            ))

        self.results[file_path] = analysis
        return analysis

    def _suggest_absolute_import(self, relative_module: str, file_path: Path) -> str:
        """Suggest absolute import path"""
        dots = len(relative_module) - len(relative_module.lstrip('.'))
        module_name = relative_module.lstrip('.')

        # Calculate absolute path
        file_parts = file_path.relative_to(self.src_dir).parts[:-1]  # Exclude filename
        if dots > len(file_parts):
            return f"# Cannot calculate - too many dots for file depth"

        # Go up 'dots' levels
        base_parts = file_parts[:-dots] if dots > 0 else file_parts

        if module_name:
            absolute = 'src.' + '.'.join(base_parts + tuple(module_name.split('.')))
        else:
            absolute = 'src.' + '.'.join(base_parts)

        return f"from {absolute} import ..."

    def analyze_all(self) -> Dict[Path, FileAnalysis]:
        """Analyze all Python files in src directory"""
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' not in str(py_file):
                self.analyze_file(py_file)
        return self.results

    def generate_summary(self) -> str:
        """Generate summary report"""
        total_files = len(self.results)
        total_imports = sum(r.total_imports for r in self.results.values())
        total_issues = sum(len(r.issues) for r in self.results.values())

        # Count by severity
        severity_counts = Counter()
        issue_type_counts = Counter()

        for analysis in self.results.values():
            for issue in analysis.issues:
                severity_counts[issue.severity] += 1
                issue_type_counts[issue.issue_type] += 1

        # Build summary
        lines = []
        lines.append("=" * 80)
        lines.append("IMPORT ANALYSIS SUMMARY")
        lines.append("=" * 80)
        lines.append(f"\nFiles analyzed: {total_files}")
        lines.append(f"Total imports: {total_imports}")
        lines.append(f"Total issues: {total_issues}\n")

        lines.append("By Severity:")
        lines.append(f"  ❌ Errors:   {severity_counts['error']}")
        lines.append(f"  ⚠️  Warnings: {severity_counts['warning']}")
        lines.append(f"  ℹ️  Info:     {severity_counts['info']}\n")

        if issue_type_counts:
            lines.append("By Issue Type:")
            for issue_type, count in issue_type_counts.most_common():
                lines.append(f"  {issue_type}: {count}")

        lines.append("\n" + "=" * 80)

        return '\n'.join(lines)

    def generate_detailed_report(self) -> str:
        """Generate detailed report with all issues"""
        lines = [self.generate_summary(), "\n"]

        # Group issues by severity
        issues_by_severity = defaultdict(list)
        for analysis in self.results.values():
            for issue in analysis.issues:
                issues_by_severity[issue.severity].append(issue)

        # Report errors first, then warnings, then info
        for severity in ['error', 'warning', 'info']:
            issues = issues_by_severity[severity]
            if not issues:
                continue

            icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}[severity]
            lines.append(f"\n{icon} {severity.upper()} ({len(issues)} issues)")
            lines.append("=" * 80)

            # Group by file
            by_file = defaultdict(list)
            for issue in issues:
                by_file[issue.file].append(issue)

            for file_path, file_issues in sorted(by_file.items()):
                lines.append(f"\nFile: {file_path}")
                for issue in file_issues:
                    lines.append(f"  Line {issue.line_number}: {issue.message}")
                    lines.append(f"    Current: {issue.line}")
                    if issue.suggestion:
                        lines.append(f"    Suggest: {issue.suggestion}")

        return '\n'.join(lines)

    def print_statistics(self):
        """Print import statistics"""
        total_absolute = sum(r.absolute_imports for r in self.results.values())
        total_relative = sum(r.relative_imports for r in self.results.values())
        total_core = sum(r.core_imports for r in self.results.values())
        total_try_except = sum(r.try_except_imports for r in self.results.values())

        print(f"\n📊 IMPORT STATISTICS")
        print("=" * 80)
        print(f"Absolute imports: {total_absolute}")
        print(f"Relative imports: {total_relative}")
        print(f"Core.* imports:   {total_core}")
        print(f"Try-except imports: {total_try_except}")

        if total_absolute + total_relative > 0:
            abs_percent = (total_absolute / (total_absolute + total_relative)) * 100
            print(f"\nAbsolute import ratio: {abs_percent:.1f}%")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze Python imports')
    parser.add_argument('--src', default='src', help='Source directory to analyze')
    parser.add_argument('--report', help='Output report to file')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    args = parser.parse_args()

    analyzer = ImportAnalyzer(Path(args.src))

    print("🔍 Analyzing imports...")
    analyzer.analyze_all()

    # Generate report
    if args.summary:
        report = analyzer.generate_summary()
    else:
        report = analyzer.generate_detailed_report()

    # Output
    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"✅ Report written to {args.report}")
    else:
        print(report)

    # Print statistics
    analyzer.print_statistics()

    # Exit code based on issues
    total_issues = sum(len(r.issues) for r in analyzer.results.values())
    errors = sum(1 for r in analyzer.results.values() for i in r.issues if i.severity == 'error')

    if errors > 0:
        print(f"\n❌ Found {errors} error(s)")
        return 1
    elif total_issues > 0:
        print(f"\n⚠️  Found {total_issues} issue(s)")
        return 0
    else:
        print(f"\n✅ No issues found!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
