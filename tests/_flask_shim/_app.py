"""Core of the minimal Flask-compatible shim (sandbox test fallback).

See ``tests/_flask_shim/__init__.py`` for why this exists. Only the Flask
surface used by this project is implemented, with behaviour chosen to match
real Flask for the cases the app relies on.
"""

import json
import re
import threading
from urllib.parse import parse_qs, urlencode

from ._templating import render_template_string


# --------------------------------------------------------------------------
# Context-local state (one per thread/request)
# --------------------------------------------------------------------------

class _G:
    """Stand-in for Flask's ``g`` object (attribute bag)."""

    def __contains__(self, key):
        return key in self.__dict__

    def pop(self, key, default=None):
        return self.__dict__.pop(key, default)


class _Local(threading.local):
    def __init__(self):
        self.app = None
        self.request = None
        self.g = _G()
        self.flashes = []


_ctx = _Local()


class _CurrentAppProxy:
    def __getattr__(self, item):
        if _ctx.app is None:
            raise RuntimeError("Working outside of application context.")
        return getattr(_ctx.app, item)


class _GProxy:
    def __getattr__(self, item):
        return getattr(_ctx.g, item)

    def __setattr__(self, key, value):
        setattr(_ctx.g, key, value)

    def __contains__(self, key):
        return key in _ctx.g

    def pop(self, key, default=None):
        return _ctx.g.pop(key, default)


current_app = _CurrentAppProxy()
g = _GProxy()


# --------------------------------------------------------------------------
# Request / Response
# --------------------------------------------------------------------------

class _MultiDict(dict):
    """Minimal form/args object supporting .get and .to_dict()."""

    def to_dict(self):
        return dict(self)


class Request:
    def __init__(self, method, path, query_string="", form=None, json_body=None):
        self.method = method
        self.path = path
        self._args = _MultiDict(_parse_qs_flat(query_string))
        self.form = _MultiDict(form or {})
        self._json = json_body

    @property
    def args(self):
        return self._args

    def get_json(self, silent=False):
        return self._json


class _RequestProxy:
    def __getattr__(self, item):
        if _ctx.request is None:
            raise RuntimeError("Working outside of request context.")
        return getattr(_ctx.request, item)


request = _RequestProxy()


class Response:
    def __init__(self, body="", status=200, headers=None, mimetype="text/html"):
        if isinstance(body, bytes):
            self.data = body
        else:
            self.data = body.encode("utf-8")
        self.status_code = status
        self.headers = headers or {}
        self.headers.setdefault("Content-Type", mimetype)

    def get_json(self):
        return json.loads(self.data.decode("utf-8"))


def jsonify(obj):
    return Response(json.dumps(obj), mimetype="application/json")


def redirect(location, code=302):
    return Response("", status=code, headers={"Location": location})


# --------------------------------------------------------------------------
# Flashes / url_for / render_template
# --------------------------------------------------------------------------

def flash(message, category="message"):
    _ctx.flashes.append((category, message))


def get_flashed_messages(with_categories=False):
    msgs = list(_ctx.flashes)
    _ctx.flashes.clear()
    if with_categories:
        return msgs
    return [m for _, m in msgs]


def url_for(endpoint, **values):
    app = _ctx.app
    rule = app.url_map_by_endpoint.get(endpoint)
    if rule is None and endpoint == "static":
        filename = values.get("filename", "")
        return f"/static/{filename}"
    if rule is None:
        raise RuntimeError(f"No endpoint named {endpoint!r}")
    path = rule.path
    for key, val in values.items():
        path = path.replace(f"<int:{key}>", str(val)).replace(f"<{key}>", str(val))
    return path


def render_template(template_name, **context):
    app = _ctx.app
    return render_template_string(app, template_name, context)


def _install_filters(env_globals):
    """Reserved hook for template filters (none needed currently)."""
    return env_globals


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

class _Rule:
    def __init__(self, path, endpoint, view, methods):
        self.path = path
        self.endpoint = endpoint
        self.view = view
        self.methods = set(methods)
        # Build a regex for matching, capturing <int:x> and <x> params.
        pattern = re.escape(path)
        pattern = pattern.replace(r"\<int:", "<int:").replace(r"\<", "<").replace(r"\>", ">")
        self.converters = {}

        def repl(match):
            conv, name = match.group(1), match.group(2)
            self.converters[name] = conv
            if conv == "int":
                return rf"(?P<{name}>\d+)"
            return rf"(?P<{name}>[^/]+)"

        regex = re.sub(r"<(?:(int):)?(\w+)>", repl, pattern)
        self.regex = re.compile(f"^{regex}$")

    def match(self, path):
        m = self.regex.match(path)
        if not m:
            return None
        params = {}
        for name, value in m.groupdict().items():
            if self.converters.get(name) == "int":
                params[name] = int(value)
            else:
                params[name] = value
        return params


class Blueprint:
    def __init__(self, name, import_name):
        self.name = name
        self.import_name = import_name
        self.deferred = []

    def route(self, path, methods=None):
        methods = methods or ["GET"]

        def decorator(func):
            self.deferred.append((path, func.__name__, func, methods))
            return func

        return decorator


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------

class _Config(dict):
    def from_mapping(self, *args, **kwargs):
        for arg in args:
            self.update(arg)
        self.update(kwargs)


class _CLI:
    def add_command(self, cmd):
        pass  # CLI commands are not exercised by the shim.


class _AppContext:
    def __init__(self, app):
        self.app = app

    def __enter__(self):
        self._prev_app = _ctx.app
        self._prev_g = _ctx.g
        _ctx.app = self.app
        _ctx.g = _G()
        return self

    def __exit__(self, *exc):
        for func in self.app.teardown_funcs:
            func(exc[1] if exc else None)
        _ctx.app = self._prev_app
        _ctx.g = self._prev_g


class _TestClient:
    def __init__(self, app):
        self.app = app

    def get(self, path, follow_redirects=False):
        return self._request("GET", path, follow_redirects=follow_redirects)

    def post(self, path, data=None, json=None, follow_redirects=False):
        return self._request("POST", path, data=data, json=json, follow_redirects=follow_redirects)

    def put(self, path, data=None, json=None, follow_redirects=False):
        return self._request("PUT", path, data=data, json=json, follow_redirects=follow_redirects)

    def delete(self, path, follow_redirects=False):
        return self._request("DELETE", path, follow_redirects=follow_redirects)

    def _request(self, method, path, data=None, json=None, follow_redirects=False):
        resp = self.app.dispatch(method, path, form=data, json_body=json)
        if follow_redirects and resp.status_code in (301, 302, 303):
            location = resp.headers.get("Location")
            resp = self.app.dispatch("GET", location)
        return resp


class Flask:
    def __init__(self, import_name, instance_relative_config=False):
        import os

        self.import_name = import_name
        self.config = _Config()
        self.rules = []
        self.url_map_by_endpoint = {}
        self.teardown_funcs = []
        self.cli = _CLI()
        # Resolve package root (the `app` package directory).
        module = __import__(import_name)
        self.root_path = os.path.dirname(os.path.abspath(module.__file__))
        self.template_folder = os.path.join(self.root_path, "templates")
        self.instance_path = os.path.join(os.path.dirname(self.root_path), "instance")

    # -- config / lifecycle ------------------------------------------------
    def teardown_appcontext(self, func):
        self.teardown_funcs.append(func)
        return func

    def app_context(self):
        return _AppContext(self)

    def open_resource(self, relative, mode="rb"):
        import os

        path = os.path.normpath(os.path.join(self.root_path, relative))
        return open(path, mode)

    # -- routing -----------------------------------------------------------
    def register_blueprint(self, bp):
        for path, name, view, methods in bp.deferred:
            endpoint = f"{bp.name}.{name}"
            rule = _Rule(path, endpoint, view, methods)
            self.rules.append(rule)
            self.url_map_by_endpoint[endpoint] = rule

    def test_client(self):
        return _TestClient(self)

    # -- dispatch ----------------------------------------------------------
    def dispatch(self, method, full_path, form=None, json_body=None):
        if "?" in full_path:
            path, query_string = full_path.split("?", 1)
        else:
            path, query_string = full_path, ""

        ctx = _AppContext(self)
        with ctx:
            _ctx.request = Request(method, path, query_string, form=form, json_body=json_body)
            try:
                matched_path = False
                for rule in self.rules:
                    params = rule.match(path)
                    if params is None:
                        continue
                    matched_path = True
                    if method not in rule.methods:
                        continue
                    result = rule.view(**params)
                    return self._make_response(result)
                if matched_path:
                    return Response("Method Not Allowed", status=405)
                return Response("Not Found", status=404)
            finally:
                _ctx.request = None

    def _make_response(self, result):
        # View may return: Response, str, (body, status), or (body, status, headers)
        if isinstance(result, Response):
            return result
        if isinstance(result, tuple):
            body = result[0]
            status = result[1] if len(result) > 1 else 200
            if isinstance(body, Response):
                body.status_code = status
                return body
            return Response(body, status=status)
        if isinstance(result, str):
            return Response(result)
        return Response(str(result))


def _parse_qs_flat(query_string):
    parsed = parse_qs(query_string, keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}
