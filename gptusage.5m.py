#!/usr/bin/env python3
# <xbar.title>ChatGPT Usage</xbar.title>
# <xbar.desc>ChatGPT/Codex plan limits (session, weekly) with reset countdowns.</xbar.desc>
# <xbar.author.github>alexander-posztos</xbar.author.github>
# <xbar.abouturl>https://github.com/alexander-posztos/token-hungry</xbar.abouturl>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>

# Reads the Codex login from ~/.codex/auth.json and asks the endpoint behind
# its /status command.

import base64
import contextlib
import io
import json
import os
import urllib.request
from datetime import datetime, timezone

import minecraft

URL = "https://chatgpt.com/backend-api/wham/"
COLORS = ((90, "#ef4444"), (75, "#f97316"), (50, "#eab308"), (0, "#22c55e"))
ICON = base64.b64encode((minecraft.HERE / "icons" / "chatgpt.tiff").read_bytes()).decode()  # the menu bar logo


def countdown(secs):
    d, h, m = secs // 86400, secs % 86400 // 3600, secs % 3600 // 60
    return f"{d}d {h}h" if d else f"{h}h {m}m" if h else f"{m}m"


# Prints the menu from rows of (label, percent used, seconds until reset).
# A row without a running window has no seconds.
def render(rows):
    title = " · ".join(f"{label[0]} {pct}%" for label, pct, _ in rows)
    print(f"{title} | templateImage={ICON}")
    print("---")
    for label, pct, secs in rows:
        filled = min(10, round(pct / 10))
        bar = "█" * filled + "░" * (10 - filled)
        color = next(c for threshold, c in COLORS if pct >= threshold)
        reset = f"   resets in {countdown(secs)}" if secs else ""
        print(f"{label:<8}{bar} {pct:>3}%{reset} | font=Menlo size=13 color={color}")


# Prints the banked resets from (name, usable from, expires) as ISO dates,
# either of which can be missing. Resets of one kind share a line.
def render_resets(resets):
    groups = {}
    for name, start, end in resets:
        line = f"{name.title()} reset"
        if start and day(start) > datetime.now(timezone.utc):
            line += f" from {day(start):%-d %b}"
        groups.setdefault(line, []).append(f"{day(end):%-d %b}" if end else "")
    if groups:
        print("---")
    for line, ends in groups.items():
        until = " · ".join(dict.fromkeys(filter(None, ends)))
        if until:
            line += f" until {until}"
        print(f"{len(ends)}× {line} | font=Menlo size=13")


def day(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()


def get(path):
    with open(os.path.expanduser("~/.codex/auth.json")) as f:
        token = json.load(f)["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    request = urllib.request.Request(URL + path, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    usage = get("usage")
    limit = usage["rate_limit"]
    rows = []
    for window in filter(None, (limit["primary_window"], limit["secondary_window"])):
        label = "Weekly" if window["limit_window_seconds"] > 86400 else "Session"
        pct, secs = round(window["used_percent"]), window["reset_after_seconds"]
        rows.append((label, pct, secs))
    render(rows)
    if usage["rate_limit_reset_credits"]["available_count"]:
        credits = get("rate-limit-reset-credits")["credits"]
        render_resets((credit["title"].split()[0], None, credit["expires_at"])
                      for credit in credits if credit["status"] == "available")
    print("---")
    print("Refresh | refresh=true")


# The menu is printed into a buffer, so minecraft.py can add its switches and
# redraw it in Minecraft mode.
with contextlib.redirect_stdout(io.StringIO()) as output:
    try:
        main()
    except Exception as error:
        print(f"⚠︎ | templateImage={ICON}")
        print("---")
        print(error)
        print("Refresh | refresh=true")
print(minecraft.menu("ChatGPT", output.getvalue()), end="")
