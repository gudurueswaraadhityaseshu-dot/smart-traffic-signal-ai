"""Look and feel for the dashboard: CSS, banners and the drawn intersection."""

import streamlit as st

from config import settings

LIGHT_COLOURS = {"GREEN": "#16a34a", "YELLOW": "#ca8a04", "RED": "#dc2626"}
CAR_COLOURS = ["#ef4444", "#3b82f6", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899"]
MAX_CARS_SHOWN = 5   # More vehicles than this are shown as "+N".

CSS = """<style>
.stApp {background: #f4f7fb; color: #0f172a !important;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stSidebar"] {background: #e0e9ff;}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {color: #0f172a !important;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {color: #475569 !important;}
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero {background: linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #db2777 100%); border-radius: 20px; padding: 28px 32px; margin-bottom: 20px; box-shadow: 0 10px 28px rgba(79,70,229,0.35);}
.hero-title {color: #ffffff; font-size: 2.5rem; font-weight: 800; line-height: 1.15;}
.hero-sub {color: #e0e7ff; font-size: 1.15rem; margin-top: 6px;}
[data-testid="stMetric"] {background: #ffffff; border: 1px solid #dbe3f0; border-top: 5px solid #2563eb; border-radius: 14px; padding: 14px 18px; box-shadow: 0 4px 14px rgba(15,23,42,0.10);}
[data-testid="stMetric"] * {color: #0f172a !important;}
[data-testid="stMetricLabel"] * {color: #475569 !important; font-size: 1.05rem !important; font-weight: 700 !important;}
[data-testid="stMetricValue"] * {color: #1d4ed8 !important; font-size: 2.3rem !important; font-weight: 800 !important;}
.banner {border-radius: 14px; padding: 16px 22px; margin: 10px 0; font-weight: 700; font-size: 1.15rem; border-left: 8px solid; box-shadow: 0 3px 10px rgba(15,23,42,0.08);}
.banner.green {background: #bbf7d0; color: #14532d; border-color: #16a34a;}
.banner.yellow {background: #fef08a; color: #713f12; border-color: #ca8a04;}
.banner.red {background: #fecaca; color: #7f1d1d; border-color: #dc2626;}
.banner.blue {background: #bfdbfe; color: #1e3a8a; border-color: #2563eb;}
.junction {position: relative; width: 100%; max-width: 680px; height: 560px; margin: 14px auto; background: linear-gradient(160deg, #bbf7d0 0%, #86efac 100%); border-radius: 22px; overflow: hidden; border: 4px solid #ffffff; box-shadow: 0 8px 26px rgba(15,23,42,0.25);}
.road-v {position: absolute; left: 38%; width: 24%; top: 0; height: 100%; background: #1f2937; border-left: 4px solid #ffffff; border-right: 4px solid #ffffff; box-sizing: border-box;}
.road-h {position: absolute; top: 36%; height: 28%; left: 0; width: 100%; background: #1f2937; border-top: 4px solid #ffffff; border-bottom: 4px solid #ffffff; box-sizing: border-box;}
.line-v {position: absolute; left: 50%; top: 0; height: 100%; border-left: 4px dashed #fde047;}
.line-h {position: absolute; top: 50%; left: 0; width: 100%; border-top: 4px dashed #fde047;}
.centre {position: absolute; left: 38%; top: 36%; width: 24%; height: 28%; background: #1f2937; display: flex; align-items: center; justify-content: center; font-size: 3.6rem; z-index: 3;}
.queue {position: absolute; display: flex; gap: 3px; align-items: center; overflow: hidden; z-index: 2;}
.q-n {left: 40%; width: 10%; top: 1%; bottom: 64%; flex-direction: column-reverse;}
.q-s {left: 50%; width: 10%; top: 64%; bottom: 1%; flex-direction: column;}
.q-e {left: 62%; right: 2%; top: 52%; height: 12%; flex-direction: row;}
.q-w {left: 2%; right: 62%; top: 38%; height: 12%; flex-direction: row-reverse;}
.car {position: relative; border-radius: 7px; flex: none; box-shadow: 0 2px 5px rgba(0,0,0,0.55); border: 2px solid rgba(255,255,255,0.85); box-sizing: border-box;}
.car::after {content: ""; position: absolute; background: rgba(224,242,254,0.9); border-radius: 3px;}
.q-n .car, .q-s .car {width: 22px; height: 34px;}
.q-e .car, .q-w .car {width: 34px; height: 22px;}
.q-n .car::after, .q-s .car::after {left: 3px; right: 3px; top: 7px; height: 8px;}
.q-e .car::after, .q-w .car::after {top: 3px; bottom: 3px; left: 7px; width: 8px;}
.more {flex: none; font-size: 14px; font-weight: 800; color: #ffffff; background: #0f172a; border-radius: 10px; padding: 2px 8px;}
.sig {position: absolute; z-index: 4; background: #0f172a; border-radius: 12px; padding: 5px; display: flex; flex-direction: column; gap: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.45); border: 2px solid #475569;}
.lamp {display: block; width: 22px; height: 22px; border-radius: 50%;}
.lamp.r {background: #4c1d1d;}
.lamp.y {background: #4a3b0c;}
.lamp.g {background: #14391f;}
.lamp.r.on {background: #ef4444; box-shadow: 0 0 16px 5px rgba(239,68,68,0.85);}
.lamp.y.on {background: #facc15; box-shadow: 0 0 16px 5px rgba(250,204,21,0.85);}
.lamp.g.on {background: #22c55e; box-shadow: 0 0 16px 5px rgba(34,197,94,0.85);}
.sig-n {left: 63.5%; top: 18%;}
.sig-s {right: 63.5%; top: 66%;}
.sig-e {left: 63.5%; top: 66%;}
.sig-w {right: 63.5%; top: 18%;}
.pill {position: absolute; z-index: 5; width: 170px; background: #ffffff; border-radius: 14px; padding: 8px 12px; font-size: 16px; line-height: 1.3; color: #0f172a; box-shadow: 0 4px 14px rgba(15,23,42,0.28); border: 3px solid #cbd5e1; box-sizing: border-box;}
.pill b {font-size: 18px;}
.pill .st {font-weight: 800;}
.pill small {display: block; color: #334155; font-size: 14px;}
.pill .timer {font-size: 24px; font-weight: 800; color: #1d4ed8;}
.pill .amb {font-size: 15px; font-weight: 800; color: #b91c1c;}
.pill.alert {border-color: #dc2626; animation: pulse 1s infinite;}
.dot {display: inline-block; width: 18px; height: 18px; border-radius: 50%; margin-right: 6px; vertical-align: middle;}
.p-n {left: 64%; top: 2%;}
.p-s {right: 64%; bottom: 2%;}
.p-e {right: 2%; top: 70%;}
.p-w {left: 2%; top: 17%;}
.amb-icon {position: absolute; z-index: 6; font-size: 46px; line-height: 1; animation: bounce 0.6s infinite alternate;}
.amb-n {left: 52%; top: 10%;}
.amb-s {left: 40%; bottom: 10%;}
.amb-e {right: 10%; top: 40%;}
.amb-w {left: 10%; top: 53%;}
@keyframes pulse {0% {box-shadow: 0 0 0 0 rgba(220,38,38,0.8);} 100% {box-shadow: 0 0 0 14px rgba(220,38,38,0);}}
@keyframes bounce {from {transform: translateY(0);} to {transform: translateY(-7px);}}
.side-title {font-size: 0.72rem; font-weight: 800; letter-spacing: 0.09em; text-transform: uppercase; color: #1d4ed8; margin: 18px 0 2px; padding-top: 10px; border-top: 1px solid #c7d2fe;}
[data-testid="stSidebarNavLink"] {border-radius: 10px; margin: 2px 6px; font-weight: 600;}
[data-testid="stSidebarNavLink"][aria-current="page"] {background: #2563eb;}
[data-testid="stSidebarNavLink"][aria-current="page"] * {color: #ffffff !important;}

</style>"""


def apply_style() -> None:
    """Call once near the top of every page."""
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    """Big gradient header at the top of a page."""
    st.markdown(
        f"<div class='hero'><div class='hero-title'>{title}</div>"
        f"<div class='hero-sub'>{subtitle}</div></div>",
        unsafe_allow_html=True,
    )


def banner(kind: str, text: str) -> None:
    """Coloured status bar. kind is 'green', 'yellow', 'red' or 'blue'."""
    st.markdown(f"<div class='banner {kind}'>{text}</div>", unsafe_allow_html=True)


def _cars_html(count: int) -> str:
    shown = min(count, MAX_CARS_SHOWN)
    parts = []
    for index in range(shown):
        colour = CAR_COLOURS[index % len(CAR_COLOURS)]
        parts.append(f"<div class='car' style='background:{colour}'></div>")
    if count > shown:
        parts.append(f"<div class='more'>+{count - shown}</div>")
    return "".join(parts)


def _signal_html(road: str, state: str) -> str:
    """A traffic-light box with three lamps. The active lamp glows."""
    lamps = ""
    for letter, name in (("r", "RED"), ("y", "YELLOW"), ("g", "GREEN")):
        on = " on" if state == name else ""
        lamps += f"<i class='lamp {letter}{on}'></i>"
    return f"<div class='sig sig-{road[0].lower()}'>{lamps}</div>"


def intersection_html(simulation) -> str:
    """Draw the four-road junction with queues, signal lights and ambulance alerts.

    The HTML is built without line breaks or indentation on purpose, so
    Streamlit's markdown does not mistake it for a code block.
    """
    layout = {
        "North": ("q-n", "p-n"),
        "South": ("q-s", "p-s"),
        "East": ("q-e", "p-e"),
        "West": ("q-w", "p-w"),
    }
    states = simulation.signal_states()
    parts = [
        "<div class='junction'>",
        "<div class='road-v'></div>",
        "<div class='road-h'></div>",
        "<div class='line-v'></div>",
        "<div class='line-h'></div>",
        "<div class='centre'>🚦</div>",
    ]

    for road in settings.ROADS:
        queue_class, _ = layout[road]
        count = simulation.queue_length(road)
        parts.append(f"<div class='queue {queue_class}'>{_cars_html(count)}</div>")
        parts.append(_signal_html(road, states[road]))

    for road in settings.ROADS:
        _, pill_class = layout[road]
        state = states[road]
        colour = LIGHT_COLOURS[state]
        count = simulation.queue_length(road)
        timer = "" if state == "RED" else f"<div class='timer'>⏱ {simulation.seconds_left()} s</div>"
        ambulance = simulation.ambulance_on_road(road)
        alert_class = " alert" if ambulance else ""
        ambulance_line = "<div class='amb'>🚑 AMBULANCE!</div>" if ambulance else ""
        if ambulance:
            parts.append(f"<div class='amb-icon amb-{road[0].lower()}'>🚑</div>")
        parts.append(
            f"<div class='pill {pill_class}{alert_class}'>"
            f"<span class='dot' style='background:{colour}'></span>"
            f"<b>{road}</b> <span class='st' style='color:{colour}'>{state}</span>"
            f"<small>{count} waiting</small>{timer}{ambulance_line}"
            "</div>"
        )

    parts.append("</div>")
    return "".join(parts)