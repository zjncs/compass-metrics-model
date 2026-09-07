"""Regression tests for is_modular language-specific keywords.

is_modular counted function/class declarations by checking whether a line
starts with a keyword. Java, PHP and Go were given Python's 'def ' keyword
(which never appears in those languages) and perl uses 'sub', so
function_count was always 0 for them; Java class declarations carry access
modifiers before 'class' ('public class Foo') and never matched
startswith('class ') either.

These tests run on temporary files, so no repository checkout or network
access is required.
"""
import textwrap

from compass_metrics.code_readability import is_modular

JAVA = """
public class Foo {
    public void bar() {
    }
}
"""

PHP = """
<?php
function add($a, $b) {
    return $a + $b;
}
class Calculator {
}
"""

GO = """
package main

func main() {
}
"""

PERL = """
sub compute {
    return 1;
}
package Utils;
"""

PYTHON = """
def foo():
    pass

class Bar:
    pass
"""

JAVASCRIPT = """
function foo() {
}

class Bar {
}
"""


def test_java_counts_methods_and_class(tmp_path):
    path = tmp_path / "Foo.java"
    path.write_text(textwrap.dedent(JAVA), encoding="utf-8")
    assert is_modular(str(path)) == (1, 1)


def test_php_counts_functions_and_class(tmp_path):
    path = tmp_path / "calc.php"
    path.write_text(textwrap.dedent(PHP), encoding="utf-8")
    assert is_modular(str(path)) == (1, 1)


def test_go_counts_funcs(tmp_path):
    path = tmp_path / "main.go"
    path.write_text(textwrap.dedent(GO), encoding="utf-8")
    assert is_modular(str(path)) == (1, 0)


def test_perl_counts_subs_and_package(tmp_path):
    path = tmp_path / "utils.pl"
    path.write_text(textwrap.dedent(PERL), encoding="utf-8")
    assert is_modular(str(path)) == (1, 1)


def test_python_counts_unchanged(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text(textwrap.dedent(PYTHON), encoding="utf-8")
    assert is_modular(str(path)) == (1, 1)


def test_javascript_counts_unchanged(tmp_path):
    path = tmp_path / "mod.js"
    path.write_text(textwrap.dedent(JAVASCRIPT), encoding="utf-8")
    assert is_modular(str(path)) == (1, 1)
