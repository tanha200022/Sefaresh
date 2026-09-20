"""
سفارشات انصاری — نسخهٔ کامل اصلاح‌شده
"""
import os
import tempfile
import traceback
import uuid

import flet as ft

try:
    import jdatetime
    JDATETIME_OK = True
except Exception:
    jdatetime = None
    JDATETIME_OK = False

# --- سازگاری با Flet جدید/قدیم ---
try:
    C = ft.Colors
    I = ft.Icons
except AttributeError:
    C = ft.colors
    I = ft.icons


# ---------- توابع کمکی ----------
def today_shamsi() -> str:
    if JDATETIME_OK:
        return jdatetime.date.today().strftime("%Y/%m/%d")
    return ""


def parse_number(value):
    if value is None:
        return None
    cleaned = str(value).replace(",", "").replace("،", "").replace(" ", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def fmt_money(value) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{int(value):,} تومان"
    except Exception:
        return "—"


# ---------- برنامهٔ اصلی ----------
def main(page: ft.Page):
    if not JDATETIME_OK:
        page.add(ft.Text(
            "کتابخانه jdatetime نصب نیست.\n"
            "با دستور زیر نصب کنید:  pip install jdatetime",
            color="red", rtl=False,
        ))
        return

    # ===== تنظیمات صفحه =====
    page.title = "سفارشات انصاری"
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
        title=ft.Text("هایپر گوشت انصاری", color="white",
                      weight=ft.FontWeight.BOLD, size=22),
        bgcolor=C.TEAL_700, center_title=True, elevation=4,
    )

    # ===== وضعیت =====
    companies = page.client_storage.get("companies") or []
    orders = page.client_storage.get("orders") or []

    def save_data():
        try:
            page.client_storage.set("companies", companies)
            page.client_storage.set("orders", orders)
        except Exception:
            show_message("خطا در ذخیره‌سازی: " + traceback.format_exc()[-150:])

    def migrate_data():
        changed = False
        name_to_id = {}
        if companies and isinstance(companies[0], str):
            old = list(companies)
            companies.clear()
            for name in old:
                cid = str(uuid.uuid4())
                companies.append({"id": cid, "name": name, "visitor": "", "phone": ""})
                name_to_id[name] = cid
            changed = True
        else:
            for c in companies:
                if isinstance(c, dict) and "id" in c:
                    name_to_id[c["name"]] = c["id"]

        for o in list(orders):
            if not isinstance(o, dict):
                orders.remove(o); changed = True; continue
            if "id" not in o:
                o["id"] = str(uuid.uuid4()); changed = True
            if "company_id" not in o:
                o["company_id"] = name_to_id.get(o.get("company", ""), "")
                changed = True
            for k, v in {
                "item": "", "buy_price": None, "sell_price": None,
                "margin": "", "settlement": "", "qty": "",
                "date": today_shamsi(), "desc": "",
            }.items():
                if k not in o:
                    o[k] = v; changed = True
        if changed:
            save_data()

    migrate_data()

    # ===== Snackbar =====
    snack_text = ft.Text("", size=15, color="white")
    snack_bar = ft.SnackBar(
        content=snack_text,
        behavior=ft.SnackBarBehavior.FLOATING,
        duration=3000,
    )
    page.overlay.append(snack_bar)

    def show_message(text, is_error=True):
        snack_text.value = text
        snack_bar.bgcolor = C.RED_600 if is_error else C.GREEN_600
        snack_bar.open = True
        page.update()

    # ===== دیالوگ تأیید =====
    confirm_state = {"action": None}
    confirm_title = ft.Text("", weight=ft.FontWeight.BOLD, size=18)
    confirm_content = ft.Text("", size=15)

    def _do_confirm(e):
        confirm_dialog.open = False
        page.update()
        action = confirm_state.get("action")
        confirm_state["action"] = None
        if action:
            try:
                action()
            except Exception:
                show_message(traceback.format_exc()[-200:])

    def _cancel_confirm(e):
        confirm_dialog.open = False
        confirm_state["action"] = None
        page.update()

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=confirm_title, content=confirm_content,
        actions=[
            ft.TextButton("حذف", on_click=_do_confirm,
                          style=ft.ButtonStyle(color=C.RED_600)),
            ft.TextButton("انصراف", on_click=_cancel_confirm),
        ],
    )
    page.overlay.append(confirm_dialog)

    def ask_confirm(title, message, action):
        confirm_title.value = title
        confirm_content.value = message
        confirm_state["action"] = action
        confirm_dialog.open = True
        page.update()

    # ===== استایل فیلدها =====
    FIELD_STYLE = {
        "border_radius": 10, "filled": True,
        "fill_color": C.WHITE, "text_size": 17,
        "border_color": C.TEAL_200,
        "focused_border_color": C.TEAL_600,
    }

    def get_company(cid):
        for c in companies:
            if c.get("id") == cid:
                return c
        return None

    def company_options():
        return [ft.dropdown.Option(key=c["id"], text=c["name"]) for c in companies]

    # ===== Dropdown =====
    company_dropdown = ft.Dropdown(
        label="انتخاب شرکت",
        options=company_options(),
        width=260, border_radius=10, filled=True,
        fill_color=C.WHITE, text_size=17,
    )
    if companies:
        company_dropdown.value = companies[0]["id"]

    # ===== فیلدهای کالا (با کیبورد عددی) =====
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
    txt_margin = ft.TextField(label="حاشیه سود (%)", read_only=True, **FIELD_STYLE)
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
    txt_date = ft.TextField(label="تاریخ تحویل", value=today_shamsi(), **FIELD_STYLE)
    txt_desc = ft.TextField(
        label="توضیحات",
        multiline=True, min_lines=2, max_lines=4,
        **FIELD_STYLE,
    )

    def update_margin(_=None):
        buy = parse_number(txt_buy_price.value)
        sell = parse_number(txt_sell_price.value)
        if buy and buy > 0 and sell is not None:
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
            try:
                ctrl.value = f"{int(raw):,}"
                ctrl.update()
            except Exception:
                pass
        update_margin()

    txt_buy_price.on_change = format_price_field
    txt_sell_price.on_change = format_price_field

    # زنجیرهٔ Tab
    txt_item_name.on_submit = lambda e: txt_buy_price.focus()
    txt_buy_price.on_submit = lambda e: txt_sell_price.focus()
    txt_sell_price.on_submit = lambda e: txt_settlement.focus()
    txt_settlement.on_submit = lambda e: txt_qty.focus()
    txt_qty.on_submit = lambda e: txt_date.focus()
    txt_date.on_submit = lambda e: txt_desc.focus()

    # ===== فیلدهای شرکت =====
    txt_comp_name = ft.TextField(label="نام شرکت", **FIELD_STYLE)
    txt_visitor = ft.TextField(label="نام ویزیتور", **FIELD_STYLE)
    txt_phone = ft.TextField(
        label="شماره تلفن",
        keyboard_type=ft.KeyboardType.PHONE,
        **FIELD_STYLE,
    )

    # ===== لیست سفارشات =====
    orders_list = ft.Column(spacing=12, tight=True)

    # ===== کارت خلاصهٔ آماری =====
    summary_count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
    summary_qty = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
    summary_buy = ft.Text("—", size=13, weight=ft.FontWeight.BOLD)
    summary_sell = ft.Text("—", size=13, weight=ft.FontWeight.BOLD)

    def _stat(label, value_ctrl, icon, color):
        return ft.Container(
            padding=10, border_radius=10, bgcolor=C.WHITE, expand=True,
            content=ft.Column([
                ft.Row([ft.Icon(icon, color=color, size=18),
                        ft.Text(label, size=13, color=C.GREY_700)],
                       spacing=5, alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([value_ctrl], alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=4, tight=True),
        )

    summary_row = ft.Row([
        _stat("سفارش", summary_count, I.LIST_ALT, C.TEAL_600),
        _stat("کارتن", summary_qty, I.INVENTORY_2, C.ORANGE_600),
        _stat("خرید", summary_buy, I.PAYMENT, C.BLUE_600),
        _stat("فروش", summary_sell, I.ATTACH_MONEY, C.GREEN_600),
    ], spacing=8)

    def refresh_summary():
        cid = company_dropdown.value
        count = 0
        total_qty = total_buy = total_sell = 0.0
        if cid:
            for o in orders:
                if o.get("company_id") != cid:
                    continue
                count += 1
                q = parse_number(o.get("qty")) or 0
                bp = parse_number(o.get("buy_price")) or 0
                sp = parse_number(o.get("sell_price")) or 0
                total_qty += q
                total_buy += bp * q
                total_sell += sp * q
        summary_count.value = str(count)
        summary_qty.value = f"{int(total_qty):,}" if total_qty else "0"
        summary_buy.value = fmt_money(total_buy) if total_buy else "—"
        summary_sell.value = fmt_money(total_sell) if total_sell else "—"

    # ===== به‌روزرسانی لیست =====
    def refresh_orders_list():
        orders_list.controls.clear()
        cid = company_dropdown.value

        if not cid:
            orders_list.controls.append(
                ft.Container(
                    padding=30, alignment=ft.alignment.center,
                    content=ft.Column([
                        ft.Icon(I.BUSINESS_OUTLINED, size=60, color=C.GREY_400),
                        ft.Text("برای مشاهدهٔ سفارشات، یک شرکت انتخاب کنید.",
                                color=C.GREY_600, size=15,
                                text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                )
            )
            refresh_summary()
            page.update()
            return

        filtered = [o for o in orders if o.get("company_id") == cid]
        if not filtered:
            orders_list.controls.append(
                ft.Container(
                    padding=30, alignment=ft.alignment.center,
                    content=ft.Column([
                        ft.Icon(I.INBOX_OUTLINED, size=60, color=C.GREY_400),
                        ft.Text("هنوز سفارشی برای این شرکت ثبت نشده است.",
                                color=C.GREY_600, size=15),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                )
            )
            refresh_summary()
            page.update()
            return

        for ord in filtered:
            parts = []
            if ord.get("date"):
                parts.append(f"تاریخ: {ord['date']}")
            if ord.get("buy_price"):
                parts.append(f"خرید: {fmt_money(ord['buy_price'])}")
            if ord.get("sell_price"):
                parts.append(f"فروش: {fmt_money(ord['sell_price'])}")
            if ord.get("margin"):
                parts.append(f"سود: {ord['margin']}٪")
            if ord.get("settlement"):
                parts.append(f"تسویه: {ord['settlement']} روز")

            subtitle = "  |  ".join(parts)
            if ord.get("desc"):
                subtitle += f"\n📝 {ord['desc']}"

            orders_list.controls.append(
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=12,
                        content=ft.ListTile(
                            leading=ft.Icon(I.LOCAL_SHIPPING, color=C.TEAL_500, size=32),
                            title=ft.Text(
                                f"{ord.get('item', '')} — {ord.get('qty', '')} کارتن",
                                size=17, weight=ft.FontWeight.BOLD,
                            ),
                            subtitle=ft.Text(subtitle, size=14, color=C.GREY_700),
                            trailing=ft.Row([
                                ft.IconButton(I.EDIT_OUTLINED, tooltip="ویرایش",
                                              icon_color=C.TEAL_700,
                                              on_click=lambda e, o=ord: open_edit_item(o)),
                                ft.IconButton(I.DELETE_OUTLINE, tooltip="حذف",
                                              icon_color=C.RED_500,
                                              on_click=lambda e, oid=ord["id"]: delete_order(oid)),
                            ], tight=True, spacing=0),
                        ),
                    ),
                )
            )
        refresh_summary()
        page.update()

    company_dropdown.on_change = lambda e: refresh_orders_list()

    # ===== دیالوگ کالا =====
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

    def close_item_dlg(e=None):
        item_dialog.open = False
        page.update()

    def save_item(e):
        try:
            cid = company_dropdown.value
            if not cid:
                show_message("ابتدا یک شرکت انتخاب کنید!"); return
            name = (txt_item_name.value or "").strip()
            if not name:
                show_message("نام کالا الزامی است!"); return
            qty = parse_number(txt_qty.value)
            if qty is None or qty <= 0:
                show_message("تعداد سفارش باید عددی مثبت باشد!"); return
            bp = parse_number(txt_buy_price.value)
            sp = parse_number(txt_sell_price.value)
            if (txt_buy_price.value or "").strip() and bp is None:
                show_message("قیمت خرید نامعتبر است!"); return
            if (txt_sell_price.value or "").strip() and sp is None:
                show_message("قیمت مصرف نامعتبر است!"); return

            record = {
                "id": editing_id["value"] or str(uuid.uuid4()),
                "company_id": cid,
                "item": name,
                "buy_price": bp, "sell_price": sp,
                "margin": txt_margin.value or "",
                "settlement": (txt_settlement.value or "").strip(),
                "qty": (txt_qty.value or "").strip(),
                "date": (txt_date.value or "").strip() or today_shamsi(),
                "desc": (txt_desc.value or "").strip(),
            }

            if editing_id["value"]:
                for i, o in enumerate(orders):
                    if o["id"] == editing_id["value"]:
                        orders[i] = record; break
            else:
                orders.append(record)

            save_data()
            clear_item_fields()
            close_item_dlg()
            refresh_orders_list()
            show_message("سفارش با موفقیت ثبت شد.", is_error=False)
        except Exception:
            show_message(f"خطا: {traceback.format_exc()[-200:]}")

    item_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("ثبت کالای جدید", size=20,
                      weight=ft.FontWeight.BOLD, color=C.TEAL_800),
        content=ft.Column(
            [txt_item_name, txt_buy_price, txt_sell_price, txt_margin,
             txt_settlement, txt_qty, txt_date, txt_desc],
            scroll=ft.ScrollMode.AUTO, height=450, tight=True, spacing=10,
        ),
        actions=[
            ft.ElevatedButton("ثبت کالا", on_click=save_item,
                              bgcolor=C.GREEN_600, color="white"),
            ft.TextButton("انصراف", on_click=close_item_dlg),
        ],
    )
    page.overlay.append(item_dialog)

    def open_add_item(e):
        if not company_dropdown.value:
            show_message("ابتدا یک شرکت انتخاب کنید!"); return
        clear_item_fields()
        item_dialog.open = True
        page.update()
        txt_item_name.focus()

    def open_edit_item(order):
        editing_id["value"] = order["id"]
        item_dialog.title.value = "ویرایش کالا"
        txt_item_name.value = order.get("item", "")
        bp, sp = order.get("buy_price"), order.get("sell_price")
        txt_buy_price.value = f"{int(bp):,}" if bp else ""
        txt_sell_price.value = f"{int(sp):,}" if sp else ""
        txt_margin.value = order.get("margin", "")
        txt_settlement.value = order.get("settlement", "")
        txt_qty.value = order.get("qty", "")
        txt_date.value = order.get("date", today_shamsi())
        txt_desc.value = order.get("desc", "")
        item_dialog.open = True
        page.update()

    # ===== دیالوگ شرکت =====
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
            if not name:
                show_message("نام شرکت الزامی است!"); return
            if any(c["name"] == name for c in companies):
                show_message("این شرکت قبلاً ثبت شده است!"); return
            new = {
                "id": str(uuid.uuid4()),
                "name": name,
                "visitor": (txt_visitor.value or "").strip(),
                "phone": (txt_phone.value or "").strip(),
            }
            companies.append(new)
            save_data()
            company_dropdown.options = company_options()
            company_dropdown.value = new["id"]
            clear_comp_fields()
            close_comp_dlg()
            refresh_orders_list()
            show_message("شرکت با موفقیت ثبت شد.", is_error=False)
        except Exception:
            show_message(f"خطا: {traceback.format_exc()[-200:]}")

    comp_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("افزودن شرکت تأمین‌کننده", size=20,
                      weight=ft.FontWeight.BOLD, color=C.TEAL_800),
        content=ft.Column([txt_comp_name, txt_visitor, txt_phone],
                          tight=True, spacing=10, height=230),
        actions=[
            ft.ElevatedButton("ثبت شرکت", on_click=save_company,
                              bgcolor=C.TEAL_600, color="white"),
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
            show_message("ابتدا یک شرکت انتخاب کنید!"); return
        company = get_company(cid)
        if not company:
            return

        def do_delete():
            try:
                companies.remove(company)
                orders[:] = [o for o in orders if o.get("company_id") != cid]
                save_data()
                company_dropdown.options = company_options()
                company_dropdown.value = companies[0]["id"] if companies else None
                refresh_orders_list()
                show_message("شرکت و سفارشات آن حذف شد.", is_error=False)
            except Exception:
                show_message(traceback.format_exc()[-200:])

        ask_confirm(
            "حذف شرکت",
            f'آیا از حذف شرکت «{company["name"]}» و تمام سفارشات آن مطمئن هستید؟',
            do_delete,
        )

    def delete_order(oid):
        def do_delete():
            try:
                orders[:] = [o for o in orders if o["id"] != oid]
                save_data()
                refresh_orders_list()
                show_message("سفارش حذف شد.", is_error=False)
            except Exception:
                show_message(traceback.format_exc()[-200:])

        ask_confirm("حذف سفارش", "آیا از حذف این سفارش مطمئن هستید؟", do_delete)

    # ===== خروجی متنی گزارش (اصلاح‌شده برای اندروید) =====
    async def export_summary(e):
        cid = company_dropdown.value
        if not cid:
            show_message("ابتدا یک شرکت انتخاب کنید!")
            return

        company = get_company(cid)
        filtered = [o for o in orders if o.get("company_id") == cid]
        if not filtered:
            show_message("سفارشی برای خروجی وجود ندارد!")
            return

        # --- ساخت متن گزارش ---
        lines = [f"گزارش سفارشات شرکت: {company['name']}"]
        if company.get("visitor"):
            lines.append(f"ویزیتور: {company['visitor']}")
        if company.get("phone"):
            lines.append(f"تلفن: {company['phone']}")
        lines.append(f"تاریخ گزارش: {today_shamsi()}")
        lines.append("=" * 50)

        for i, o in enumerate(filtered, 1):
            lines.append(f"{i}. {o.get('item','')} — {o.get('qty','')} کارتن")
            if o.get("date"):
                lines.append(f"   تاریخ تحویل: {o['date']}")
            if o.get("buy_price"):
                lines.append(f"   قیمت خرید: {fmt_money(o['buy_price'])}")
            if o.get("sell_price"):
                lines.append(f"   قیمت فروش: {fmt_money(o['sell_price'])}")
            if o.get("margin"):
                lines.append(f"   حاشیه سود: {o['margin']}%")
            if o.get("settlement"):
                lines.append(f"   مدت تسویه: {o['settlement']} روز")
            if o.get("desc"):
                lines.append(f"   توضیحات: {o['desc']}")
            lines.append("")

        text = "\n".join(lines)

        # --- پیدا کردن مسیر قابل نوشتن ---
        folder = None

        async def _try_get(method_name):
            fn = getattr(page, method_name, None)
            if fn is None:
                return None
            try:
                res = fn()
                if hasattr(res, "__await__"):
                    res = await res
                return res
            except Exception:
                return None

        for name in (
            "get_application_documents_directory",
            "get_downloads_directory",
            "get_external_storage_directory",
        ):
            folder = await _try_get(name)
            if folder:
                break

        if not folder:
            folder = tempfile.gettempdir()

        # --- تلاش برای ذخیره در فایل ---
        try:
            out_dir = os.path.join(folder, "AnsariOrders")
            os.makedirs(out_dir, exist_ok=True)

            safe_name = (company["name"] or "company").replace("/", "-").replace("\\", "-")
            filename = f"{safe_name}_{today_shamsi().replace('/', '-')}.txt"
            path = os.path.join(out_dir, filename)

            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

            show_message(f"گزارش ذخیره شد:\n{path}", is_error=False)
            return
        except Exception:
            pass

        # --- اگر فایل نشد، کپی در کلیپ‌بورد ---
        try:
            set_cb = (getattr(page, "set_clipboard_async", None)
                      or getattr(page, "set_clipboard", None))
            if set_cb is None:
                raise RuntimeError("clipboard API پیدا نشد")
            res = set_cb(text)
            if hasattr(res, "__await__"):
                await res
            show_message("ذخیرهٔ فایل ممکن نشد؛ متن گزارش در کلیپ‌بورد کپی شد ✅",
                         is_error=False)
        except Exception:
            show_message(f"خطا در خروجی: {traceback.format_exc()[-200:]}")

    # ===== چیدمان =====
    page.add(
        ft.Container(height=8),
        ft.Row(
            [
                company_dropdown,
                ft.IconButton(I.ADD_BUSINESS, on_click=open_add_company,
                              tooltip="افزودن شرکت", icon_size=30,
                              icon_color=C.TEAL_700),
                ft.IconButton(I.DELETE_FOREVER_OUTLINED, on_click=delete_company,
                              tooltip="حذف شرکت", icon_size=30,
                              icon_color=C.RED_400),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        ),
        ft.Container(height=12),
        ft.Row(
            [
                ft.ElevatedButton(
                    "ثبت کالای جدید", on_click=open_add_item,
                    icon=I.ADD_SHOPPING_CART,
                    width=230, height=50,
                    bgcolor=C.ORANGE_600, color="white", elevation=4,
                ),
                ft.IconButton(I.DOWNLOAD_OUTLINED, on_click=export_summary,
                              tooltip="خروجی متنی گزارش", icon_size=30,
                              icon_color=C.TEAL_700),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        ),
        ft.Container(height=15),
        summary_row,
        ft.Divider(height=25, color=C.GREY_300),
        ft.Row([
            ft.Icon(I.LIST_ALT, color=C.TEAL_800),
            ft.Text("لیست سفارشات ثبت شده", size=18,
                    weight=ft.FontWeight.BOLD, color=C.TEAL_800),
        ]),
        ft.Container(height=8),
        orders_list,
    )

    # رفرش اولیه
    refresh_orders_list()


if __name__ == "__main__":
    ft.app(target=main)
