"""Detect XML namespace prefixes a workflow declares but never uses.

Extracting a block into a new workflow by copying the parent's header carries
namespace prefixes the extracted body does not need. Unused prefixes that point at
Integration Service connector bundles fail to resolve when the project is opened in
UiPath Studio, so this check keeps declarations and usage in step.

Run from the project root:  python Tests/Validation/validate_namespace_usage.py
Exits non-zero when any workflow declares a prefix it does not use.
"""

import os
import re
import sys

SKIP_DIRS = {'.git', '.storage', '.objects', '.screenshots', '.settings', '.local'}
# Prefixes XAML requires structurally even when no element or attribute names them.
# 'this' is Studio boilerplate for the workflow's own class and is always emitted.
ALWAYS_KEEP = {'mc', 'x', 'sap', 'sap2010', 'sco', 'this'}


def declared_prefixes(header):
    return dict(re.findall(r'xmlns:([\w.]+)="([^"]*)"', header))


def used_prefixes(body):
    used = set(re.findall(r'<(?:/)?([\w.]+):', body))
    used |= set(re.findall(r'\s([\w.]+):[\w.]+\s*=', body))
    for attr in re.findall(r'(?:TypeArguments|Type)="([^"]+)"', body):
        used |= set(re.findall(r'([\w.]+):', attr))
    for expression in re.findall(r'"\[([^"]*)\]"', body):
        used |= set(re.findall(r'([\w.]+):', expression))
    return used


def main(root='.'):
    findings = []
    scanned = 0
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(names):
            if not name.endswith('.xaml'):
                continue
            path = os.path.join(base, name)
            text = open(path, encoding='utf-8', errors='replace').read()
            start = text.index('<Activity')
            header = text[start:text.index('>', start) + 1]
            body = text[text.index('>', start) + 1:]
            scanned += 1
            unused = sorted(p for p in declared_prefixes(header)
                            if p not in ALWAYS_KEEP and p not in used_prefixes(body))
            for prefix in unused:
                findings.append((path, prefix, declared_prefixes(header)[prefix]))

    print(f'Workflows scanned      : {scanned}')
    print(f'Unused namespace decls : {len(findings)}')
    for path, prefix, uri in findings:
        print(f'  UNUSED {path}: xmlns:{prefix} -> {uri[:78]}')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '.'))
