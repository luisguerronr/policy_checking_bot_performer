"""Static validation of UiPath workflow references and argument contracts.

Checks every .xaml workflow in the project for:
  1. well-formed XML;
  2. Invoke Workflow File targets that exist on disk;
  3. argument keys passed at each invoke site that are declared by the target;
  4. argument direction and type agreement between caller and target;
  5. declared input arguments that a caller does not supply (reported as warnings).

Run from the project root:  python Tests/Validation/validate_workflow_references.py
Exits non-zero when any error is found.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

XAML_NS = 'http://schemas.microsoft.com/winfx/2006/xaml'
UIPATH_NS = 'http://schemas.uipath.com/workflow/activities'
ACTIVITIES_NS = 'http://schemas.microsoft.com/netfx/2009/xaml/activities'

SKIP_DIRS = {'.git', '.storage', '.objects', '.screenshots', '.settings', '.local'}
ARGUMENT_TAGS = {
    f'{{{ACTIVITIES_NS}}}InArgument': 'In',
    f'{{{ACTIVITIES_NS}}}OutArgument': 'Out',
    f'{{{ACTIVITIES_NS}}}InOutArgument': 'InOut',
}
DIRECTION_PATTERN = re.compile(r'^(In|Out|InOut)Argument\((.*)\)$', re.S)
PREFIX_PATTERN = re.compile(r'\b([A-Za-z_][\w.]*):')


def parse_with_prefixes(path):
    """Return (root_element, {prefix: namespace_uri}) for one XAML file."""
    prefixes = {}
    root = None
    for event, payload in ET.iterparse(path, events=('start-ns', 'start')):
        if event == 'start-ns':
            prefixes.setdefault(payload[0], payload[1])
        elif root is None:
            root = payload
    return root, prefixes


def canonical_type(type_text, prefixes):
    """Rewrite prefixed type names to namespace URIs so aliases compare equal."""
    if type_text is None:
        return None
    collapsed = re.sub(r'\s+', '', type_text)
    return PREFIX_PATTERN.sub(lambda m: '{%s}' % prefixes.get(m.group(1), m.group(1)), collapsed)


def declared_arguments(path, cache):
    """Map argument name -> (direction, canonical type) for a workflow's x:Members."""
    if path in cache:
        return cache[path]
    result = {}
    root, prefixes = parse_with_prefixes(path)
    members = root.find(f'{{{XAML_NS}}}Members') if root is not None else None
    if members is not None:
        for prop in members.findall(f'{{{XAML_NS}}}Property'):
            name = prop.get('Name')
            match = DIRECTION_PATTERN.match((prop.get('Type') or '').strip())
            if name and match:
                result[name] = (match.group(1), canonical_type(match.group(2), prefixes))
    cache[path] = result
    return result


def invoke_sites(path):
    """Yield (target_workflow_path, {argument key: (direction, canonical type)})."""
    root, prefixes = parse_with_prefixes(path)
    if root is None:
        return
    for invoke in root.iter(f'{{{UIPATH_NS}}}InvokeWorkflowFile'):
        target = invoke.get('WorkflowFileName')
        if not target:
            continue
        passed = {}
        container = invoke.find(f'{{{UIPATH_NS}}}InvokeWorkflowFile.Arguments')
        if container is not None:
            for argument in container:
                direction = ARGUMENT_TAGS.get(argument.tag)
                key = argument.get(f'{{{XAML_NS}}}Key')
                if direction and key:
                    passed[key] = (direction, canonical_type(argument.get(f'{{{XAML_NS}}}TypeArguments'), prefixes))
        yield target, passed


def workflow_files(root):
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(names):
            if name.endswith('.xaml'):
                yield os.path.join(base, name)


def main(root='.'):
    errors = []
    warnings = []
    cache = {}
    files = list(workflow_files(root))
    invoke_count = 0

    for path in files:
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            errors.append(f'{path}: malformed XML: {exc}')
            continue

        for target, passed in invoke_sites(path):
            invoke_count += 1
            target_path = os.path.join(root, target.replace('\\', os.sep))
            if not os.path.isfile(target_path):
                errors.append(f'{path}: invokes missing workflow "{target}"')
                continue

            declared = declared_arguments(target_path, cache)
            for key, (direction, type_name) in sorted(passed.items()):
                if key not in declared:
                    errors.append(f'{path}: passes "{key}" to "{target}", which does not declare it')
                    continue
                expected_direction, expected_type = declared[key]
                if direction != expected_direction:
                    errors.append(
                        f'{path}: passes "{key}" to "{target}" as {direction}Argument, '
                        f'declared {expected_direction}Argument')
                elif type_name != expected_type:
                    errors.append(
                        f'{path}: passes "{key}" to "{target}" with type {type_name}, '
                        f'declared {expected_type}')

            for key, (direction, _) in sorted(declared.items()):
                if direction in ('In', 'InOut') and key not in passed:
                    warnings.append(f'{path}: does not supply "{key}" ({direction}Argument) to "{target}"')

    print(f'Workflows scanned : {len(files)}')
    print(f'Invoke sites      : {invoke_count}')
    print(f'Errors            : {len(errors)}')
    for item in errors:
        print(f'  ERROR {item}')
    print(f'Warnings          : {len(warnings)}')
    for item in warnings:
        print(f'  WARN  {item}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '.'))
