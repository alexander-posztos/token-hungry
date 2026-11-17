#!/usr/bin/env python3
# <xbar.title>Claude Usage</xbar.title>
# <xbar.desc>Claude plan limits (session, weekly, per model) with reset countdowns.</xbar.desc>
# <xbar.author.github>alexander-posztos</xbar.author.github>
# <xbar.abouturl>https://github.com/alexander-posztos/token-hungry</xbar.abouturl>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>

# Reads Claude Code's login from the Keychain and asks the endpoint behind
# its /usage command. Banked resets only come back for Claude Code's user agent.

import base64
import contextlib
import io
import json
import subprocess
import urllib.request
from datetime import datetime, timezone

import minecraft

URL = "https://api.anthropic.com/api/oauth/usage?cedar_ember=1"
VERSION = "2.1.323"  # Claude Code version to claim when the claude command is missing
COLORS = ((90, "#ef4444"), (75, "#f97316"), (50, "#eab308"), (0, "#22c55e"))
ICON = base64.b64encode((minecraft.HERE / "icons" / "claude.tiff").read_bytes()).decode()  # the menu bar logo


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


# Claude Code's user agent with the installed version, since Anthropic stops
# returning banked resets to versions that have grown old.
def user_agent():
    try:
        version = subprocess.check_output(["claude", "--version"], text=True).split()[0]
    except Exception:
        version = VERSION
    return f"claude-cli/{version} (external, cli)"


def main():
    command = ["security", "find-generic-password", "-ws", "Claude Code-credentials"]
    token = json.loads(subprocess.check_output(command))["claudeAiOauth"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}", "User-Agent": user_agent()}
    request = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        usage = json.load(response)

    now = datetime.now(timezone.utc)
    rows = []
    for limit in usage["limits"]:
        kind, reset = limit["kind"], limit["resets_at"]
        model = ((limit["scope"] or {}).get("model") or {}).get("display_name")
        label = {"session": "Session", "weekly_all": "Weekly"}.get(kind, model)
        secs = reset and int((day(reset) - now).total_seconds())
        rows.append((label or kind, round(limit["percent"]), secs))
    render(rows)
    grants = (usage.get("cedar_ember") or {}).get("grants") or []
    render_resets((grant["type"], grant["starts_at"], grant["ends_at"])
                  for grant in grants for _ in range(grant["resets_left"]))
    print("---")
    print("Usage settings | href=https://claude.ai/settings/usage")
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
print(minecraft.menu("Claude", output.getvalue()), end="")
