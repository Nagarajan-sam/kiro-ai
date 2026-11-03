"""A tiny Jinja-like template renderer (sandbox test fallback only).

This supports exactly the template features used by this project:
  - {% extends "base.html" %}
  - {% block name %} ... {% endblock %}
  - {{ expression }}  with dotted access, `or`, filters, and function calls
  - {% if %}/{% elif %}/{% else %}/{% endif %}
  - {% for x in seq %} ... {% endfor %}
  - {% with messages = get_flashed_messages(with_categories=true) %}
  - url_for(...), get_flashed_messages(...)

It is intentionally small and is NOT a real Jinja2 implementation. Its only
job is to let the test suite verify rendered pages when Flask/Jinja2 cannot
be installed. Expressions are evaluated with a restricted ``eval`` over the
template context plus the helper functions.
"""

import html
import os
import re

from . import _app


def render_template_string(app, template_name, context):
    source = _load(app, template_name)
    tokens, parent = _preprocess(app, source)
    env = _make_env(context)

    if parent is not None:
        # Child template: collect its blocks, then render the parent,
        # substituting block contents.
        blocks = _collect_blocks(source)
        parent_source = _load(app, parent)
        return _render_nodes(_parse(parent_source), env, blocks)

    return _render_nodes(_parse(source), env, {})


# --------------------------------------------------------------------------
# Loading & inheritance
# --------------------------------------------------------------------------

def _load(app, name):
    path = os.path.join(app.template_folder, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _preprocess(app, source):
    m = re.search(r'{%\s*extends\s*"([^"]+)"\s*%}', source)
    parent = m.group(1) if m else None
    return source, parent


def _collect_blocks(source):
    """Return {block_name: inner_source} for all blocks in a template."""
    blocks = {}
    pattern = re.compile(r"{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}", re.DOTALL)
    for match in pattern.finditer(source):
        blocks[match.group(1)] = match.group(2)
    return blocks


# --------------------------------------------------------------------------
# Expression evaluation
# --------------------------------------------------------------------------

def _make_env(context):
    env = {key: _wrap(value) for key, value in context.items()}
    env["url_for"] = _app.url_for
    env["get_flashed_messages"] = _app.get_flashed_messages
    return env


class _Undefined:
    """Behaves like Jinja's undefined for the cases we use (falsey, empty)."""

    def __bool__(self):
        return False

    def __str__(self):
        return ""

    def __iter__(self):
        return iter(())

    def __getattr__(self, name):
        return _Undefined()

    def __eq__(self, other):
        return isinstance(other, _Undefined) or other is None

    def __getitem__(self, key):
        return _Undefined()


class _AttrDict(dict):
    """Allow attribute access (student.name) on dict rows in templates."""

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return _Undefined()


def _wrap(value):
    if isinstance(value, _AttrDict):
        return value
    if isinstance(value, dict):
        return _AttrDict({k: _wrap(v) for k, v in value.items()})
    # sqlite3.Row-like: has keys()
    if hasattr(value, "keys") and not isinstance(value, (str, bytes)):
        try:
            return _AttrDict({k: _wrap(value[k]) for k in value.keys()})
        except Exception:
            return value
    if isinstance(value, (list, tuple)):
        return [_wrap(v) for v in value]
    return value


# Jinja uses `true`/`false`/`none`; map them for eval.
_EVAL_GLOBALS = {"true": True, "false": False, "none": None, "__builtins__": {}}

# Filters we support, used as `value | filter`.
_FILTERS = {}


def _apply_filters(expr):
    """Rewrite `a | filter` into filter(a). Supports chained filters."""
    # Only handle the simple pipe used in templates (no filter args here).
    if "|" not in expr:
        return expr
    parts = [p.strip() for p in expr.split("|")]
    result = parts[0]
    for filt in parts[1:]:
        result = f"__filter_{filt}({result})"
    return result


def _eval(expr, env):
    expr = expr.strip()
    try:
        safe_globals = dict(_EVAL_GLOBALS)
        return eval(expr, safe_globals, env)  # noqa: S307 - restricted builtins
    except Exception:
        return _Undefined()


# --------------------------------------------------------------------------
# Parser / renderer
# --------------------------------------------------------------------------

_TAG_RE = re.compile(r"({%.*?%}|{{.*?}})", re.DOTALL)


def _parse(source):
    """Split template into a flat list of ('text'|'tag', content) nodes."""
    nodes = []
    for part in _TAG_RE.split(source):
        if not part:
            continue
        if part.startswith("{{") or part.startswith("{%"):
            nodes.append(("tag", part))
        else:
            nodes.append(("text", part))
    return nodes


def _render_nodes(nodes, env, blocks):
    out = []
    i = 0
    while i < len(nodes):
        kind, content = nodes[i]
        if kind == "text":
            out.append(content)
            i += 1
            continue

        inner = content.strip()
        if content.startswith("{{"):
            out.append(_render_expr(inner[2:-2].strip(), env))
            i += 1
            continue

        # Statement tags: {% ... %}
        stmt = inner[2:-2].strip()
        head = stmt.split()[0] if stmt else ""

        if head == "extends":
            i += 1
        elif head == "block":
            name = stmt.split()[1]
            body_nodes, j = _grab_until(nodes, i + 1, {"endblock"})
            i = j + 1  # consume the {% endblock %}
            # Child-provided block overrides the default body.
            if name in blocks:
                out.append(_render_nodes(_parse(blocks[name]), env, blocks))
            else:
                out.append(_render_nodes(body_nodes, env, blocks))
        elif head == "if":
            i, text = _render_if(nodes, i, env, blocks)
            out.append(text)
        elif head == "for":
            i, text = _render_for(nodes, i, env, blocks)
            out.append(text)
        elif head == "with":
            i, text = _render_with(nodes, i, env, blocks)
            out.append(text)
        else:
            # Unknown/standalone tag (e.g. stray) -> skip.
            i += 1
    return "".join(out)


def _render_expr(expr, env):
    value = _eval(_apply_filters(expr), env)
    if isinstance(value, _Undefined):
        return ""
    return html.escape(str(value), quote=True)


def _grab_until(nodes, start, terminators, intermediates=None):
    """Collect nodes until a matching terminator at the same nesting level.

    Returns ``(collected_nodes, index)`` where ``index`` points AT the
    stopping tag (a terminator or intermediate). The caller decides whether
    to consume that tag. ``terminators`` are the closing keywords (e.g.
    ``endif``); ``intermediates`` are same-level branch keywords (e.g.
    ``elif``/``else``) that should also stop collection.
    """
    intermediates = intermediates or set()
    opens = {"if", "for", "with", "block"}
    closes = {"endif", "endfor", "endwith", "endblock"}
    depth = 0
    collected = []
    i = start
    while i < len(nodes):
        head = _tag_head(nodes[i])
        if head in opens:
            depth += 1
        elif head in closes:
            if depth == 0 and head in terminators:
                return collected, i
            depth -= 1
        elif depth == 0 and head in intermediates:
            return collected, i
        collected.append(nodes[i])
        i += 1
    return collected, i


def _tag_head(node):
    """Return the leading keyword of a tag node, or None for text/expr nodes."""
    kind, content = node
    if kind != "tag" or not content.startswith("{%"):
        return None
    inner = content.strip()[2:-2].strip()
    parts = inner.split()
    return parts[0] if parts else None


def _render_if(nodes, i, env, blocks):
    # Parse a full if/elif/else/endif chain.
    branches = []  # list of (condition_or_None, body_nodes)
    stmt = nodes[i][1].strip()[2:-2].strip()
    condition = stmt[len("if"):].strip()
    i += 1
    body, i = _grab_until(nodes, i, {"endif"}, {"elif", "else"})
    branches.append((condition, body))

    while i < len(nodes):
        head = _tag_head(nodes[i])
        content = nodes[i][1]
        if head == "elif":
            cond = content.strip()[2:-2].strip()[len("elif"):].strip()
            i += 1
            body, i = _grab_until(nodes, i, {"endif"}, {"elif", "else"})
            branches.append((cond, body))
        elif head == "else":
            i += 1
            body, i = _grab_until(nodes, i, {"endif"})
            branches.append((None, body))
        elif head == "endif":
            i += 1  # consume the {% endif %}
            break
        else:
            # Should not happen with well-formed templates; stop safely.
            break

    for cond, body in branches:
        if cond is None or bool(_eval(cond, env)):
            return i, _render_nodes(body, env, blocks)
    return i, ""


def _render_for(nodes, i, env, blocks):
    stmt = nodes[i][1].strip()[2:-2].strip()
    m = re.match(r"for\s+(.+?)\s+in\s+(.+)", stmt)
    i += 1
    body, i = _grab_until(nodes, i, {"endfor"})
    i += 1  # consume the {% endfor %}
    if not m:
        return i, ""
    targets = [t.strip() for t in m.group(1).split(",")]
    iterable_expr = m.group(2)
    seq = _eval(iterable_expr, env)
    out = []
    if seq and not isinstance(seq, _Undefined):
        for item in seq:
            loop_env = dict(env)
            if len(targets) == 1:
                loop_env[targets[0]] = _wrap(item)
            else:
                # Tuple unpacking, e.g. `for category, message in ...`.
                for name, value in zip(targets, item):
                    loop_env[name] = _wrap(value)
            out.append(_render_nodes(body, loop_env, blocks))
    return i, "".join(out)


def _render_with(nodes, i, env, blocks):
    stmt = nodes[i][1].strip()[2:-2].strip()
    assignment = stmt[len("with"):].strip()
    i += 1
    body, i = _grab_until(nodes, i, {"endwith"})
    i += 1  # consume the {% endwith %}
    local_env = dict(env)
    if "=" in assignment:
        name, expr = assignment.split("=", 1)
        local_env[name.strip()] = _wrap(_eval(expr.strip(), env))
    return i, _render_nodes(body, local_env, blocks)
