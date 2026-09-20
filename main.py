import sqlite3
import traceback
import uuid
from pathlib import Path

import flet as ft
import jdatetime


APP_NAME = "سفارشات انصاری"


def today_shamsi() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")


def parse_number(value):
    if value is None:
        return None
    cleaned = str(value).replace(",", "").replace("،", "").replace(" ", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def fmt_money(value) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{int(round(float(value))):,} تومان"
    except (TypeError, ValueError):
        return "—"


def app_data_dir() -> Path:
    # Android/desktop writable storage.
    try:
        from flet import app_storage_path
        path = app_storage_path()
        if path:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            return p
    except Exception:
        pass

    p = Path(__file__).resolve().parent / ".data"
    p.mkdir(parents=True, exist_ok=True)
    return p


DB_PATH = app_data_dir() / "ansari_orders.db"


class Database:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def init_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            visitor TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            item TEXT NOT NULL,
            buy_price REAL,
            sell_price REAL,
            margin REAL,
            settlement INTEGER,
            qty REAL NOT NULL,
            date TEXT NOT NULL,
            desc TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_orders_company
        ON orders(company_id);
        """)
        self.conn.commit()

    def companies(self):
        return self.conn.execute(
            "SELECT * FROM companies ORDER BY name"
        ).fetchall()

    def add_company(self, name, visitor, phone):
        cid = str(uuid.uuid4())
        now = today_shamsi()
        self.conn.execute(
            """INSERT INTO companies
               (id,name,visitor,phone,created_at)
               VALUES(?,?,?,?,?)""",
            (cid, name, visitor, phone, now),
        )
        self.conn.commit()
        return cid

    def delete_company(self, cid):
        self.conn.execute("DELETE FROM companies WHERE id=?", (cid,))
        self.conn.commit()

    def orders(self, company_id):
        return self.conn.execute(
            """SELECT * FROM orders
               WHERE company_id=?
               ORDER BY date DESC, rowid DESC""",
            (company_id,),
        ).fetchall()

    def get_order(self, oid):
        return self.conn.execute(
            "SELECT * FROM orders WHERE id=?", (oid,)
        ).fetchone()

    def save_order(self, record):
        now = today_shamsi()
        exists = self.conn.execute(
            "SELECT id FROM orders WHERE id=?", (record["id"],)
        ).fetchone()

        if exists:
            self.conn.execute(
                """UPDATE orders SET
                   company_id=?, item=?, buy_price=?, sell_price=?,
                   margin=?, settlement=?, qty=?, date=?, desc=?,
                   updated_at=?
                   WHERE id=?""",
                (
                    record["company_id"], record["item"],
                    record["buy_price"], record["sell_price"],
                    record["margin"], record["settlement"],
                    record["qty"], record["date"], record["desc"],
                    now, record["id"],
                ),
            )
        else:
            self.conn.execute(
                """INSERT INTO orders
                   (id,company_id,item,buy_price,sell_price,margin,
                    settlement,qty,date,desc,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record["id"], record["company_id"], record["item"],
                    record["buy_price"], record["sell_price"],
                    record["margin"], record["settlement"], record["qty"],
                    record["date"], record["desc"], now, now,
                ),
            )
        self.conn.commit()

    def delete_order(self, oid):
        self.conn.execute("DELETE FROM orders WHERE id=?", (oid,))
        self.conn.commit()

    def close(self):
        self.conn.close()


def main(page: ft.Page):
    C = getattr(ft, "Colors", getattr(ft, "colors", None))
    I = getattr(ft, "Icons", getattr(ft, "icons", None))

    db = Database(DB_PATH)

    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = C.BLUE_GREY_50
    page.rtl = True
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO
    page.theme = ft.Theme(
        text_theme=ft.TextTheme(body_medium=ft.TextStyle(size=16)),
        color_scheme_seed=C.TEAL,
    )

    page.appbar = ft.AppBar(
        leading=ft.Icon(I.SHOPPING_CART_CHECKOUT, color="white"),
        title=ft.Text(
            "هایپر گوشت انصاری",
            color="white",
            weight=ft.FontWeight.BOLD,
            size=22,
        ),
        bgcolor=C.TEAL_700,
        center_title=True,
        elevation=4,
    )

    snack_text = ft.Text("", size=15, color="white")
    snack_bar = ft.SnackBar(
        content=snack_text,
        behavior=ft.SnackBarBehavior.FLOATING,
        duration=3500,
    )
    page.overlay.append(snack_bar)

    def show_message(message, is_error=True):
        snack_text.value = message
        snack_bar.bgcolor = C.RED_600 if is_error else C.GREEN_600
        snack_bar.open = True
        page.update()

    FIELD_STYLE = {
        "border_radius": 10,
        "filled": True,
        "fill_color": C.WHITE,
        "text_size": 17,
        "border_color": C.TEAL_200,
        "focused_border_color": C.TEAL_600,
    }

    companies = list(db.companies())

    company_dropdown = ft.Dropdown(
        label="انتخاب شرکت",
        options=[],
        width=260,
        border_radius=10,
        filled=True,
        fill_color=C.WHITE,
        text_size=17,
    )

    def reload_companies():
        nonlocal companies
        companies = list(db.companies())
        company_dropdown.options = [
            ft.dropdown.Option(key=c["id"], text=c["name"])
            for c in companies
        ]
        if companies:
            if not company_dropdown.value or not any(
                c["id"] == company_dropdown.value for c in companies
            ):
                company_dropdown.value = companies[0]["id"]
        else:
            company_dropdown.value = None

    reload_companies()

    txt_item_name = ft.TextField(label="نام کالا", **FIELD_STYLE)
    txt_buy_price = ft.TextField(
        label="قیمت خرید (تومان)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **FIELD_STYLE,
    )
    txt_sell_price = ft.TextField(
        label="قیمت مصرف (تومان)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **FIELD_STYLE,
    )
    txt_margin = ft.TextField(
        label="حاشیه سود (%)", read_only=True, **FIELD_STYLE
    )
    txt_settlement = ft.TextField(
        label="مدت تسویه (روز)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **FIELD_STYLE,
    )
    txt_qty = ft.TextField(
        label="تعداد سفارش (کارتن)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **FIELD_STYLE,
    )
    txt_date = ft.TextField(
        label="تاریخ تحویل", value=today_shamsi(), **FIELD_STYLE
    )
    txt_desc = ft.TextField(
        label="توضیحات",
        multiline=True,
        min_lines=2,
        max_lines=4,
        **FIELD_STYLE,
    )

    def update_margin(_=None):
        buy = parse_number(txt_buy_price.value)
        sell = parse_number(txt_sell_price.value)
        if buy is not None and buy > 0 and sell is not None:
            txt_margin.value = f"{((sell - buy) / buy) * 100:.1f}"
        else:
            txt_margin.value = ""
        try:
            txt_margin.update()
        except Exception:
            pass

    def format_price_field(e):
        ctrl = e.control
        raw = (ctrl.value or "").replace(",", "").replace("،", "").strip()
        if raw.isdigit():
            ctrl.value = f"{int(raw):,}"
            ctrl.update()
        update_margin()

    txt_buy_price.on_change = format_price_field
    txt_sell_price.on_change = format_price_field

    txt_item_name.on_submit = lambda e: txt_buy_price.focus()
    txt_buy_price.on_submit = lambda e: txt_sell_price.focus()
    txt_sell_price.on_submit = lambda e: txt_settlement.focus()
    txt_settlement.on_submit = lambda e: txt_qty.focus()
    txt_qty.on_submit = lambda e: txt_date.focus()
    txt_date.on_submit = lambda e: txt_desc.focus()

    txt_comp_name = ft.TextField(label="نام شرکت", **FIELD_STYLE)
    txt_visitor = ft.TextField(label="نام ویزیتور", **FIELD_STYLE)
    txt_phone = ft.TextField(
        label="شماره تلفن",
        keyboard_type=ft.KeyboardType.PHONE,
        **FIELD_STYLE,
    )

    orders_list = ft.Column(spacing=12, tight=True)

    summary_count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
    summary_qty = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
    summary_buy = ft.Text("—", size=13, weight=ft.FontWeight.BOLD)
    summary_sell = ft.Text("—", size=13, weight=ft.FontWeight.BOLD)

    def _stat(label, value_ctrl, icon, color):
        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=C.WHITE,
            expand=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, color=color, size=18),
                            ft.Text(label, size=13, color=C.GREY_700),
                        ],
                        spacing=5,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [value_ctrl],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
        )

    summary_row = ft.Row(
        [
            _stat("سفارش", summary_count, I.LIST_ALT, C.TEAL_600),
            _stat("کارتن", summary_qty, I.INVENTORY_2, C.ORANGE_600),
            _stat("خرید", summary_buy, I.PAYMENT, C.BLUE_600),
            _stat("فروش", summary_sell, I.ATTACH_MONEY, C.GREEN_600),
        ],
        spacing=8,
    )

    def refresh_summary():
        cid = company_dropdown.value
        count = 0
        total_qty = total_buy = total_sell = 0.0

        if cid:
            for o in db.orders(cid):
                count += 1
                q = float(o["qty"] or 0)
                bp = float(o["buy_price"] or 0)
                sp = float(o["sell_price"] or 0)
                total_qty += q
                total_buy += bp * q
                total_sell += sp * q

        summary_count.value = str(count)
        summary_qty.value = f"{int(total_qty):,}" if total_qty else "0"
        summary_buy.value = fmt_money(total_buy) if total_buy else "—"
        summary_sell.value = fmt_money(total_sell) if total_sell else "—"

    editing_id = {"value": None}

    def clear_item_fields():
        txt_item_name.value = ""
        txt_buy_price.value = ""
        txt_sell_price.value = ""
        txt_margin.value = ""
        txt_settlement.value = ""
        txt_qty.value = ""
        txt_date.value = today_shamsi()
        txt_desc.value = ""
        editing_id["value"] = None
        item_dialog.title.value = "ثبت کالای جدید"

    def refresh_orders_list(_=None):
        orders_list.controls.clear()
        cid = company_dropdown.value

        if not cid:
            orders_list.controls.append(
                ft.Container(
                    padding=30,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            ft.Icon(
                                I.BUSINESS_OUTLINED,
                                size=60,
                                color=C.GREY_400,
                            ),
                            ft.Text(
                                "برای مشاهده سفارشات، یک شرکت انتخاب کنید.",
                                color=C.GREY_600,
                                size=15,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                )
            )
            refresh_summary()
            page.update()
            return

        filtered = list(db.orders(cid))

        if not filtered:
            orders_list.controls.append(
                ft.Container(
                    padding=30,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            ft.Icon(
                                I.INBOX_OUTLINED,
                                size=60,
                                color=C.GREY_400,
                            ),
                            ft.Text(
                                "هنوز سفارشی برای این شرکت ثبت نشده است.",
                                color=C.GREY_600,
                                size=15,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                )
            )
        else:
            for order in filtered:
                parts = [f"تاریخ: {order['date']}"]
                if order["buy_price"] is not None:
                    parts.append(f"خرید: {fmt_money(order['buy_price'])}")
                if order["sell_price"] is not None:
                    parts.append(f"فروش: {fmt_money(order['sell_price'])}")
                if order["margin"] is not None:
                    parts.append(f"سود: {float(order['margin']):.1f}٪")
                if order["settlement"] is not None:
                    parts.append(f"تسویه: {order['settlement']} روز")

                subtitle = "  |  ".join(parts)
                if order["desc"]:
                    subtitle += f"\n📝 {order['desc']}"

                orders_list.controls.append(
                    ft.Card(
                        elevation=2,
                        content=ft.Container(
                            padding=12,
                            content=ft.ListTile(
                                leading=ft.Icon(
                                    I.LOCAL_SHIPPING,
                                    color=C.TEAL_500,
                                    size=32,
                                ),
                                title=ft.Text(
                                    f"{order['item']} — {order['qty']} کارتن",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                subtitle=ft.Text(
                                    subtitle,
                                    size=14,
                                    color=C.GREY_700,
                                ),
                                trailing=ft.Row(
                                    [
                                        ft.IconButton(
                                            I.EDIT_OUTLINED,
                                            tooltip="ویرایش",
                                            icon_color=C.TEAL_700,
                                            on_click=lambda e, oid=order["id"]:
                                                open_edit_item(oid),
                                        ),
                                        ft.IconButton(
                                            I.DELETE_OUTLINE,
                                            tooltip="حذف",
                                            icon_color=C.RED_500,
                                            on_click=lambda e, oid=order["id"]:
                                                ask_delete_order(oid),
                                        ),
                                    ],
                                    tight=True,
                                    spacing=0,
                                ),
                            ),
                        ),
                    )
                )

        refresh_summary()
        page.update()

    company_dropdown.on_change = refresh_orders_list

    def close_item_dlg(e=None):
        item_dialog.open = False
        page.update()

    def save_item(e):
        try:
            cid = company_dropdown.value
            if not cid:
                show_message("ابتدا یک شرکت انتخاب کنید!")
                return

            name = (txt_item_name.value or "").strip()
            if not name:
                show_message("نام کالا الزامی است!")
                return

            qty = parse_number(txt_qty.value)
            if qty is None or qty <= 0:
                show_message("تعداد سفارش باید عددی مثبت باشد!")
                return

            settlement_raw = (txt_settlement.value or "").strip()
            settlement = None
            if settlement_raw:
                settlement = parse_number(settlement_raw)
                if settlement is None or settlement < 0:
                    show_message("مدت تسویه باید عددی معتبر باشد!")
                    return
                settlement = int(settlement)

            bp = parse_number(txt_buy_price.value)
            sp = parse_number(txt_sell_price.value)

            margin = None
            if bp is not None and bp > 0 and sp is not None:
                margin = round(((sp - bp) / bp) * 100, 2)

            record = {
                "id": editing_id["value"] or str(uuid.uuid4()),
                "company_id": cid,
                "item": name,
                "buy_price": bp,
                "sell_price": sp,
                "margin": margin,
                "settlement": settlement,
                "qty": qty,
                "date": (txt_date.value or "").strip() or today_shamsi(),
                "desc": (txt_desc.value or "").strip(),
            }

            db.save_order(record)
            clear_item_fields()
            close_item_dlg()
            refresh_orders_list()
            show_message("سفارش با موفقیت ذخیره شد.", is_error=False)

        except Exception:
            show_message(f"خطا: {traceback.format_exc()[-300:]}")

    item_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            "ثبت کالای جدید",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=C.TEAL_800,
        ),
        content=ft.Column(
            [
                txt_item_name,
                txt_buy_price,
                txt_sell_price,
                txt_margin,
                txt_settlement,
                txt_qty,
                txt_date,
                txt_desc,
            ],
            scroll=ft.ScrollMode.AUTO,
            height=450,
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.ElevatedButton(
                "ثبت کالا",
                on_click=save_item,
                bgcolor=C.GREEN_600,
                color="white",
            ),
            ft.TextButton("انصراف", on_click=close_item_dlg),
        ],
    )
    page.overlay.append(item_dialog)

    def open_add_item(e):
        if not company_dropdown.value:
            show_message("ابتدا یک شرکت انتخاب کنید!")
            return
        clear_item_fields()
        item_dialog.open = True
        page.update()
        txt_item_name.focus()

    def open_edit_item(order_id):
        order = db.get_order(order_id)
        if not order:
            show_message("سفارش پیدا نشد!")
            return

        editing_id["value"] = order["id"]
        item_dialog.title.value = "ویرایش کالا"
        txt_item_name.value = order["item"]
        txt_buy_price.value = (
            f"{int(order['buy_price']):,}"
            if order["buy_price"] is not None else ""
        )
        txt_sell_price.value = (
            f"{int(order['sell_price']):,}"
            if order["sell_price"] is not None else ""
        )
        txt_margin.value = (
            f"{float(order['margin']):.1f}"
            if order["margin"] is not None else ""
        )
        txt_settlement.value = (
            str(order["settlement"])
            if order["settlement"] is not None else ""
        )
        txt_qty.value = str(order["qty"])
        txt_date.value = order["date"] or today_shamsi()
        txt_desc.value = order["desc"] or ""
        item_dialog.open = True
        page.update()

    confirm_dialog = ft.AlertDialog(modal=True)
    page.overlay.append(confirm_dialog)

    def close_confirm():
        confirm_dialog.open = False
        page.update()

    def ask_delete_order(order_id):
        def do_delete(e):
            try:
                db.delete_order(order_id)
                close_confirm()
                refresh_orders_list()
                show_message("سفارش حذف شد.", is_error=False)
            except Exception:
                show_message(f"خطا: {traceback.format_exc()[-300:]}")

        confirm_dialog.title = ft.Text("حذف سفارش")
        confirm_dialog.content = ft.Text("آیا از حذف این سفارش مطمئن هستید؟")
        confirm_dialog.actions = [
            ft.TextButton(
                "حذف",
                on_click=do_delete,
                style=ft.ButtonStyle(color=C.RED_600),
            ),
            ft.TextButton("انصراف", on_click=lambda e: close_confirm()),
        ]
        confirm_dialog.open = True
        page.update()

    def clear_comp_fields():
        txt_comp_name.value = ""
        txt_visitor.value = ""
        txt_phone.value = ""

    def close_comp_dlg(e=None):
        comp_dialog.open = False
        page.update()

    def save_company(e):
        try:
            name = (txt_comp_name.value or "").strip()
            visitor = (txt_visitor.value or "").strip()
            phone = (txt_phone.value or "").strip()

            if not name:
                show_message("نام شرکت الزامی است!")
                return

            if any(c["name"] == name for c in companies):
                show_message("این شرکت قبلاً ثبت شده است!")
                return

            cid = db.add_company(name, visitor, phone)
            clear_comp_fields()
            close_comp_dlg()
            reload_companies()
            company_dropdown.value = cid
            refresh_orders_list()
            show_message("شرکت با موفقیت ثبت شد.", is_error=False)

        except sqlite3.IntegrityError:
            show_message("این شرکت قبلاً ثبت شده است!")
        except Exception:
            show_message(f"خطا: {traceback.format_exc()[-300:]}")

    comp_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            "افزودن شرکت تأمین‌کننده",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=C.TEAL_800,
        ),
        content=ft.Column(
            [txt_comp_name, txt_visitor, txt_phone],
            tight=True,
            spacing=10,
            height=230,
        ),
        actions=[
            ft.ElevatedButton(
                "ثبت شرکت",
                on_click=save_company,
                bgcolor=C.TEAL_600,
                color="white",
            ),
            ft.TextButton("انصراف", on_click=close_comp_dlg),
        ],
    )
    page.overlay.append(comp_dialog)

    def open_add_company(e):
        clear_comp_fields()
        comp_dialog.open = True
        page.update()
        txt_comp_name.focus()

    def delete_company(e):
        cid = company_dropdown.value
        if not cid:
            show_message("ابتدا یک شرکت انتخاب کنید!")
            return

        company = next((c for c in companies if c["id"] == cid), None)
        if not company:
            return

        def do_delete(e):
            try:
                db.delete_company(cid)
                close_confirm()
                reload_companies()
                refresh_orders_list()
                show_message(
                    "شرکت و سفارشات آن حذف شد.",
                    is_error=False,
                )
            except Exception:
                show_message(f"خطا: {traceback.format_exc()[-300:]}")

        confirm_dialog.title = ft.Text("حذف شرکت")
        confirm_dialog.content = ft.Text(
            f"شرکت «{company['name']}» و تمام سفارش‌های آن حذف شود؟"
        )
        confirm_dialog.actions = [
            ft.TextButton(
                "حذف",
                on_click=do_delete,
                style=ft.ButtonStyle(color=C.RED_600),
            ),
            ft.TextButton("انصراف", on_click=lambda e: close_confirm()),
        ]
        confirm_dialog.open = True
        page.update()

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        company_dropdown,
                        ft.ElevatedButton(
                            "افزودن شرکت",
                            icon=I.ADD_BUSINESS,
                            on_click=open_add_company,
                            bgcolor=C.TEAL_600,
                            color="white",
                        ),
                        ft.OutlinedButton(
                            "حذف شرکت",
                            icon=I.DELETE_OUTLINE,
                            on_click=delete_company,
                            style=ft.ButtonStyle(color=C.RED_600),
                        ),
                    ],
                    wrap=True,
                    spacing=8,
                ),
                ft.Divider(height=8),
                summary_row,
                ft.Container(height=5),
                ft.ElevatedButton(
                    "ثبت سفارش جدید",
                    icon=I.ADD_SHOPPING_CART,
                    on_click=open_add_item,
                    bgcolor=C.GREEN_600,
                    color="white",
                ),
                ft.Text(
                    "فهرست سفارشات",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=C.TEAL_800,
                ),
                orders_list,
            ],
            spacing=12,
        )
    )

    refresh_orders_list()


if __name__ == "__main__":
    ft.app(target=main)
