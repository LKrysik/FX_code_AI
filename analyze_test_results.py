"""
Analyze test results XML to extract key metrics and failure patterns
"""
import xml.etree.ElementTree as ET
from collections import defaultdict
import json
from datetime import datetime
from pathlib import Path

def format_test_path(classname, name):
    """Format test path in readable format

    Args:
        classname: Test class name (e.g., 'api.test_auth.TestAuthLogin')
        name: Test name (e.g., 'test_login_success')

    Returns:
        Formatted path (e.g., 'tests_e2e/api/test_auth.py::TestAuthLogin::test_login_success')
    """
    if not classname:
        return f"<unknown>::{name}"

    # Convert dotted classname to file path
    parts = classname.split('.')
    if len(parts) >= 2:
        # e.g., 'api.test_auth.TestAuthLogin' -> 'tests_e2e/api/test_auth.py::TestAuthLogin'
        file_path = 'tests_e2e/' + '/'.join(parts[:-1]) + '.py'
        class_name = parts[-1]
        return f"{file_path}::{class_name}::{name}"
    else:
        return f"{classname}::{name}"

def format_duration(seconds):
    """Format duration in human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., '44m 9s', '3.85s', '1h 23m')
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def analyze_test_results(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    results = {
        'summary': {},
        'errors_by_type': defaultdict(list),
        'failures_by_test': defaultdict(list),
        'test_classes': defaultdict(int),
        'long_running_tests': [],
        'all_tests': [],  # NEW: Complete list of all tests
    }

    # Get top-level summary
    testsuite = root.find('.//testsuite')
    if testsuite is not None:
        results['summary'] = {
            'total_tests': int(testsuite.get('tests', 0)),
            'errors': int(testsuite.get('errors', 0)),
            'failures': int(testsuite.get('failures', 0)),
            'skipped': int(testsuite.get('skipped', 0)),
            'time': float(testsuite.get('time', 0)),
            'timestamp': testsuite.get('timestamp', ''),
            'hostname': testsuite.get('hostname', ''),
        }
        # Calculate passed tests
        results['summary']['passed'] = (
            results['summary']['total_tests'] -
            results['summary']['errors'] -
            results['summary']['failures'] -
            results['summary']['skipped']
        )

    # Analyze individual test cases
    for testcase in root.findall('.//testcase'):
        classname = testcase.get('classname', '')
        name = testcase.get('name', '')
        time = float(testcase.get('time', 0))

        # Determine test status
        has_error = testcase.find('error') is not None
        has_failure = testcase.find('failure') is not None
        has_skipped = testcase.find('skipped') is not None

        if has_error:
            status = 'error'
            error_elem = testcase.find('error')
            error_msg = error_elem.get('message', '') if error_elem is not None else ''
            error_text = error_elem.text[:200] if error_elem is not None and error_elem.text else ''
        elif has_failure:
            status = 'failed'
            failure_elem = testcase.find('failure')
            error_msg = failure_elem.get('message', '') if failure_elem is not None else ''
            error_text = failure_elem.text[:200] if failure_elem is not None and failure_elem.text else ''
        elif has_skipped:
            status = 'skipped'
            skipped_elem = testcase.find('skipped')
            error_msg = skipped_elem.get('message', '') if skipped_elem is not None else ''
            error_text = skipped_elem.text[:200] if skipped_elem is not None and skipped_elem.text else ''
        else:
            status = 'passed'
            error_msg = ''
            error_text = ''

        # Add to all_tests list
        results['all_tests'].append({
            'classname': classname,
            'name': name,
            'path': format_test_path(classname, name),
            'time': time,
            'status': status,
            'error_message': error_msg,
            'error_text': error_text,
        })

        # Track test classes
        if classname:
            results['test_classes'][classname] += 1

        # Track long-running tests (>10 seconds)
        if time > 10:
            results['long_running_tests'].append({
                'class': classname,
                'name': name,
                'time': time
            })

        # Collect errors
        for error in testcase.findall('.//error'):
            error_msg = error.get('message', '')
            results['errors_by_type'][error_msg].append({
                'class': classname,
                'name': name,
                'time': time
            })

        # Collect failures
        for failure in testcase.findall('.//failure'):
            failure_msg = failure.get('message', '')
            results['failures_by_test'][f"{classname}::{name}"].append({
                'message': failure_msg,
                'text': failure.text[:500] if failure.text else ''  # First 500 chars
            })

    return results

def generate_readable_text_report(xml_file, output_file='test_results_summary.txt'):
    """Generate human-readable text report from JUnit XML

    Args:
        xml_file: Path to JUnit XML file
        output_file: Path to output text report (default: test_results_summary.txt)

    Returns:
        Path to generated report file
    """
    results = analyze_test_results(xml_file)
    summary = results['summary']
    all_tests = results['all_tests']

    # Group tests by status
    passed_tests = [t for t in all_tests if t['status'] == 'passed']
    failed_tests = [t for t in all_tests if t['status'] == 'failed']
    error_tests = [t for t in all_tests if t['status'] == 'error']
    skipped_tests = [t for t in all_tests if t['status'] == 'skipped']

    # Build report content
    lines = []
    lines.append("=" * 80)
    lines.append("                          TEST RESULTS SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Duration: {format_duration(summary.get('time', 0))}")
    lines.append(f"XML Source: {Path(xml_file).name}")
    lines.append("")
    lines.append(f"Total Tests: {summary.get('total_tests', 0)}")
    lines.append(f"Passed:  {summary.get('passed', 0):3d} ({summary.get('passed', 0) / max(summary.get('total_tests', 1), 1) * 100:5.1f}%)")
    lines.append(f"Failed:  {summary.get('failures', 0):3d} ({summary.get('failures', 0) / max(summary.get('total_tests', 1), 1) * 100:5.1f}%)")
    lines.append(f"Errors:  {summary.get('errors', 0):3d} ({summary.get('errors', 0) / max(summary.get('total_tests', 1), 1) * 100:5.1f}%)")
    lines.append(f"Skipped: {summary.get('skipped', 0):3d} ({summary.get('skipped', 0) / max(summary.get('total_tests', 1), 1) * 100:5.1f}%)")
    lines.append("")

    # Passed tests section
    if passed_tests:
        lines.append("=" * 80)
        lines.append(f"                           PASSED TESTS ({len(passed_tests)})")
        lines.append("=" * 80)
        # Show first 50 passed tests
        for test in passed_tests[:50]:
            lines.append(f"✓ {test['path']} ({test['time']:.2f}s)")
        if len(passed_tests) > 50:
            lines.append(f"... and {len(passed_tests) - 50} more (see JSON for full list)")
        lines.append("")

    # Failed tests section
    if failed_tests:
        lines.append("=" * 80)
        lines.append(f"                           FAILED TESTS ({len(failed_tests)})")
        lines.append("=" * 80)
        for test in failed_tests:
            lines.append(f"✗ {test['path']} ({test['time']:.2f}s)")
            if test['error_message']:
                lines.append(f"  Error: {test['error_message']}")
            if test['error_text']:
                # Show first line of error text
                first_line = test['error_text'].split('\n')[0]
                lines.append(f"  Details: {first_line}")
            lines.append("")

    # Error tests section
    if error_tests:
        lines.append("=" * 80)
        lines.append(f"                           ERROR TESTS ({len(error_tests)})")
        lines.append("=" * 80)
        # Group errors by error message for better readability
        errors_grouped = defaultdict(list)
        for test in error_tests:
            errors_grouped[test['error_message']].append(test)

        # Show top 10 most common errors
        sorted_error_groups = sorted(errors_grouped.items(), key=lambda x: len(x[1]), reverse=True)
        for error_msg, tests in sorted_error_groups[:10]:
            lines.append(f"{error_msg} ({len(tests)} occurrences)")
            for test in tests[:5]:  # Show first 5 tests with this error
                lines.append(f"  - {test['path']} ({test['time']:.2f}s)")
            if len(tests) > 5:
                lines.append(f"  ... and {len(tests) - 5} more with same error")
            lines.append("")

        if len(sorted_error_groups) > 10:
            lines.append(f"... and {len(sorted_error_groups) - 10} more error types (see JSON for full list)")
            lines.append("")

    # Skipped tests section
    if skipped_tests:
        lines.append("=" * 80)
        lines.append(f"                          SKIPPED TESTS ({len(skipped_tests)})")
        lines.append("=" * 80)
        for test in skipped_tests:
            lines.append(f"⊘ {test['path']} ({test['time']:.2f}s)")
            if test['error_message']:
                lines.append(f"  Reason: {test['error_message']}")
        lines.append("")

    # Long-running tests section
    if results['long_running_tests']:
        lines.append("=" * 80)
        lines.append(f"                      LONG RUNNING TESTS (>10s) - {len(results['long_running_tests'])}")
        lines.append("=" * 80)
        sorted_long = sorted(results['long_running_tests'], key=lambda x: x['time'], reverse=True)[:20]
        for test in sorted_long:
            path = format_test_path(test['class'], test['name'])
            lines.append(f"{test['time']:.2f}s - {path}")
        lines.append("")

    # Footer
    lines.append("=" * 80)
    lines.append("Detailed JSON analysis: test_analysis_detailed.json")
    lines.append(f"Full XML results: {Path(xml_file).name}")
    lines.append("=" * 80)

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return output_file

def main(xml_file=None):
    """Main entry point for command-line usage

    Args:
        xml_file: Path to JUnit XML file (default: test_results_20251111_154527.xml)
    """
    if xml_file is None:
        xml_file = 'test_results_20251111_154527.xml'

    print(f"Analyzing test results from: {xml_file}")

    results = analyze_test_results(xml_file)

    print("=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    print(json.dumps(results['summary'], indent=2))

    print("\n" + "=" * 80)
    print("ERRORS BY TYPE (Top 10)")
    print("=" * 80)
    sorted_errors = sorted(results['errors_by_type'].items(),
                          key=lambda x: len(x[1]), reverse=True)[:10]
    for error_type, cases in sorted_errors:
        print(f"\n{error_type}: {len(cases)} occurrences")
        for case in cases[:3]:  # Show first 3
            print(f"  - {case['class']}::{case['name']} ({case['time']:.2f}s)")

    print("\n" + "=" * 80)
    print("FAILURES BY TEST (Top 20)")
    print("=" * 80)
    for test_name, failures in list(results['failures_by_test'].items())[:20]:
        print(f"\n{test_name}:")
        for failure in failures[:2]:  # Show first 2 failures per test
            print(f"  Message: {failure['message']}")
            print(f"  Details: {failure['text'][:200]}...")

    print("\n" + "=" * 80)
    print("TEST CLASSES DISTRIBUTION")
    print("=" * 80)
    sorted_classes = sorted(results['test_classes'].items(),
                           key=lambda x: x[1], reverse=True)[:15]
    for classname, count in sorted_classes:
        print(f"{classname}: {count} tests")

    print("\n" + "=" * 80)
    print(f"LONG RUNNING TESTS (>{10}s) - Total: {len(results['long_running_tests'])}")
    print("=" * 80)
    sorted_long = sorted(results['long_running_tests'],
                        key=lambda x: x['time'], reverse=True)[:20]
    for test in sorted_long:
        print(f"{test['time']:.2f}s - {test['class']}::{test['name']}")

    # Save detailed results
    with open('test_analysis_detailed.json', 'w', encoding='utf-8') as f:
        # Convert defaultdict to dict for JSON serialization
        output = {
            'summary': results['summary'],
            'errors_by_type': {k: v for k, v in results['errors_by_type'].items()},
            'failures_by_test': dict(results['failures_by_test']),
            'test_classes': dict(results['test_classes']),
            'long_running_tests': results['long_running_tests'],
            'all_tests': results['all_tests'],  # Include all tests in JSON
        }
        json.dump(output, f, indent=2)

    print("\n" + "=" * 80)
    print("Detailed analysis saved to: test_analysis_detailed.json")
    print("=" * 80)

    # Generate readable text report
    report_file = generate_readable_text_report(xml_file)
    print(f"Readable summary report saved to: {report_file}")
    print("=" * 80)

if __name__ == '__main__':
    import sys
    # Accept XML file path as command-line argument
    xml_file = sys.argv[1] if len(sys.argv) > 1 else None
    main(xml_file)
