import streamlit as st
import duckdb
import pandas as pd
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "madang.db"
CSV_CUSTOMER = BASE_DIR / "Customer_madang.csv"
CSV_BOOK = BASE_DIR / "Book_madang.csv"
CSV_ORDERS = BASE_DIR / "Orders_madang.csv"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=str(DB_PATH), read_only=False)
    return conn


def ensure_tables():
    conn = get_conn()
    existing = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}

    if "customer" not in {e.lower() for e in existing} and CSV_CUSTOMER.exists():
        conn.execute(f"CREATE TABLE Customer AS SELECT * FROM '{CSV_CUSTOMER.as_posix()}'")
    if "book" not in {e.lower() for e in existing} and CSV_BOOK.exists():
        conn.execute(f"CREATE TABLE Book AS SELECT * FROM '{CSV_BOOK.as_posix()}'")
    if "orders" not in {e.lower() for e in existing} and CSV_ORDERS.exists():
        conn.execute(f"CREATE TABLE Orders AS SELECT * FROM '{CSV_ORDERS.as_posix()}'")
    conn.close()


def select_query(sql, params=None):
    conn = get_conn()
    if params:
        df = conn.execute(sql, params).df()
    else:
        df = conn.execute(sql).df()
    conn.close()
    return df.to_dict("records")


def execute_query(sql, params=None):
    conn = get_conn()
    if params:
        conn.execute(sql, params)
    else:
        conn.execute(sql)
    conn.close()


ensure_tables()

st.set_page_config(page_title="Madang Manager (DuckDB)", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f7faff; }
    h1 { color: #1E3A8A; font-weight: 700; }
    h2, h3, h4 { color: #2563EB; margin-top: 0.8rem; }
    .stDataFrame {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div[data-testid="stButton"] button {
        background-color: #2563EB; color: white; border-radius: 5px;
        padding: 0.5rem 1rem; border: none;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #1E40AF; color: #f0f0f0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Madang Manager (DuckDB)")

cust_cnt = select_query("SELECT COUNT(*) AS c FROM Customer;")[0]["c"]
book_cnt = select_query("SELECT COUNT(*) AS c FROM Book;")[0]["c"]
order_cnt = select_query("SELECT COUNT(*) AS c FROM Orders;")[0]["c"]

info_col1, info_col2, info_col3 = st.columns(3)
info_col1.metric("고객 수", f"{cust_cnt}명")
info_col2.metric("도서 수", f"{book_cnt}권")
info_col3.metric("주문 수", f"{order_cnt}건")

tab_customer, tab_book, tab_orders, tab_view = st.tabs(
    ["고객", "도서", "주문", "고객별 주문"]
)

with tab_customer:
    st.subheader("고객 목록")
    customers = select_query("SELECT custid, name, address, phone FROM Customer ORDER BY custid;")
    st.dataframe(pd.DataFrame(customers), use_container_width=True, height=280)

    st.markdown("#### 고객 추가")
    col_add1, col_add2, col_add3, col_add4 = st.columns([1.5, 2, 1.5, 0.8])
    with col_add1:
        c_name = st.text_input("이름", key="c_name_new")
    with col_add2:
        c_addr = st.text_input("주소", key="c_addr_new")
    with col_add3:
        c_phone = st.text_input("전화", key="c_phone_new")
    with col_add4:
        add_clicked = st.button("등록", key="c_add_btn")

    if add_clicked:
        row = select_query("SELECT COALESCE(MAX(custid), 0) AS m FROM Customer;")
        new_id = row[0]["m"] + 1
        execute_query(
            "INSERT INTO Customer (custid, name, address, phone) VALUES (?, ?, ?, ?);",
            (new_id, c_name, c_addr, c_phone)
        )
        st.success(f"신규 고객이 추가되었습니다. (ID: {new_id})")
        st.rerun()

    st.markdown("#### 고객 수정 / 삭제")
    cust_ids = [c["custid"] for c in customers]
    selected_id = st.selectbox(
        "고객 선택",
        [None] + cust_ids,
        format_func=lambda x: "선택 안 함" if x is None else f"{x} - " + [c for c in customers if c["custid"] == x][0]["name"],
        key="cust_select_box"
    )

    if selected_id:
        sel = [c for c in customers if c["custid"] == selected_id][0]
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            edit_name = st.text_input("이름", value=sel["name"], key="cust_edit_name")
            edit_phone = st.text_input("전화", value=sel["phone"] or "", key="cust_edit_phone")
        with col_e2:
            edit_addr = st.text_input("주소", value=sel["address"], key="cust_edit_addr")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("저장", use_container_width=True, key="cust_save_btn"):
                execute_query(
                    "UPDATE Customer SET name=?, address=?, phone=? WHERE custid=?;",
                    (edit_name, edit_addr, edit_phone, sel["custid"])
                )
                st.success("고객 정보가 수정되었습니다.")
                st.rerun()
        with col_btn2:
            if st.button("삭제", use_container_width=True, key="cust_del_btn", type="secondary"):
                cnt = select_query(
                    "SELECT COUNT(*) AS c FROM Orders WHERE custid = ?;",
                    (sel["custid"],)
                )[0]["c"]
                if cnt > 0:
                    st.error("이 고객은 주문 내역이 있어서 삭제할 수 없습니다.")
                else:
                    execute_query("DELETE FROM Customer WHERE custid=?;", (sel["custid"],))
                    st.success("고객이 삭제되었습니다.")
                    st.rerun()
    else:
        st.info("수정하거나 삭제할 고객을 선택하세요.")

with tab_book:
    st.subheader("도서 목록")
    books = select_query("SELECT bookid, bookname, publisher, price FROM Book ORDER BY bookid;")
    st.dataframe(pd.DataFrame(books), use_container_width=True, height=280)

    st.markdown("#### 도서 추가")
    bcol1, bcol2, bcol3, bcol4 = st.columns([1.4, 1.4, 1, 0.8])
    with bcol1:
        b_name = st.text_input("도서명", key="b_name_new")
    with bcol2:
        b_pub = st.text_input("출판사", key="b_pub_new")
    with bcol3:
        b_price = st.number_input("가격", min_value=0, value=10000, step=1000, key="b_price_new")
    with bcol4:
        b_add = st.button("등록", key="b_add_btn")

    if b_add:
        row = select_query("SELECT COALESCE(MAX(bookid), 0) AS m FROM Book;")
        new_bid = row[0]["m"] + 1
        execute_query(
            "INSERT INTO Book (bookid, bookname, publisher, price) VALUES (?, ?, ?, ?);",
            (new_bid, b_name, b_pub, b_price)
        )
        st.success(f"새 도서가 추가되었습니다. (ID: {new_bid})")
        st.rerun()

    st.markdown("#### 도서 수정 / 삭제")
    book_ids = [b["bookid"] for b in books]
    selected_bid = st.selectbox(
        "도서 선택",
        [None] + book_ids,
        format_func=lambda x: "선택 안 함" if x is None else f"{x} - " + [b for b in books if b["bookid"] == x][0]["bookname"],
        key="book_select_box"
    )

    if selected_bid:
        sb = [b for b in books if b["bookid"] == selected_bid][0]
        col_be1, col_be2, col_be3 = st.columns([1.4, 1.2, 0.8])
        with col_be1:
            eb_name = st.text_input("도서명", value=sb["bookname"], key="book_edit_name")
        with col_be2:
            eb_pub = st.text_input("출판사", value=sb["publisher"], key="book_edit_pub")
        with col_be3:
            eb_price = st.number_input("가격", min_value=0, value=sb["price"], step=1000, key="book_edit_price")

        col_bbtn1, col_bbtn2 = st.columns(2)
        with col_bbtn1:
            if st.button("저장", use_container_width=True, key="book_save_btn"):
                execute_query(
                    "UPDATE Book SET bookname=?, publisher=?, price=? WHERE bookid=?;",
                    (eb_name, eb_pub, eb_price, sb["bookid"])
                )
                st.success("도서 정보가 수정되었습니다.")
                st.rerun()
        with col_bbtn2:
            if st.button("삭제", use_container_width=True, key="book_del_btn", type="secondary"):
                cnt = select_query(
                    "SELECT COUNT(*) AS c FROM Orders WHERE bookid = ?;",
                    (sb["bookid"],)
                )[0]["c"]
                if cnt > 0:
                    st.error("이 도서는 주문 내역에 사용되어 삭제할 수 없습니다.")
                else:
                    execute_query("DELETE FROM Book WHERE bookid=?;", (sb["bookid"],))
                    st.success("도서가 삭제되었습니다.")
                    st.rerun()
    else:
        st.info("수정하거나 삭제할 도서를 선택하세요.")

with tab_orders:
    st.subheader("주문 목록")
    orders = select_query("""
        SELECT o.orderid, o.custid, c.name AS customer,
               o.bookid, b.bookname, o.saleprice, o.orderdate
        FROM Orders o
        JOIN Customer c ON o.custid = c.custid
        JOIN Book b ON o.bookid = b.bookid
        ORDER BY o.orderid;
    """)
    st.dataframe(pd.DataFrame(orders), use_container_width=True, height=280)

    st.markdown("#### 주문 입력")
    custs = select_query("SELECT custid, name FROM Customer ORDER BY custid;")
    bks = select_query("SELECT bookid, bookname, price FROM Book ORDER BY bookid;")

    ocol1, ocol2, ocol3, ocol4 = st.columns([1.5, 1.5, 1, 1])
    with ocol1:
        sel_cust = st.selectbox("고객", custs, format_func=lambda x: f"{x['custid']} - {x['name']}")
    with ocol2:
        sel_book = st.selectbox("도서", bks, format_func=lambda x: f"{x['bookid']} - {x['bookname']} ({x['price']}원)")
    with ocol3:
        saleprice = st.number_input("판매가", min_value=0, value=sel_book["price"], step=1000, key="sale_price")
    with ocol4:
        orderdate = st.date_input("주문일", value=date.today(), key="order_date")

    if st.button("주문 등록", key="order_add_btn"):
        row = select_query("SELECT COALESCE(MAX(orderid), 0) AS m FROM Orders;")
        new_oid = row[0]["m"] + 1
        execute_query(
            "INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate) VALUES (?, ?, ?, ?, ?);",
            (new_oid, sel_cust["custid"], sel_book["bookid"], saleprice, orderdate)
        )
        st.success(f"주문이 입력되었습니다. (ID: {new_oid})")
        st.rerun()

    st.markdown("#### 주문 삭제")
    order_ids = [o["orderid"] for o in orders]
    if order_ids:
        del_oid = st.selectbox("삭제할 주문", order_ids, key="order_delete_box")
        if st.button("선택 주문 삭제", key="order_del_btn", type="secondary"):
            execute_query("DELETE FROM Orders WHERE orderid=?;", (del_oid,))
            st.success("주문이 삭제되었습니다.")
            st.rerun()
    else:
        st.info("삭제할 주문이 없습니다.")

with tab_view:
    st.subheader("고객명으로 주문 조회")
    name_keyword = st.text_input("고객 이름을 입력하세요", key="search_name")
    if name_keyword:
        rows = select_query("""
            SELECT c.custid, c.name, b.bookname, o.saleprice, o.orderdate
            FROM Customer c
            JOIN Orders o ON c.custid = o.custid
            JOIN Book b ON o.bookid = b.bookid
            WHERE c.name = ?
            ORDER BY o.orderdate;
        """, (name_keyword,))
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("해당 고객의 주문이 없습니다.")
    else:
        st.caption("조회할 고객 이름을 입력하면 주문 내역이 표시됩니다.")

