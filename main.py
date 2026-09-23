"""
مدیریت سفارشات فروشگاه انصاری
نسخه آفلاین Android/Desktop با SQLite
"""

from __future__ import annotations

import asyncio
import sqlite3
import traceback
import uuid
from pathlib import Path

import flet as ft
import jdatetime


# -----------------------------
# ابزارهای عمومی
# -----------------------------
def today_shamsi() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")


def normalize_digits(value) -> str:
    if value is None:
        return ""
    table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return str(value).translate(table)


def parse_number(value):
    text = normalize_digits(value)
    text = text.replace(",", "").replace("،", "").replace(" ", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def fmt_number(value) -> str:
    number = parse_number(value)
    if number is None:
        return ""
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def fmt_money(value) -> str:
    number = parse_number(value)
    if number is None:
        return "—"
    return f"{int(number):,} تومان"


def make_id() -> str:
    return str(uuid.uuid4())


# -----------------------------
# دیتابیس
# -----------------------------
class Database:
    def __init__(self):
        # مسیر قابل نوشتن در محیط Flet/Android و Desktop
        storage = Path.home() / ".ansari_orders"
        storage.mkdir(parents=True, exist_ok=True)
        self.path = storage / "orders.db"
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
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
                settlement TEXT NOT NULL DEFAULT '',
                qty REAL NOT NULL DEFAULT 0,
                delivery_date TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_orders_company
            ON orders(company_id);
            """
        )
        self.conn.commit()

    def companies(self):
        return self.conn.execute(
            "SELECT * FROM companies ORDER BY name"
        ).fetchall()

    def get_company(self, company_id):
        return self.conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()

    def add_company(self, name, visitor, phone):
        company_id = make_id()
        try:
            self.conn.execute(
                """
                INSERT INTO companies(id, name, visitor, phone, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (company_id, name.strip(), visitor.strip(), phone.strip()),
            )
            self.conn.commit()
            return company_id
        except sqlite3.IntegrityError:
            return None

    def delete_company(self, company_id):
        self.conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        self.conn.commit()

    def orders(self, company_id):
        return self.conn.execute(
            """
            SELECT * FROM orders
            WHERE company_id = ?
            ORDER BY rowid DESC
            """,
            (company_id,),
        ).fetchall()

    def get_order(self, order_id):
        return self.conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()

    def save_order(
        self,
        order_id,
        company_id,
        item,
        buy_price,
        sell_price,
        margin,
        settlement,
        qty,
        delivery_date,
        description,
    ):
        now = today_shamsi()
        if order_id:
            self.conn.execute(
                """
                UPDATE orders
                SET company_id=?, item=?, buy_price=?, sell_price=?,
                    margin=?, settlement=?, qty=?, delivery_date=?,
                    description=?, updated_at=?
                WHERE id=?
                """,
                (
                    company_id, item, buy_price, sell_price, margin,
                    settlement, qty, delivery_date, description, now, order_id
                ),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO orders(
                    id, company_id, item, buy_price, sell_price, margin,
                    settlement, qty, delivery_date, description,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    make_id(), company_id, item, buy_price, sell_price,
                    margin, settlement, qty, delivery_date, description,
                    now, now
                ),
            )
        self.conn.commit()

    def delete_order(self, order_id):
        self.conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# -----------------------------
# برنامه
# -----------------------------
def main(page: ft.Page):
    db = Database()

    # سازگاری با نسخه‌های مختلف Flet
    colors = getattr(ft, "Colors", None) or getattr(ft, "colors")
    icons = getattr(ft, "Icons", None) or getattr(ft, "icons")

    page.title = "مدیریت سفارشات انصاری"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = colors.BLUE_GREY_50
    page.padding = 12
    page.scroll = ft.ScrollMode.AUTO

    selected_company = {"id": None}
    editing_order = {"id": None}

    # -------------------------
    # پیام
    # -------------------------
    snack_text = ft.Text("", color="white", size=15)
    snack = ft.SnackBar(content=snack_text, duration=3000)
    page.overlay.append(snack)

    def message(text, error=True):
        snack_text.value = text
        try:
            snack.bgcolor = colors.RED_600 if error else colors.GREEN_600
        except Exception:
            pass
        snack.open = True
        page.update()

    # -------------------------
    # فیلدها
    # -------------------------
    field_style = dict(
        border_radius=10,
        filled=True,
        fill_color="white",
        text_size=16,
    )

    company_dropdown = ft.Dropdown(
        label="انتخاب شرکت",
        width=260,
        **field_style,
    )

    item_name = ft.TextField(label="نام کالا", **field_style)
    buy_price = ft.TextField(
        label="قیمت خرید (تومان)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **field_style,
    )
    sell_price = ft.TextField(
        label="قیمت مصرف‌کننده (تومان)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **field_style,
    )
    margin = ft.TextField(
        label="درصد اختلاف قیمت",
        read_only=True,
        **field_style,
    )
    settlement = ft.TextField(
        label="مدت تسویه (روز)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **field_style,
    )
    quantity = ft.TextField(
        label="تعداد سفارش (کارتن)",
        keyboard_type=ft.KeyboardType.NUMBER,
        **field_style,
    )
    delivery_date = ft.TextField(
        label="تاریخ تحویل",
        value=today_shamsi(),
        **field_style,
    )
    description = ft.TextField(
        label="توضیحات",
        multiline=True,
        min_lines=2,
        max_lines=4,
        **field_style,
    )

    company_name = ft.TextField(label="نام شرکت", **field_style)
    visitor = ft.TextField(label="نام ویزیتور", **field_style)
    phone = ft.TextField(
        label="شماره تلفن",
        keyboard_type=ft.KeyboardType.PHONE,
        **field_style,
    )

    # -------------------------
    # خلاصه
    # -------------------------
    summary_count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
    summary_qty = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
    summary_buy = ft.Text("—", size=13, weight=ft.FontWeight.BOLD)
    summary_sell = ft.Text("—", size=13, weight=ft.FontWeight.BOLD)

    def stat(title, value, icon, color):
        return ft.Container(
            expand=True,
            padding=8,
            bgcolor="white",
            border_radius=10,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=17, color=color),
                            ft.Text(title, size=12),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row([value], alignment=ft.MainAxisAlignment.CENTER),
                ],
                spacing=3,
                tight=True,
            ),
        )

    summary = ft.Row(
        [
            stat("سفارش", summary_count, icons.LIST_ALT, colors.TEAL_600),
            stat("کارتن", summary_qty, icons.INVENTORY_2, colors.ORANGE_600),
            stat("خرید", summary_buy, icons.PAYMENT, colors.BLUE_600),
            stat("فروش", summary_sell, icons.ATTACH_MONEY, colors.GREEN_600),
        ],
        spacing=7,
    )

    orders_column = ft.Column(spacing=10, tight=True)

    # -------------------------
    # محاسبه درصد
    # -------------------------
    def update_margin(_=None):
        buy = parse_number(buy_price.value)
        sell = parse_number(sell_price.value)
        if buy is not None and buy > 0 and sell is not None:
            margin.value = f"{((sell - buy) / buy) * 100:.1f}"
        else:
            margin.value = ""
        try:
            margin.update()
        except Exception:
            pass

    def format_price(e):
        value = normalize_digits(e.control.value)
        value = value.replace(",", "").replace("،", "").replace(" ", "")
        if value.isdigit():
            e.control.value = f"{int(value):,}"
        update_margin()
        try:
            e.control.update()
        except Exception:
            pass

    buy_price.on_change = format_price
    sell_price.on_change = format_price

    # -------------------------
    # شرکت‌ها
    # -------------------------
    def refresh_company_dropdown():
        rows = db.companies()
        company_dropdown.options = [
            ft.dropdown.Option(str(row["id"]), row["name"]) for row in rows
        ]

        current = selected_company["id"]
        valid = {str(row["id"]) for row in rows}
        if current not in valid:
            selected_company["id"] = str(rows[0]["id"]) if rows else None

        company_dropdown.value = selected_company["id"]

    def on_company_change(e):
        selected_company["id"] = e.control.value
        refresh_orders()
        page.update()

    company_dropdown.on_change = on_company_change

    # -------------------------
    # دیالوگ شرکت
    # -------------------------
    company_dialog = ft.AlertDialog(modal=True)

    def close_company(e=None):
        company_dialog.open = False
        page.update()

    def save_company(e):
        name = (company_name.value or "").strip()
        if not name:
            message("نام شرکت الزامی است!")
            return

        company_id = db.add_company(
            name,
            (visitor.value or "").strip(),
            (phone.value or "").strip(),
        )
        if not company_id:
            message("این شرکت قبلاً ثبت شده است!")
            return

        company_name.value = ""
        visitor.value = ""
        phone.value = ""
        selected_company["id"] = company_id
        refresh_company_dropdown()
        close_company()
        refresh_orders()
        message("شرکت با موفقیت ثبت شد.", False)

    company_dialog.title = ft.Text("افزودن شرکت تأمین‌کننده")
    company_dialog.content = ft.Column(
        [company_name, visitor, phone],
        tight=True,
        spacing=10,
        height=220,
    )
    company_dialog.actions = [
        ft.ElevatedButton(
            "ثبت شرکت",
            on_click=save_company,
            bgcolor=colors.TEAL_600,
            color="white",
        ),
        ft.TextButton("انصراف", on_click=close_company),
    ]
    page.overlay.append(company_dialog)

    def open_company(e):
        company_name.value = ""
        visitor.value = ""
        phone.value = ""
        company_dialog.open = True
        page.update()
        company_name.focus()

    # -------------------------
    # تأیید حذف
    # -------------------------
    confirm_dialog = ft.AlertDialog(modal=True)
    confirm_action = {"fn": None}

    def close_confirm(e=None):
        confirm_action["fn"] = None
        confirm_dialog.open = False
        page.update()

    def run_confirm(e):
        fn = confirm_action["fn"]
        confirm_action["fn"] = None
        confirm_dialog.open = False
        page.update()
        if fn:
            fn()

    confirm_dialog.actions = [
        ft.TextButton("حذف", on_click=run_confirm),
        ft.TextButton("انصراف", on_click=close_confirm),
    ]
    page.overlay.append(confirm_dialog)

    def confirm(title, text, fn):
        confirm_dialog.title = ft.Text(title)
        confirm_dialog.content = ft.Text(text)
        confirm_action["fn"] = fn
        confirm_dialog.open = True
        page.update()

    def delete_company(e):
        cid = selected_company["id"]
        if not cid:
            message("ابتدا یک شرکت انتخاب کنید!")
            return

        company = db.get_company(cid)
        if not company:
            return

        def do_delete():
            db.delete_company(cid)
            selected_company["id"] = None
            refresh_company_dropdown()
            refresh_orders()
            message("شرکت و تمام سفارش‌های آن حذف شد.", False)

        confirm(
            "حذف شرکت",
            f"شرکت «{company['name']}» و همه سفارش‌های آن حذف شود؟",
            do_delete,
        )

    # -------------------------
    # دیالوگ سفارش
    # -------------------------
    order_dialog = ft.AlertDialog(modal=True)

    def clear_order_fields():
        editing_order["id"] = None
        item_name.value = ""
        buy_price.value = ""
        sell_price.value = ""
        margin.value = ""
        settlement.value = ""
        quantity.value = ""
        delivery_date.value = today_shamsi()
        description.value = ""
        order_dialog.title = ft.Text("ثبت سفارش جدید")

    def close_order(e=None):
        order_dialog.open = False
        page.update()

    def save_order(e):
        cid = selected_company["id"]
        if not cid:
            message("ابتدا یک شرکت انتخاب کنید!")
            return

        name = (item_name.value or "").strip()
        if not name:
            message("نام کالا الزامی است!")
            return

        qty = parse_number(quantity.value)
        if qty is None or qty <= 0:
            message("تعداد سفارش باید بیشتر از صفر باشد!")
            return

        bp = parse_number(buy_price.value)
        sp = parse_number(sell_price.value)
        m = parse_number(margin.value)

        try:
            db.save_order(
                editing_order["id"],
                cid,
                name,
                bp,
                sp,
                m,
                normalize_digits(settlement.value).strip(),
                qty,
                (delivery_date.value or "").strip() or today_shamsi(),
                (description.value or "").strip(),
            )
        except Exception:
            message("خطا در ذخیره سفارش: " + traceback.format_exc()[-180:])
            return

        clear_order_fields()
        close_order()
        refresh_orders()
        message("سفارش با موفقیت ذخیره شد.", False)

    order_dialog.title = ft.Text("ثبت سفارش جدید")
    order_dialog.content = ft.Container(
        width=430,
        content=ft.Column(
            [
                item_name,
                buy_price,
                sell_price,
                margin,
                settlement,
                quantity,
                delivery_date,
                description,
            ],
            spacing=9,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        height=470,
    )
    order_dialog.actions = [
        ft.ElevatedButton(
            "ذخیره سفارش",
            on_click=save_order,
            bgcolor=colors.GREEN_600,
            color="white",
        ),
        ft.TextButton("انصراف", on_click=close_order),
    ]
    page.overlay.append(order_dialog)

    def open_new_order(e):
        if not selected_company["id"]:
            message("ابتدا یک شرکت انتخاب کنید!")
            return
        clear_order_fields()
        order_dialog.open = True
        page.update()
        item_name.focus()

    def open_edit_order(order):
        editing_order["id"] = order["id"]
        order_dialog.title = ft.Text("ویرایش سفارش")
        item_name.value = order["item"] or ""
        buy_price.value = fmt_number(order["buy_price"])
        sell_price.value = fmt_number(order["sell_price"])
        margin.value = (
            f"{order['margin']:.1f}" if order["margin"] is not None else ""
        )
        settlement.value = order["settlement"] or ""
        quantity.value = fmt_number(order["qty"])
        delivery_date.value = order["delivery_date"] or today_shamsi()
        description.value = order["description"] or ""
        order_dialog.open = True
        page.update()

    def delete_order(order_id):
        def do_delete():
            db.delete_order(order_id)
            refresh_orders()
            message("سفارش حذف شد.", False)

        confirm("حذف سفارش", "آیا این سفارش حذف شود؟", do_delete)

    # -------------------------
    # لیست و خلاصه سفارش‌ها
    # -------------------------
    def refresh_orders():
        orders_column.controls.clear()
        cid = selected_company["id"]

        if not cid:
            orders_column.controls.append(
                ft.Container(
                    padding=30,
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        "برای مشاهده سفارش‌ها یک شرکت انتخاب کنید.",
                        size=15,
                        color=colors.GREY_600,
                    ),
                )
            )
            refresh_summary()
            page.update()
            return

        rows = db.orders(cid)

        if not rows:
            orders_column.controls.append(
                ft.Container(
                    padding=30,
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        "هنوز سفارشی ثبت نشده است.",
                        size=15,
                        color=colors.GREY_600,
                    ),
                )
            )
            refresh_summary()
            page.update()
            return

        for row in rows:
            details = []
            if row["delivery_date"]:
                details.append(f"تحویل: {row['delivery_date']}")
            if row["buy_price"] is not None:
                details.append(f"خرید: {fmt_money(row['buy_price'])}")
            if row["sell_price"] is not None:
                details.append(f"فروش: {fmt_money(row['sell_price'])}")
            if row["margin"] is not None:
                details.append(f"اختلاف: {row['margin']:.1f}٪")
            if row["settlement"]:
                details.append(f"تسویه: {row['settlement']} روز")

            subtitle = " | ".join(details)
            if row["description"]:
                subtitle += f"\n📝 {row['description']}"

            orders_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.ListTile(
                            leading=ft.Icon(
                                icons.LOCAL_SHIPPING,
                                color=colors.TEAL_600,
                                size=30,
                            ),
                            title=ft.Text(
                                f"{row['item']} — {fmt_number(row['qty'])} کارتن",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                            ),
                            subtitle=ft.Text(
                                subtitle,
                                size=13,
                                color=colors.GREY_700,
                            ),
                            trailing=ft.Row(
                                [
                                    ft.IconButton(
                                        icons.EDIT_OUTLINED,
                                        tooltip="ویرایش",
                                        on_click=lambda e, r=row: open_edit_order(r),
                                    ),
                                    ft.IconButton(
                                        icons.DELETE_OUTLINE,
                                        tooltip="حذف",
                                        on_click=lambda e, oid=row["id"]: delete_order(oid),
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

    def refresh_summary():
        cid = selected_company["id"]
        if not cid:
            summary_count.value = "0"
            summary_qty.value = "0"
            summary_buy.value = "—"
            summary_sell.value = "—"
            return

        rows = db.orders(cid)
        total_qty = 0
        total_buy = 0
        total_sell = 0

        for row in rows:
            q = row["qty"] or 0
            total_qty += q
            total_buy += (row["buy_price"] or 0) * q
            total_sell += (row["sell_price"] or 0) * q

        summary_count.value = str(len(rows))
        summary_qty.value = fmt_number(total_qty) or "0"
        summary_buy.value = fmt_money(total_buy) if total_buy else "—"
        summary_sell.value = fmt_money(total_sell) if total_sell else "—"

    # -------------------------
    # گزارش متنی
    # -------------------------
    def build_report(company, rows):
        lines = [
            "📋 گزارش سفارشات",
            "🏬 هایپر گوشت انصاری",
            "━━━━━━━━━━━━━━━━━━━━",
            f"شرکت: {company['name']}",
        ]

        if company["visitor"]:
            lines.append(f"ویزیتور: {company['visitor']}")
        if company["phone"]:
            lines.append(f"📞 {company['phone']}")

        lines += [
            f"📅 تاریخ گزارش: {today_shamsi()}",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for index, row in enumerate(rows, 1):
            lines.append(f"🔸 {index}. {row['item']}")
            lines.append(f"    تعداد: {fmt_number(row['qty'])} کارتن")
            if row["delivery_date"]:
                lines.append(f"    🗓 تحویل: {row['delivery_date']}")
            if row["buy_price"] is not None:
                lines.append(f"    💰 خرید: {fmt_money(row['buy_price'])}")
            if row["sell_price"] is not None:
                lines.append(f"    💵 فروش: {fmt_money(row['sell_price'])}")
            if row["margin"] is not None:
                lines.append(f"    📈 اختلاف: {row['margin']:.1f}٪")
            if row["settlement"]:
                lines.append(f"    ⏱ تسویه: {row['settlement']} روز")
            if row["description"]:
                lines.append(f"    📝 {row['description']}")
            lines.append("")

        total_qty = sum(row["qty"] or 0 for row in rows)
        total_buy = sum((row["buy_price"] or 0) * (row["qty"] or 0) for row in rows)
        total_sell = sum((row["sell_price"] or 0) * (row["qty"] or 0) for row in rows)
        profit = total_sell - total_buy
        percent = (profit / total_buy * 100) if total_buy else 0

        lines += [
            "━━━━━━━━━━━━━━━━━━━━",
            f"📦 تعداد سفارش: {len(rows)}",
            f"📊 مجموع کارتن: {fmt_number(total_qty)}",
            f"💳 مجموع خرید: {fmt_money(total_buy)}",
            f"💵 مجموع فروش: {fmt_money(total_sell)}",
            f"✅ اختلاف کل: {fmt_money(profit)} ({percent:.1f}%)",
        ]
        return "\n".join(lines)

    # -------------------------
    # گزارش / کپی
    # -------------------------
    report_text = {"value": ""}

    preview_text = ft.Text("", size=14, selectable=True)
    preview_dialog = ft.AlertDialog(modal=True)

    def close_report(e=None):
        preview_dialog.open = False
        page.update()

    async def copy_report(e):
        text = report_text["value"]
        if not text:
            return

        # Flet 0.24+: set_clipboard async
        setter = getattr(page, "set_clipboard_async", None)
        if setter is None:
            setter = getattr(page, "set_clipboard", None)

        if setter is None:
            message("قابلیت کپی در این نسخه Flet در دسترس نیست.")
            return

        try:
            result = setter(text)
            if asyncio.iscoroutine(result) or hasattr(result, "__await__"):
                await result
            message("گزارش کپی شد؛ حالا در ایتا Paste کنید.", False)
        except Exception:
            message("خطا در کپی متن.")

    preview_dialog.title = ft.Text("گزارش سفارشات")
    preview_dialog.content = ft.Container(
        width=430,
        height=460,
        content=ft.Column([preview_text], scroll=ft.ScrollMode.AUTO),
    )
    preview_dialog.actions = [
        ft.ElevatedButton(
            "کپی متن برای ایتا",
            on_click=copy_report,
            bgcolor=colors.TEAL_600,
            color="white",
        ),
        ft.TextButton("بستن", on_click=close_report),
    ]
    page.overlay.append(preview_dialog)

    def show_report(e):
        cid = selected_company["id"]
        if not cid:
            message("ابتدا یک شرکت انتخاب کنید!")
            return

        company = db.get_company(cid)
        rows = db.orders(cid)

        if not rows:
            message("برای این شرکت سفارشی وجود ندارد!")
            return

        report_text["value"] = build_report(company, rows)
        preview_text.value = report_text["value"]
        preview_dialog.open = True
        page.update()

    # -------------------------
    # AppBar
    # -------------------------
    page.appbar = ft.AppBar(
        leading=ft.Icon(icons.SHOPPING_CART, color="white"),
        title=ft.Text(
            "هایپر گوشت انصاری",
            color="white",
            size=21,
            weight=ft.FontWeight.BOLD,
        ),
        center_title=True,
        bgcolor=colors.TEAL_700,
    )

    # -------------------------
    # چیدمان
    # -------------------------
    page.add(
        ft.Container(height=5),
        ft.Row(
            [
                company_dropdown,
                ft.IconButton(
                    icons.ADD_BUSINESS,
                    tooltip="افزودن شرکت",
                    icon_size=29,
                    on_click=open_company,
                ),
                ft.IconButton(
                    icons.DELETE_FOREVER_OUTLINED,
                    tooltip="حذف شرکت",
                    icon_size=29,
                    on_click=delete_company,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        ),
        ft.Container(height=8),
        ft.Row(
            [
                ft.ElevatedButton(
                    "ثبت سفارش جدید",
                    icon=icons.ADD_SHOPPING_CART,
                    width=210,
                    height=48,
                    bgcolor=colors.ORANGE_600,
                    color="white",
                    on_click=open_new_order,
                ),
                ft.ElevatedButton(
                    "گزارش",
                    icon=icons.DESCRIPTION,
                    width=150,
                    height=48,
                    bgcolor=colors.TEAL_600,
                    color="white",
                    on_click=show_report,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        ),
        ft.Container(height=12),
        summary,
        ft.Divider(height=20),
        ft.Row(
            [
                ft.Icon(icons.LIST_ALT, color=colors.TEAL_800),
                ft.Text(
                    "لیست سفارشات ثبت‌شده",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=colors.TEAL_800,
                ),
            ]
        ),
        ft.Container(height=5),
        orders_column,
    )

    refresh_company_dropdown()
    refresh_orders()


# -----------------------------
# اجرا
# -----------------------------
if __name__ == "__main__":
    ft.app(target=main)
