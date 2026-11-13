"""Lecture mentor UI. Upload and status in the sidebar, chat in the main area.

Talks to the backend over HTTP only, so it never needs database credentials.
"""

import os
from datetime import date

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:5000")
TIMEOUT = 30

SOURCE_TYPES = [
    "slides",
    "lecture_transcript",
    "exercise_sheet",
    "textbook",
    "lecture_notes",
    "paper",
    "article",
    "other",
]

SEASONS = ["winter", "summer"]
ROLES = ["primary", "supplementary"]

# Percent and label per pipeline phase. Even quarters: the bar reports the
# phase, not elapsed time
PROGRESS = {
    "pending": (0, "Queued"),
    "extracting": (25, "Extracting ..."),
    "chunking": (50, "Chunking ..."),
    "embedding": (75, "Embedding ..."),
    "done": (100, "Finished"),
}

UNASSIGNED = "__unassigned__"

st.set_page_config(page_title="Lecture mentor", page_icon="🎓", layout="wide")


def enum_label(value: str) -> str:
    """Display text for an enum value: `lecture_transcript` to `Lecture transcript`."""
    return value.replace("_", " ").capitalize()


def api(method: str, path: str, **kwargs) -> requests.Response:
    """Call the backend, raising nothing so the caller can read the status."""
    return requests.request(method, f"{BACKEND_URL}{path}", timeout=TIMEOUT, **kwargs)


def get_list(path: str) -> list[dict]:
    """GET a collection. Empty list on any failure, with the reason shown."""
    try:
        response = api("GET", path)
    except requests.RequestException as exc:
        st.sidebar.error(f"Backend unreachable: {exc}")
        return []
    if response.status_code != 200:
        st.sidebar.error(f"GET {path} returned {response.status_code}")
        return []
    return response.json()


def detail_of(response: requests.Response) -> str:
    """The `detail` field of an error body, or the raw text when there is none."""
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text


# --------------------------------------------------------------------------
# Reference data, read once per run and reused by every section below
# --------------------------------------------------------------------------

universities = get_list("/universities")
courses = get_list("/courses")
editions = get_list("/editions")
documents = get_list("/documents")

university_names = {u["id"]: u["name"] for u in universities}
course_names = {c["id"]: c["name"] for c in courses}


def edition_label(edition: dict) -> str:
    """`Datenbanksysteme, winter 2025`, falling back to the id if orphaned."""
    course = course_names.get(edition["course_id"], "Unknown course")
    return f"{course}, {edition['season']} {edition['year']}"


edition_labels = {e["id"]: edition_label(e) for e in editions}

# Editions grouped by course, so the pickers can cascade: course, then edition
editions_of: dict[str, dict[str, str]] = {course_id: {} for course_id in course_names}
for e in editions:
    editions_of.setdefault(e["course_id"], {})[e["id"]] = (
        f"{e['season']} {e['year']}" + (f", {e['lecturer']}" if e["lecturer"] else "")
    )

# Which document sits in which edition. One request per edition, which is fine
# at this scale and would need a backend filter once it is not
assignment: dict[str, dict] = {}
for edition in editions:
    for link in get_list(f"/editions/{edition['id']}/documents"):
        assignment[link["document_id"]] = {**link, "edition_id": edition["id"]}

# --------------------------------------------------------------------------
# Sidebar, part one: upload
# --------------------------------------------------------------------------

st.sidebar.header("Upload")

uploaded = st.sidebar.file_uploader("Lecture material", type=["pdf", "md", "txt"])
title = st.sidebar.text_input(
    "Title", value=uploaded.name.rsplit(".", 1)[0] if uploaded else ""
)
source_type = st.sidebar.selectbox(
    "Type", SOURCE_TYPES, index=0, format_func=enum_label
)

upload_course = st.sidebar.selectbox(
    "Course",
    [UNASSIGNED, *course_names],
    format_func=lambda i: "Unassigned" if i == UNASSIGNED else course_names[i],
    help="Leave on Unassigned for material that belongs to no lecture",
)

upload_edition, upload_role, upload_week = None, ROLES[0], None
if upload_course != UNASSIGNED:
    choices = editions_of.get(upload_course, {})
    if not choices:
        st.sidebar.warning("That course has no edition yet. Create one further down.")
    else:
        upload_edition = st.sidebar.selectbox(
            "Edition", list(choices), format_func=lambda i: choices[i]
        )
        upload_role = st.sidebar.selectbox("Role", ROLES, format_func=enum_label)
        upload_week = st.sidebar.number_input(
            "Week",
            min_value=1,
            max_value=52,
            value=None,
            step=1,
            placeholder="optional",
        )

if st.sidebar.button("Upload", disabled=uploaded is None, width="stretch"):
    form: dict[str, str | int] = {
        "title": title or uploaded.name,
        "source_type": source_type,
    }
    if upload_edition is not None:
        form["edition_id"] = upload_edition
        form["role"] = upload_role
        if upload_week is not None:
            form["week"] = int(upload_week)

    response = api(
        "POST",
        "/documents/upload",
        files={
            "file": (
                uploaded.name,
                uploaded.getvalue(),
                uploaded.type or "application/octet-stream",
            )
        },
        data=form,
    )
    if response.status_code == 201:
        st.session_state["watch_id"] = response.json()["id"]
        st.rerun()
    else:
        st.sidebar.error(f"{response.status_code}: {detail_of(response)}")

# --------------------------------------------------------------------------
# Sidebar, part two: creating a university, a course and an edition
# --------------------------------------------------------------------------

st.sidebar.divider()

with st.sidebar.expander("Courses and editions"):
    st.caption("A course belongs to a university, an edition belongs to a course.")

    with st.form("new_university", clear_on_submit=True):
        university_name = st.text_input("University name")
        if st.form_submit_button("Create university", width="stretch"):
            response = api("POST", "/universities", json={"name": university_name})
            if response.status_code == 201:
                st.rerun()
            else:
                st.error(f"{response.status_code}: {detail_of(response)}")

    with st.form("new_course", clear_on_submit=True):
        course_name = st.text_input("Course name")
        course_code = st.text_input("Code", placeholder="optional")
        course_university = st.selectbox(
            "University",
            list(university_names),
            format_func=lambda i: university_names[i],
            disabled=not university_names,
        )
        if st.form_submit_button(
            "Create course", width="stretch", disabled=not university_names
        ):
            response = api(
                "POST",
                "/courses",
                json={
                    "name": course_name,
                    "code": course_code or None,
                    "university_id": course_university,
                },
            )
            if response.status_code == 201:
                st.rerun()
            else:
                st.error(f"{response.status_code}: {detail_of(response)}")

    with st.form("new_edition", clear_on_submit=True):
        edition_course = st.selectbox(
            "Course",
            list(course_names),
            format_func=lambda i: course_names[i],
            disabled=not course_names,
        )
        edition_year = st.number_input(
            "Year", min_value=1900, max_value=2100, value=date.today().year, step=1
        )
        edition_season = st.selectbox("Season", SEASONS, format_func=enum_label)
        edition_lecturer = st.text_input("Lecturer", placeholder="optional")
        if st.form_submit_button(
            "Create edition", width="stretch", disabled=not course_names
        ):
            response = api(
                "POST",
                f"/courses/{edition_course}/editions",
                json={
                    "year": int(edition_year),
                    "season": edition_season,
                    "lecturer": edition_lecturer or None,
                },
            )
            if response.status_code == 201:
                st.rerun()
            else:
                st.error(f"{response.status_code}: {detail_of(response)}")

# --------------------------------------------------------------------------
# Sidebar, part three: status of one document
# --------------------------------------------------------------------------

st.sidebar.divider()
st.sidebar.header("Status")

if not documents:
    st.sidebar.caption("No documents yet.")
else:
    labels = {d["id"]: f"{d['title']} [{d['status']}]" for d in documents}
    ids = list(labels)

    # The widget owns `watch_id` through its key, so the selection survives a
    # rerun. Passing `index` instead would change the widget's identity every
    # time the selection changes, and Streamlit would discard the new pick
    if st.session_state.get("watch_id") not in ids:
        st.session_state["watch_id"] = ids[0]
    st.sidebar.selectbox(
        "Document",
        ids,
        key="watch_id",
        format_func=lambda i: labels[i],
    )
    selected_id = st.session_state["watch_id"]

    if st.sidebar.button("Ingest", width="stretch"):
        response = api("POST", f"/documents/{selected_id}/ingest")
        if response.status_code == 202:
            st.sidebar.info("Ingestion started")
        else:
            st.sidebar.warning(f"{response.status_code}: {detail_of(response)}")

    with st.sidebar.popover("Delete"):
        st.caption("Removes the row, its chunks and the uploaded file.")
        if st.button("Yes, delete", type="primary"):
            response = api("DELETE", f"/documents/{selected_id}")
            if response.status_code == 204:
                # No need to clear `watch_id`: on the rerun the id is gone from
                # the list, and the guard above falls back to the first entry
                st.rerun()
            else:
                st.error(f"{response.status_code}: {detail_of(response)}")

    # ---- assignment of the selected document -----------------------------

    current = assignment.get(selected_id)
    with st.sidebar.expander(
        "Assigned to "
        + (
            edition_labels.get(current["edition_id"], "an edition")
            if current
            else "nothing"
        )
    ):
        if not edition_labels:
            st.caption("No editions exist yet. Create one further down.")
        else:
            course_ids = [c for c in course_names if editions_of.get(c)]
            assigned_course = (
                next(
                    (
                        e["course_id"]
                        for e in editions
                        if e["id"] == current["edition_id"]
                    ),
                    None,
                )
                if current
                else None
            )
            course_choice = st.selectbox(
                "Course",
                course_ids,
                index=(
                    course_ids.index(assigned_course)
                    if assigned_course in course_ids
                    else 0
                ),
                format_func=lambda i: course_names[i],
                key="assign_course",
            )
            choices = editions_of[course_choice]
            target = st.selectbox(
                "Edition",
                list(choices),
                index=(
                    list(choices).index(current["edition_id"])
                    if current and current["edition_id"] in choices
                    else 0
                ),
                format_func=lambda i: choices[i],
                key="assign_edition",
            )
            role = st.selectbox(
                "Role",
                ROLES,
                index=ROLES.index(current["role"]) if current else 0,
                format_func=enum_label,
                key="assign_role",
            )
            week = st.number_input(
                "Week",
                min_value=1,
                max_value=52,
                value=current["week"] if current else None,
                step=1,
                placeholder="optional",
                key="assign_week",
            )

            left, right = st.columns(2)
            if left.button("Assign", width="stretch"):
                body = {"role": role, "week": int(week) if week else None}
                response = api(
                    "PUT",
                    f"/editions/{target}/documents/{selected_id}",
                    json=body,
                )
                if response.status_code in (200, 201):
                    st.rerun()
                else:
                    st.error(f"{response.status_code}: {detail_of(response)}")

            if right.button("Detach", width="stretch", disabled=current is None):
                response = api(
                    "DELETE",
                    f"/editions/{current['edition_id']}/documents/{selected_id}",
                )
                if response.status_code == 204:
                    st.rerun()
                else:
                    st.error(f"{response.status_code}: {detail_of(response)}")

    @st.fragment(run_every=2)
    def status_panel() -> None:
        """Poll the status endpoint without rerunning the rest of the page."""
        document_id = st.session_state.get("watch_id")
        if document_id is None:
            return
        try:
            response = api("GET", f"/documents/{document_id}/status")
        except requests.RequestException:
            st.caption("Backend unreachable")
            return
        if response.status_code != 200:
            st.caption(f"status returned {response.status_code}")
            return

        state = response.json()
        phase = state["status"]
        left, right = st.columns(2)
        left.metric("Status", phase)
        right.metric("Chunks", state["chunk_count"])

        if phase == "failed":
            st.status("Failed", state="error")
        else:
            percent, text = PROGRESS[phase]
            st.progress(percent, text=text)

        if state["error"]:
            st.error(state["error"])

    with st.sidebar:
        status_panel()

# --------------------------------------------------------------------------
# Main area: chat
# --------------------------------------------------------------------------

st.title("Lecture mentor")

st.session_state.setdefault("messages", [])

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Ask about your lecture material")
if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            response = api("POST", "/chat", json={"question": question})
        except requests.RequestException as exc:
            answer = f"Backend unreachable: {exc}"
        else:
            if response.status_code == 404:
                answer = (
                    "`POST /chat` does not exist yet. Retrieval is the next "
                    "piece of work, and this window goes live the moment the "
                    "endpoint answers."
                )
            elif response.status_code == 200:
                answer = response.json().get("answer", response.text)
            else:
                answer = f"{response.status_code}: {response.text}"
        st.markdown(answer)

    st.session_state["messages"].append({"role": "assistant", "content": answer})
