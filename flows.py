"""Fetch current flows (CFS) from USGS and Colorado DWR, with a small in-memory cache."""
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

import config

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
DWR_STATION_URL = "https://dwr.state.co.us/Rest/GET/api/v2/telemetrystations/telemetrystation/"
DWR_SERIES_URL = "https://dwr.state.co.us/Rest/GET/api/v2/telemetrystations/telemetrytimeseriesraw/"

TZ = ZoneInfo(config.LOCAL_TZ)
_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT
_lock = threading.Lock()
_cache = {}  # name -> (expires_at, value)
_last_good = {}  # name -> value; served if a refresh fails (upstream hiccup)
RETRY_AFTER_ERROR = 60  # seconds before retrying a failed source


def _cached(name, ttl, fn):
    now = time.time()
    with _lock:
        hit = _cache.get(name)
        if hit and hit[0] > now:
            return hit[1]
    try:
        value = fn()
    except Exception:
        try:
            value = fn()  # one quick retry
        except Exception:
            with _lock:
                if name in _last_good:  # keep showing the last good data briefly
                    _cache[name] = (now + RETRY_AFTER_ERROR, _last_good[name])
                    return _last_good[name]
            raise
    with _lock:
        _cache[name] = (now + ttl, value)
        _last_good[name] = value
    return value


def _get_json(url, params):
    r = _session.get(url, params=params, timeout=config.HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _parse_time(s):
    """Parse ISO time; naive DWR series times are local Colorado time."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def _sites(source):
    return [s for s in config.SITES if s["source"] == source]


# ---------- current values: one batched call per source ----------
def _fetch_usgs_current():
    sites = _sites("usgs")
    if not sites:
        return {}
    data = _get_json(USGS_IV_URL, {
        "format": "json",
        "sites": ",".join(s["site_id"] for s in sites),
        "parameterCd": "00060",
        "siteStatus": "all",
    })
    out = {}
    for ts in data.get("value", {}).get("timeSeries", []):
        site_id = ts["sourceInfo"]["siteCode"][0]["value"]
        vals = [v for v in ts["values"][0]["value"] if v["value"] not in (None, "", "-999999")]
        if vals:
            out[site_id] = (float(vals[-1]["value"]), _parse_time(vals[-1]["dateTime"]))
    return out


def _fetch_dwr_current():
    sites = _sites("dwr")
    if not sites:
        return {}
    data = _get_json(DWR_STATION_URL, {
        "format": "json",
        "abbrev": ",".join(s["site_id"] for s in sites),
        "parameter": "DISCHRG",
    })
    out = {}
    for r in data.get("ResultList", []):
        if r.get("measValue") is not None and r.get("measDateTime"):
            out[r["abbrev"]] = (float(r["measValue"]), _parse_time(r["measDateTime"]))
    return out


_FETCHERS = {"usgs": _fetch_usgs_current, "dwr": _fetch_dwr_current}


def _current_by_source():
    results, errors = {}, {}
    for source, fn in _FETCHERS.items():
        try:
            results[source] = _cached(f"current:{source}", config.CACHE_SECONDS, fn)
        except Exception as exc:  # network/parse problems -> show per-site error
            results[source] = {}
            errors[source] = str(exc)
    return results, errors


# ---------- optional 7-day history (hourly points) for the chart ----------
def _fetch_history(site):
    if site["source"] == "usgs":
        data = _get_json(USGS_IV_URL, {"format": "json", "sites": site["site_id"],
                                       "parameterCd": "00060", "period": "P7D"})
        ts = data["value"]["timeSeries"]
        raw = ts[0]["values"][0]["value"] if ts else []
        pts = [(v["dateTime"], v["value"]) for v in raw]
    else:
        start = (datetime.now(TZ) - timedelta(days=7)).strftime("%m/%d/%Y")
        data = _get_json(DWR_SERIES_URL, {"format": "json", "abbrev": site["site_id"],
                                          "parameter": "DISCHRG", "startDate": start,
                                          "pageSize": 5000})
        pts = [(r["measDateTime"], r["measValue"]) for r in data.get("ResultList", [])]
    hourly = {}
    for t, v in pts:
        try:
            dt, val = _parse_time(t), float(v)
        except (TypeError, ValueError):
            continue
        if val < 0:
            continue
        hourly[dt.replace(minute=0, second=0, microsecond=0)] = val  # keep one point/hour
    cutoff = datetime.now(TZ) - timedelta(days=7)
    return [{"t": k.isoformat(), "cfs": round(hourly[k], 1)} for k in sorted(hourly) if k >= cutoff]


def history(site):
    try:
        return _cached(f"hist:{site['key']}", config.HISTORY_CACHE_SECONDS,
                       lambda: _fetch_history(site))
    except Exception:
        return []


# ---------- public ----------
def get_flows():
    by_source, errors = _current_by_source()
    flows = []
    for s in config.SITES:
        item = {k: s[k] for k in ("key", "river", "water", "gauge_name", "source", "site_id", "url")}
        hit = by_source.get(s["source"], {}).get(s["site_id"])
        if hit:
            cfs, dt = hit
            item.update(cfs=cfs, timestamp=dt.isoformat(),
                        timestamp_local=dt.strftime("%b %-d, %Y %-I:%M %p ") + dt.tzname(),
                        error=None)
        else:
            item.update(cfs=None, timestamp=None, timestamp_local=None,
                        error=("Data source unavailable" if s["source"] in errors
                               else "No current data reported for this gauge"))
        if config.SHOW_SPARKLINES:
            item["history_7d"] = history(s)
        flows.append(item)
    return flows
