import hmac
import json
import os
import re
import time

import streamlit as st
import streamlit.components.v1 as components

from places import PLACES as BASE_PLACES, NC
from mapview import build_map_html
from ai import clean_text, secret, ask_ai, plan_trip

st.set_page_config(page_title="WonderMap AI - Andaman", page_icon="🌴", layout="wide")

DATA_DIR = "data"
PENDING_FILE = os.path.join(DATA_DIR, "pending_gems.json")
APPROVED_FILE = os.path.join(DATA_DIR, "approved_gems.json")
EXTRA_FILE = "extra_places.json"
MAX_PENDING = 50


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def normalize(p, source):
    try:
        lat = float(p["lat"])
        lng = float(p["lng"])
    except Exception:
        return None
    if not (6.0 <= lat <= 14.5 and 92.0 <= lng <= 94.5):
        return None
    pid = clean_text(p.get("id"), 80)
    name = clean_text(p.get("name"), 60)
    if not pid or len(name) < 2:
        return None
    return {
        "id": pid, "name": name,
        "category": clean_text(p.get("category"), 40) or "Hidden Gems",
        "emoji": clean_text(p.get("emoji"), 8) or "📍",
        "lat": lat, "lng": lng,
        "area": clean_text(p.get("area"), 60) or "Andaman",
        "info": clean_text(p.get("info"), 400),
        "hours": clean_text(p.get("hours"), 100) or NC,
        "fee": clean_text(p.get("fee"), 100) or NC,
        "best_time": clean_text(p.get("best_time"), 100) or NC,
        "tips": clean_text(p.get("tips"), 200) or NC,
        "source": source,
    }


def load_places():
    places, ids, names = [], set(), set()

    def add(raw, source):
        p = normalize(raw, source)
        if not p or p["id"] in ids:
            return
        if source == "osm" and p["name"].lower() in names:
            return
        ids.add(p["id"])
        names.add(p["name"].lower())
        places.append(p)

    for raw in BASE_PLACES:
        add(raw, "official")
    for raw in read_json(EXTRA_FILE, []):
        src = raw.get("source") if raw.get("source") in ("osm", "community") else "osm"
        add(raw, src)
    for raw in read_json(APPROVED_FILE, []):
        add(raw, "community")
    return places


def owner_unlocked(pin):
    secret_pin = secret("OWNER_PIN")
    if not secret_pin:
        return False, "The owner PIN is not set in Secrets."
    now = time.time()
    if now < st.session_state.get("pin_locked_until", 0):
        return False, "Too many wrong tries. Please wait a minute."
    if hmac.compare_digest(pin.encode("utf-8"), secret_pin.encode("utf-8")):
        st.session_state["pin_fails"] = 0
        return True, ""
    fails = st.session_state.get("pin_fails", 0) + 1
    st.session_state["pin_fails"] = fails
    if fails >= 5:
        st.session_state["pin_locked_until"] = now + 60
        st.session_state["pin_fails"] = 0
    return False, "Wrong PIN."


places = load_places()
by_id = {p["id"]: p for p in places}

for key, default in (("messages", []), ("focus", ""), ("plan", ""), ("last_q", 0.0), ("gem_count", 0)):
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🌴 WonderMap AI - Andaman")
st.caption("Explore the Andaman Islands. Details can change, so please confirm hours, prices, ferries and permits locally. "
           "Your questions are sent to Google's Gemini to get answers.")

# ---------- Owner panel (sidebar) ----------
with st.sidebar:
    st.header("🔑 Owner")
    with st.expander("Review hidden gems"):
        pin = st.text_input("Owner PIN", type="password", key="owner_pin_box")
        if pin:
            ok, msg = owner_unlocked(pin)
            if not ok:
                st.error(msg)
            else:
                pending = read_json(PENDING_FILE, [])
                st.write(len(pending), "waiting for review")
                for g in pending:
                    st.divider()
                    st.write("**" + g["name"] + "** · " + g["area"])
                    st.write(g["info"])
                    if g.get("tips"):
                        st.write("Tips: " + g["tips"])
                    st.write(str(round(g["lat"], 5)) + ", " + str(round(g["lng"], 5)))
                    c1, c2 = st.columns(2)
                    if c1.button("Approve", key="ap_" + g["id"]):
                        approved = read_json(APPROVED_FILE, [])
                        approved.append({"id": g["id"], "name": g["name"], "category": "Hidden Gems",
                                         "emoji": "💎", "lat": g["lat"], "lng": g["lng"], "area": g["area"],
                                         "info": g["info"], "tips": g.get("tips", "")})
                        write_json(APPROVED_FILE, approved)
                        write_json(PENDING_FILE, [x for x in pending if x["id"] != g["id"]])
                        st.rerun()
                    if c2.button("Reject", key="rj_" + g["id"]):
                        write_json(PENDING_FILE, [x for x in pending if x["id"] != g["id"]])
                        st.rerun()
                st.divider()
                st.download_button("Download approved gems (backup)",
                                   data=json.dumps(read_json(APPROVED_FILE, []), ensure_ascii=False, indent=1),
                                   file_name="approved_gems.json", mime="application/json")

tab_map, tab_trip, tab_gem = st.tabs(["🗺️ Map & Chat", "🧳 My Trip", "💎 Add a Hidden Gem"])

# ---------- Map and chat ----------
with tab_map:
    components.html(build_map_html(places, st.session_state.focus), height=560)
    st.subheader("✨ Ask WonderMap AI")
    for m in st.session_state.messages[-12:]:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    question = st.chat_input("Ask anything about the Andamans...")
    if question:
        if time.time() - st.session_state.last_q < 3:
            st.warning("Please wait a few seconds between questions.")
        else:
            st.session_state.last_q = time.time()
            q = clean_text(question, 500)
            history = list(st.session_state.messages)
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("Thinking..."):
                result = ask_ai(q, places, history)
            st.session_state.messages.append({"role": "assistant", "content": result["reply"]})
            if result["placeId"] in by_id:
                st.session_state.focus = result["placeId"]
            st.rerun()

# ---------- Trip planner ----------
with tab_trip:
    st.write("Pick the places you want to visit, and the AI will plan your days.")
    labels = {p["id"]: p["emoji"] + " " + p["name"] + " (" + p["area"] + ")" for p in places}
    chosen_ids = st.multiselect("Places (up to 15)", options=list(labels.keys()),
                                format_func=lambda i: labels[i], max_selections=15)
    days = st.number_input("Number of days", min_value=1, max_value=7, value=2, step=1)
    if st.button("✨ Plan with AI"):
        if not chosen_ids:
            st.warning("Pick at least one place first.")
        else:
            with st.spinner("Planning..."):
                out = plan_trip([by_id[i] for i in chosen_ids], int(days))
            if out["ok"]:
                st.session_state.plan = out["plan"]
            else:
                st.error(out["msg"])
    if st.session_state.plan:
        st.markdown("**Your plan**")
        st.write(st.session_state.plan)
        st.caption("Tap the copy icon on the box below to copy your plan.")
        st.code(st.session_state.plan, language=None)

# ---------- Add a hidden gem ----------
with tab_gem:
    st.write("Know a hidden gem? Tell us. The owner reviews every submission before it appears on the map.")
    st.caption("To get the coordinates, long-press the spot in Google Maps and copy the two numbers shown.")
    with st.form("gem_form", clear_on_submit=True):
        g_name = st.text_input("Place name *", max_chars=60)
        g_area = st.text_input("Area (for example: Havelock Island)", max_chars=60)
        g_desc = st.text_area("Description * (what makes it special?)", max_chars=400)
        g_tips = st.text_area("Tips (optional)", max_chars=200)
        c1, c2 = st.columns(2)
        g_lat = c1.number_input("Latitude *", min_value=6.0, max_value=14.5, value=11.6765, format="%.5f")
        g_lng = c2.number_input("Longitude *", min_value=92.0, max_value=94.5, value=92.7275, format="%.5f")
        sent = st.form_submit_button("Submit for review")
    if sent:
        name = clean_text(g_name, 60)
        desc = clean_text(g_desc, 400)
        pending = read_json(PENDING_FILE, [])
        if len(name) < 2:
            st.error("Please enter a place name.")
        elif len(desc) < 10:
            st.error("Please write a short description (at least 10 letters).")
        elif st.session_state.gem_count >= 3:
            st.error("You have sent enough gems for now. Thank you!")
        elif len(pending) >= MAX_PENDING:
            st.error("Too many gems are waiting for review. Please try again later.")
        else:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "gem"
            pending.append({"id": "gem-" + slug + "-" + str(int(time.time())), "name": name,
                            "area": clean_text(g_area, 60) or "Andaman", "info": desc,
                            "tips": clean_text(g_tips, 200), "lat": float(g_lat), "lng": float(g_lng)})
            if write_json(PENDING_FILE, pending):
                st.session_state.gem_count += 1
                st.success("Thank you! Your hidden gem was sent for review.")
            else:
                st.error("Could not save your gem right now. Please try again later.")
# END OF FILE
