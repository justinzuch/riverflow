import os
#importing random river to start, instead of defauling to the first river in the list
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request

import config
import flows as flow_data


class PrefixMiddleware:
    """Serve the app under a URL prefix (e.g. /riverflow) when the web server
    passes the full path instead of setting SCRIPT_NAME. Harmless otherwise."""

    def __init__(self, wsgi_app, prefix):
        self.wsgi_app, self.prefix = wsgi_app, prefix.rstrip("/")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if self.prefix and not environ.get("SCRIPT_NAME") and path.startswith(self.prefix):
            environ["SCRIPT_NAME"] = self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
        return self.wsgi_app(environ, start_response)


app = Flask(__name__)
app.wsgi_app = PrefixMiddleware(app.wsgi_app, os.environ.get("RIVERFLOW_URL_PREFIX", ""))

TZ = ZoneInfo(config.LOCAL_TZ)
CHART_W, CHART_H = 600, 180


def _fmt_cfs(v):
    if v is None:
        return "—"
    return f"{v:,.0f}" if v >= 100 else f"{v:g}"


def _axis(v):
    return f"{v:,.0f}" if v >= 10 else f"{v:.1f}"


def _chart(history):
    """Build SVG paths + axis labels for a 7-day chart (pure server-side, no JS needed)."""
    if len(history) < 2:
        return None
    times = [datetime.fromisoformat(p["t"]) for p in history]
    vals = [p["cfs"] for p in history]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or max(hi * 0.1, 1)
    ymin, ymax = max(lo - pad, 0), hi + pad
    t0, t1 = times[0].timestamp(), times[-1].timestamp()
    tspan = (t1 - t0) or 1

    def x(t): return (t.timestamp() - t0) / tspan * CHART_W
    def y(v): return CHART_H - (v - ymin) / (ymax - ymin) * CHART_H

    pts = [(x(t), y(v)) for t, v in zip(times, vals)]
    line = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    area = line + f" L{CHART_W},{CHART_H} L0,{CHART_H} Z"
    # midnight gridlines with weekday labels
    days, seen = [], set()
    for t in times:
        if t.hour == 0 and t.date() not in seen:
            seen.add(t.date())
            days.append({"x": x(t), "pct": x(t) / CHART_W * 100, "label": t.strftime("%a")})
    imin, imax = vals.index(lo), vals.index(hi)
    return {
        "w": CHART_W, "h": CHART_H, "line": line, "area": area, "days": days,
        "min": _fmt_cfs(lo), "max": _fmt_cfs(hi),
        "min_when": times[imin].strftime("%a %-m/%-d %-I %p"), "max_when": times[imax].strftime("%a %-m/%-d %-I %p"),
        "ymin": _axis(ymin), "ymax": _axis(ymax),
        "points": [[round(a, 1), round(b, 1), _fmt_cfs(v), t.strftime("%a %b %-d, %-I %p")]
                   for (a, b), v, t in zip(pts, vals, times)],
    }


@app.route("/")
def index():
    data = flow_data.get_flows()
    keys = [f["key"] for f in data]
    selected = request.args.get("river", "").lower()
    picked_at_random = selected not in keys
    if picked_at_random:
        # No (or unknown) ?river= given: feature a random river on each visit.
        selected = random.choice(keys)
    for f in data:
        f["cfs_display"] = _fmt_cfs(f["cfs"])
        f["chart"] = _chart(f.get("history_7d") or [])
    now = datetime.now(TZ)
    html = render_template("index.html", flows=data, selected=selected,
                           picked_at_random=picked_at_random,
                           generated=now.strftime("%b %-d, %Y %-I:%M %p ") + now.tzname(),
                           cache_minutes=config.CACHE_SECONDS // 60)
    resp = app.make_response(html)
    # Don't let browsers/proxies cache the page, so each visit gets a fresh pick.
    resp.headers["Cache-Control"] = "no-store"
    return resp    


@app.route("/api/flows")
def api_flows():
    return jsonify({
        "generated": datetime.now(TZ).isoformat(),
        "timezone": config.LOCAL_TZ,
        "units": "cfs",
        "flows": flow_data.get_flows(),
    })


if __name__ == "__main__":
    # `python app.py` -> http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
