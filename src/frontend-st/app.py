"""Streamlit test console for the lecture-ai database.

A scratch page for running SQL against the dev database and inspecting
the schema. Not part of the product.
"""

import os

import pandas as pd
import psycopg
import streamlit as st
from psycopg import sql

DATABASE_URL = os.environ["DATABASE_URL"]
CACHE_TTL = 30  # seconds; short enough to notice schema and data changes

TABLE_LIST_SQL = """
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
"""

# format_type gives the real Postgres type, so vector(1024) and the enums
# show up properly instead of information_schema's "USER-DEFINED".
COLUMN_SQL = """
SELECT a.attname                                      AS column,
       format_type(a.atttypid, a.atttypmod)           AS type,
       NOT a.attnotnull                               AS nullable,
       pg_get_expr(d.adbin, d.adrelid)                AS default,
       a.attgenerated <> ''                           AS generated
FROM pg_attribute a
LEFT JOIN pg_attrdef d
       ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE a.attrelid = %s::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum
"""


def connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


@st.cache_data(ttl=CACHE_TTL)
def list_tables() -> list[str]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(TABLE_LIST_SQL)
        return [row[0] for row in cur.fetchall()]


@st.cache_data(ttl=CACHE_TTL)
def table_definition(table: str) -> pd.DataFrame:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(COLUMN_SQL, (table,))
        cols = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    # the tsv default is a whole CASE expression; left whole it squeezes
    # every other column flat. Full text is still in the cell tooltip.
    df["default"] = df["default"].apply(
        lambda v: v[:27] + "…" if isinstance(v, str) and len(v) > 28 else v
    )
    return df


@st.cache_data(ttl=CACHE_TTL)
def row_count(table: str) -> int:
    stmt = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
    with connect() as conn, conn.cursor() as cur:
        cur.execute(stmt)
        return cur.fetchone()[0]


def for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Text-ify values Arrow cannot represent.

    st.dataframe serialises through Arrow, which has no notion of uuid.UUID,
    dicts from JSONB or the float lists pgvector returns. Left alone they are
    rendered as decomposed structs instead of readable values.
    """
    keep = (str, int, float, bool)
    for col in df.columns[df.dtypes == "object"]:
        df[col] = df[col].map(
            lambda v: v if v is None or isinstance(v, keep) else str(v)
        )
    return df


def unique_columns(cols: list[str]) -> list[str]:
    """Number repeated labels.

    A join happily returns two columns called "id", but pandas and Arrow
    both refuse a frame with duplicate labels.
    """
    seen: dict[str, int] = {}
    out: list[str] = []
    for col in cols:
        seen[col] = seen.get(col, 0) + 1
        out.append(col if seen[col] == 1 else f"{col}__{seen[col]}")
    return out


def run_query(query: str) -> tuple[pd.DataFrame | None, str]:
    """Run a statement. Returns (rows, status). rows is None when it returned none."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query)  # noqa: S608 - arbitrary SQL is the point of this page
        if cur.description is None:
            conn.commit()
            return None, f"{cur.rowcount} row(s) affected"
        cols = unique_columns([c.name for c in cur.description])
        rows = cur.fetchall()
        df = for_display(pd.DataFrame(rows, columns=cols))
        return df, f"{len(rows)} row(s)"


st.set_page_config(
    page_title="lecture-ai SQL console",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.session_state.setdefault("result", None)
st.session_state.setdefault("status", "")
st.session_state.setdefault("error", "")

st.session_state.setdefault("show_schema", True)

header, toggle = st.columns([5, 1])
header.title("SQL console")
toggle.write("")  # nudge the toggle down to baseline
st.session_state.show_schema = toggle.toggle(
    "Schema panel", value=st.session_state.show_schema
)

# Streamlit's own sidebar is left-only, so the schema panel is a right column.
if st.session_state.show_schema:
    main, schema = st.columns([1, 1], gap="large")
else:
    main = st.container()
    schema = None

with main:
    query = st.text_area(
        "Query",
        height=240,
        placeholder="SELECT id, title, status FROM documents LIMIT 20;",
        label_visibility="collapsed",
    )
    run, clear, _ = st.columns([1, 1, 4])
    if run.button("Run", type="primary", width="stretch"):
        if query.strip():
            try:
                st.session_state.result, st.session_state.status = run_query(query)
                st.session_state.error = ""
            except Exception as exc:  # noqa: BLE001 - show the driver error verbatim
                st.session_state.result = None
                st.session_state.status = ""
                st.session_state.error = str(exc)
        else:
            st.session_state.error = "Nothing to run."
    if clear.button("Clear", width="stretch"):
        st.session_state.result = None
        st.session_state.status = ""
        st.session_state.error = ""

if schema is not None:
    with schema:
        st.subheader("Tables")
        try:
            tables = list_tables()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
            tables = []
        for table in tables:
            try:
                label = f"{table}  (count: {row_count(table)})"
            except Exception:  # noqa: BLE001 - still list the table if the count fails
                label = table
            with st.expander(label):
                try:
                    st.metric("rows", row_count(table))
                    st.dataframe(
                        table_definition(table),
                        width="stretch",
                        hide_index=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

# Results span the full width, below both panes.
st.divider()
if st.session_state.error:
    st.error(st.session_state.error)
elif st.session_state.status:
    st.caption(st.session_state.status)
    if st.session_state.result is not None:
        st.dataframe(st.session_state.result, width="stretch", hide_index=True)
else:
    st.caption("No results yet.")
