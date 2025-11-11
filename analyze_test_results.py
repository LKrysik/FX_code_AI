"""
Analyze test results XML to extract key metrics and failure patterns
"""
import xml.etree.ElementTree as ET
from collections import defaultdict
import json

def analyze_test_results(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    results = {
        'summary': {},
        'errors_by_type': defaultdict(list),
        'failures_by_test': defaultdict(list),
        'test_classes': defaultdict(int),
        'long_running_tests': [],
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
        }

    # Analyze individual test cases
    for testcase in root.findall('.//testcase'):
        classname = testcase.get('classname', '')
        name = testcase.get('name', '')
        time = float(testcase.get('time', 0))

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

if __name__ == '__main__':
    results = analyze_test_results('test_results_20251111_154527.xml')

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
    with open('test_analysis_detailed.json', 'w') as f:
        # Convert defaultdict to dict for JSON serialization
        output = {
            'summary': results['summary'],
            'errors_by_type': {k: v for k, v in results['errors_by_type'].items()},
            'failures_by_test': dict(results['failures_by_test']),
            'test_classes': dict(results['test_classes']),
            'long_running_tests': results['long_running_tests']
        }
        json.dump(output, f, indent=2)

    print("\n" + "=" * 80)
    print("Detailed analysis saved to: test_analysis_detailed.json")
    print("=" * 80)
