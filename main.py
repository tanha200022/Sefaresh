import asyncio
import os
import traceback
import uuid

import flet as ft

try:
    import jdatetime
except Exception:
    jdatetime = None

# ---------- سازگاری با نسخه های مختلف flet ----------
Colors = getattr(ft, "Colors", None) or ft.colors
Icons  = getattr(ft, "Icons", None) or ft.icons

try:
    _Option = ft.DropdownOption          # flet >= 0.26
except AttributeError:
    _Option = ft.dropdown.Option         # flet < 0.26

def option(key, text):
    return _Option(key=key, text=text)

HAS_SCREENSHOT = hasattr(ft, "Screenshot")

# ---------- ابزارهای کمکی ----------
_DIGITS_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def normalize_digits(value):
    return (value or "").translate(_DIGITS_MAP)

def to_number(value):
    if value is None:
        return None
    cleaned = normalize_digits(str(value)).replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

def qty_text(value):
    q = to_number(str(value))
    return f"{q:g}" if q is not None else str(value or "")

def money(value):
    return f"{int(value):,}" if value else ""

def format_price(value):
    return f"{int(value):,} تومان" if value else "—"


def main(page: ft.Page):
    if jdatetime is None:
        page.add(ft.Text("خطای راه اندازی: کتابخانه jdatetime نصب نیست.\n"
                         "ابتدا اجرا کنید:  pip install jdatetime", color="red", rtl=False))
        return

    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

    # ---------------- 1. تنظیمات ظاهری ----------------
    page.title = "هایپر گوشت انصاری"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = Colors.BLUE_GREY_50
    page.rtl = True
    page.theme = ft.Theme(
        color_scheme_seed=Colors.TEAL,
        text_theme=ft.TextTheme(body_medium=ft.TextStyle(size=18)),
    )
    page.appbar = ft.AppBar(
        leading=ft.Icon(Icons.SHOPPING_CART_CHECKOUT, color="white"),
        title=ft.Text("هایپر گوشت انصاری", color="white",
                      weight=ft.FontWeight.BOLD, size=22),
        bgcolor=Colors.TEAL_700, center_title=True, elevation=4,
    )

    # ---------------- 2. پیام و دیالوگ تایید (تک نمونه) ----------------
    snack_text = ft.Text("", size=16, color="white")
    snack = ft.SnackBar(content=snack_text)

    def show_message(text, error=True):
        snack_text.value = text
        snack.bgcolor = Colors.RED_600 if error else Colors.GREEN_600
        snack.open = True
        page.update()

    confirm_pending = {"action": None}
    confirm_title = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
    confirm_body = ft.Text("", size=16)
    confirm_yes_label = ft.Text("حذف")

    def on_confirm_yes(e):
        action = confirm_pending["action"]
        confirm_pending["action"] = None   # جلوگیری از اجرای دوباره
        confirm_dialog.open = False
        page.update()
        if action:
            action()

    def on_confirm_no(e):
        confirm_pending["action"] = None
        confirm_dialog.open = False
        page.update()

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=confirm_title,
        content=confirm_body,
        actions=[
            ft.TextButton(content=confirm_yes_label, on_click=on_confirm_yes),
            ft.TextButton("انصراف", on_click=on_confirm_no),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.extend([snack, confirm_dialog])

    def ask_confirm(title, message, action, yes_label="حذف"):
        confirm_title.value = title
        confirm_body.value = message
        confirm_yes_label.value = yes_label
        confirm_pending["action"] = action
        confirm_dialog.open = True
        page.update()

    def close_dialog(dlg):
        dlg.open = False
        page.update()

    # ---------------- 3. ذخیره سازی و مهاجرت داده ----------------
    companies = page.client_storage.get("companies") or []
    orders = page.client_storage.get("orders") or []

    def save_data():
        page.client_storage.set("companies", companies)
        page.client_storage.set("orders", orders)

    def migrate_data():
        changed = False
        name_to_id = {}
        if companies and isinstance(companies[0], str):      # فرمت قدیمی
            old_names = list(companies)
            companies.clear()
            for name in old_names:
                cid = str(uuid.uuid4())
                companies.append({"id": cid, "name": name, "visitor": "", "phone": ""})
                name_to_id[name] = cid
            changed = True
        else:
            for c in companies:
                if not isinstance(c, dict):
                    continue
                if "id" not in c:
                    c["id"] = str(uuid.uuid4())
                    changed = True
                if c.get("name") and c["name"] not in name_to_id:
                    name_to_id[c["name"]] = c["id"]
                for k in ("visitor", "phone"):
                    if k not in c:
                        c[k] = ""
                        changed = True

        for o in list(orders):
            if not isinstance(o, dict):
                orders.remove(o)
                changed = True
                continue
            if "id" not in o:
                o["id"] = str(uuid.uuid4())
                changed = True
            if "company_id" not in o:
                o["company_id"] = name_to_id.get(o.get("company", ""), "")
                changed = True
            defaults = {"item": "", "buy_price": None, "sell_price": None,
                        "margin": "", "settlement": "", "qty": 1,
                        "date": today_shamsi, "desc": ""}
            for k, v in defaults.items():
                if k not in o:
                    o[k] = v
                    changed = True
        if changed:
            save_data()

    migrate_data()

    # ---------------- 4. فیلدهای فرم کالا ----------------
    field_style = {"border_radius": 10, "filled": True,
                   "fill_color": Colors.WHITE, "text_size": 18}

    txt_item_name  = ft.TextField(label="نام کالا", **field_style)
    txt_buy_price  = ft.TextField(label="قیمت خرید (تومان)", keyboard_type=ft.KeyboardType.NUMBER, **field_style)
    txt_sell_price = ft.TextField(label="قیمت مصرف (تومان)", keyboard_type=ft.KeyboardType.NUMBER, **field_style)
    txt_margin     = ft.TextField(label="حاشیه سود (%)", read_only=True, **field_style)
    txt_settlement = ft.TextField(label="مدت تسویه (روز)", keyboard_type=ft.KeyboardType.NUMBER, **field_style)
    txt_qty        = ft.TextField(label="تعداد سفارش (کارتن)", keyboard_type=ft.KeyboardType.NUMBER, **field_style)
    txt_date       = ft.TextField(label="تاریخ تحویل", value=today_shamsi, **field_style)
    txt_desc       = ft.TextField(label="توضیحات", multiline=True, min_lines=2, max_lines=4, **field_style)

    def recalc_margin():
        buy = to_number(txt_buy_price.value)
        sell = to_number(txt_sell_price.value)
        if buy and buy > 0 and sell is not None:
            txt_margin.value = f"{((sell - buy) / buy) * 100:.1f}"
        else:
            txt_margin.value = ""

    def format_currency(e):
        raw = normalize_digits(e.control.value).replace(",", "").strip()
        if raw.isdigit():
            e.control.value = f"{int(raw):,}"
            e.control.update()
        recalc_margin()
        txt_margin.update()

    txt_buy_price.on_change = format_currency
    txt_sell_price.on_change = format_currency

    def chain(src, dst):
        src.on_submit = lambda e: dst.focus()

    chain(txt_item_name, txt_buy_price)
    chain(txt_buy_price, txt_sell_price)
    chain(txt_sell_price, txt_settlement)
    chain(txt_settlement, txt_qty)
    chain(txt_qty, txt_date)
    chain(txt_date, txt_desc)

    editing = {"id": None, "company_id": None}

    def clear_item_fields():
        for c in (txt_item_name, txt_buy_price, txt_sell_price, txt_margin,
                  txt_settlement, txt_qty, txt_desc):
            c.value = ""
        txt_date.value = today_shamsi
        editing["id"] = None
        editing["company_id"] = None
        item_dialog.title.value = "ثبت کالای جدید"

    def save_item(e):
        try:
            company_id = editing["company_id"] or company_dropdown.value
            if not company_id:
                show_message("لطفا ابتدا یک شرکت را انتخاب کنید!")
                return
            item = (txt_item_name.value or "").strip()
            if not item:
                show_message("نام کالا الزامی است!")
                return
            qty = to_number(txt_qty.value)
            if qty is None or qty <= 0:
                show_message("تعداد سفارش باید عدد بزرگ تر از صفر باشد!")
                return
            buy = to_number(txt_buy_price.value)
            sell = to_number(txt_sell_price.value)
            settlement = to_number(txt_settlement.value)
            if (txt_buy_price.value or "").strip() and buy is None:
                show_message("قیمت خرید نامعتبر است!")
                return
            if (txt_sell_price.value or "").strip() and sell is None:
                show_message("قیمت مصرف نامعتبر است!")
                return
            if (txt_settlement.value or "").strip() and settlement is None:
                show_message("مدت تسویه باید عدد معتبر باشد!")
                return

            record = {
                "id": editing["id"] or str(uuid.uuid4()),
                "company_id": company_id,
                "item": item,
                "buy_price": buy,
                "sell_price": sell,
                "margin": txt_margin.value,
                "settlement": f"{int(settlement)}" if settlement is not None else "",
                "qty": qty,
                "date": (txt_date.value or "").strip() or today_shamsi,
                "desc": (txt_desc.value or "").strip(),
            }
            if editing["id"]:
                for i, o in enumerate(orders):
                    if o["id"] == editing["id"]:
                        orders[i] = record
                        break
            else:
                orders.append(record)
            save_data()
            clear_item_fields()
            close_dialog(item_dialog)
            refresh_orders_list()
            show_message("سفارش با موفقیت ثبت شد.", error=False)
        except Exception:
            show_message(f"خطا: {traceback.format_exc()[-200:]}")

    item_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("ثبت کالای جدید", size=22, weight=ft.FontWeight.BOLD, color=Colors.TEAL_800),
        content=ft.Column(
            [txt_item_name, txt_buy_price, txt_sell_price, txt_margin,
             txt_settlement, txt_qty, txt_date, txt_desc],
            scroll=ft.ScrollMode.AUTO, height=470, tight=True, width=400,
        ),
        actions=[
            ft.ElevatedButton("ثبت کالا", on_click=save_item,
                              bgcolor=Colors.GREEN_600, color="white"),
            ft.TextButton("انصراف", on_click=lambda e: close_dialog(item_dialog)),
        ],
    )
    page.overlay.append(item_dialog)

    def open_add_item(e):
        if not company_dropdown.value:
            show_message("لطفا ابتدا یک شرکت را انتخاب کنید!")
            return
        clear_item_fields()
        item_dialog.open = True
        page.update()
        txt_item_name.focus()

    def open_edit_item(o):
        editing["id"] = o["id"]
        editing["company_id"] = o.get("company_id")   # قفل بودن شرکت هنگام ویرایش
        item_dialog.title.value = "ویرایش کالا"
        txt_item_name.value = o.get("item", "")
        txt_buy_price.value = money(o.get("buy_price"))
        txt_sell_price.value = money(o.get("sell_price"))
        recalc_margin()
        txt_margin.value = o.get("margin", "")
        txt_settlement.value = str(o.get("settlement") or "")
        txt_qty.value = qty_text(o.get("qty"))
        txt_date.value = o.get("date", today_shamsi)
        txt_desc.value = o.get("desc", "")
        item_dialog.open = True
        page.update()

    # ---------------- 5. فرم شرکت ----------------
    txt_comp_name = ft.TextField(label="نام شرکت", **field_style)
    txt_visitor   = ft.TextField(label="نام ویزیتور", **field_style)
    txt_phone     = ft.TextField(label="شماره تلفن", keyboard_type=ft.KeyboardType.PHONE, **field_style)

    def get_company(cid):
        for c in companies:
            if c["id"] == cid:
                return c
        return None

    def rebuild_dropdown(select_id=None):
        company_dropdown.options = [option(c["id"], c["name"]) for c in companies]
        ids = [c["id"] for c in companies]
        if select_id and select_id in ids:
            company_dropdown.value = select_id
        elif company_dropdown.value not in ids:
            company_dropdown.value = None

    def save_company(e):
        try:
            name = (txt_comp_name.value or "").strip()
            if not name:
                show_message("نام شرکت الزامی است!")
                return
            if any(c["name"] == name for c in companies):
                show_message("این شرکت قبلا ثبت شده است!")
                return
            comp = {"id": str(uuid.uuid4()), "name": name,
                    "visitor": (txt_visitor.value or "").strip(),
                    "phone": normalize_digits(txt_phone.value or "").strip()}
            companies.append(comp)
            rebuild_dropdown(select_id=comp["id"])
            save_data()
            txt_comp_name.value = txt_visitor.value = txt_phone.value = ""
            close_dialog(comp_dialog)
            refresh_orders_list()
            show_message(f"شرکت «{name}» ثبت شد.", error=False)
        except Exception:
            show_message(f"خطا: {traceback.format_exc()[-200:]}")

    comp_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("افزودن شرکت تامین کننده", size=22,
                      weight=ft.FontWeight.BOLD, color=Colors.TEAL_800),
        content=ft.Column([txt_comp_name, txt_visitor, txt_phone], height=250, tight=True, width=400),
        actions=[
            ft.ElevatedButton("ثبت شرکت", on_click=save_company,
                              bgcolor=Colors.TEAL_600, color="white"),
            ft.TextButton("انصراف", on_click=lambda e: close_dialog(comp_dialog)),
        ],
    )
    page.overlay.append(comp_dialog)

    def delete_company(e):
        cid = company_dropdown.value
        comp = get_company(cid) if cid else None
        if not comp:
            show_message("ابتدا یک شرکت را انتخاب کنید!")
            return
        def do_delete():
            companies.remove(comp)
            orders[:] = [o for o in orders if o.get("company_id") != cid]
            rebuild_dropdown()
            save_data()
            refresh_orders_list()
        n = sum(1 for o in orders if o.get("company_id") == cid)
        ask_confirm("حذف شرکت",
                    f'آیا از حذف شرکت «{comp["name"]}» و {n} سفارش آن مطمئن هستید؟',
                    do_delete)

    # ---------------- 6. دراپ داون و لیست سفارشات ----------------
    company_dropdown = ft.Dropdown(
        label="انتخاب شرکت", width=250, border_radius=10, filled=True,
        fill_color=Colors.WHITE, text_size=18,
        on_change=lambda e: refresh_orders_list(),
    )

    search_box = ft.TextField(
        label="جستجو در سفارشات...", prefix_icon=Icons.SEARCH,
        border_radius=10, filled=True, fill_color=Colors.WHITE, text_size=16,
        width=240, on_change=lambda e: refresh_orders_list(),
    )

    orders_list = ft.ListView(expand=True, spacing=15, padding=10)
    orders_screenshot = ft.Screenshot(content=orders_list) if HAS_SCREENSHOT else orders_list

    empty_state = ft.Container(
        visible=False, alignment=ft.alignment.center,
        content=ft.Column([
            ft.Icon(Icons.INBOX_OUTLINED, size=70, color=Colors.GREY_400),
            ft.Text("سفارشی یافت نشد", size=18, color=Colors.GREY_500),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
    )

    totals_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD, color=Colors.TEAL_900)

    def delete_order(oid):
        def do_delete():
            orders[:] = [o for o in orders if o["id"] != oid]
            save_data()
            refresh_orders_list()
        ask_confirm("حذف سفارش", "آیا از حذف این سفارش مطمئن هستید؟", do_delete)

    def build_card(o):
        parts = [f"تاریخ تحویل: {o.get('date', '')}"]
        if o.get("buy_price"):
            parts.append(f"خرید: {format_price(o['buy_price'])}")
        if o.get("sell_price"):
            parts.append(f"فروش: {format_price(o['sell_price'])}")
        if o.get("margin"):
            parts.append(f"سود: {o['margin']}٪")
        if o.get("settlement"):
            parts.append(f"تسویه: {o['settlement']} روز")
        subtitle = "  |  ".join(parts)
        if o.get("desc"):
            subtitle += f"\n{o['desc']}"
        return ft.Card(
            elevation=3, surface_tint_color=Colors.WHITE,
            content=ft.Container(
                padding=15,
                content=ft.ListTile(
                    leading=ft.Icon(Icons.LOCAL_SHIPPING, color=Colors.TEAL_500, size=35),
                    title=ft.Text(f"{o.get('item', '')} - {qty_text(o.get('qty'))} کارتن",
                                  size=20, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(subtitle, size=15, color=Colors.GREY_700),
                    trailing=ft.Row([
                        ft.IconButton(Icons.EDIT_OUTLINED, tooltip="ویرایش",
                                      icon_color=Colors.TEAL_700,
                                      on_click=lambda e, x=o: open_edit_item(x)),
                        ft.IconButton(Icons.DELETE_OUTLINE, tooltip="حذف",
                                      icon_color=Colors.RED_500,
                                      on_click=lambda e, oid=o["id"]: delete_order(oid)),
                    ], tight=True),
                ),
            ),
        )

    def refresh_orders_list():
        orders_list.controls.clear()
        selected = company_dropdown.value
        query = normalize_digits(search_box.value or "").strip().lower()
        shown, total_qty = 0, 0.0
        for o in orders:
            if o.get("company_id") != selected:
                continue
            if query and query not in (o.get("item") or "").lower() \
                     and query not in (o.get("desc") or "").lower():
                continue
            shown += 1
            total_qty += to_number(str(o.get("qty"))) or 0
            orders_list.controls.append(build_card(o))
        empty_state.visible = shown == 0
        totals_text.value = f"تعداد اقلام: {shown}    |    مجموع: {total_qty:g} کارتن"
        page.update()

    # ---------------- 7. اسکرین شات از لیست ----------------
    async def take_list_screenshot(e):
        if not HAS_SCREENSHOT:
            show_message("این قابلیت نیاز به بروزرسانی flet دارد (pip install -U flet)")
            return
        if not orders_list.controls:
            show_message("سفارشی برای عکس گرفتن وجود ندارد!")
            return
        try:
            # موقتا ارتفاع لیست را به اندازه کل محتوا می بریم تا همه کارت ها رندر شوند
            old_height = orders_list.height
            orders_list.height = max(len(orders_list.controls) * 195 + 40, 300)
            orders_list.update()
            await asyncio.sleep(0.4)          # فرصت رندر یک فریم
            image_bytes = await orders_screenshot.capture()
            orders_list.height = old_height
            orders_list.update()
            base = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
            folder = os.path.join(base, "screenshots")
            os.makedirs(folder, exist_ok=True)
            fname = f"orders_{jdatetime.date.today().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}.png"
            path = os.path.join(folder, fname)
            with open(path, "wb") as f:
                f.write(image_bytes)
            show_message(f"عکس ذخیره شد:\n{path}", error=False)
        except Exception:
            orders_list.height = None
            show_message(f"خطا در گرفتن عکس: {traceback.format_exc()[-200:]}")

    # ---------------- 8. چیدمان صفحه ----------------
    page.add(
        ft.Container(height=8),
        ft.Row([
            company_dropdown,
            ft.IconButton(Icons.ADD_BUSINESS, on_click=lambda e: open_dialog(comp_dialog),
                          tooltip="افزودن شرکت", icon_size=32, icon_color=Colors.TEAL_700),
            ft.IconButton(Icons.DELETE_FOREVER_OUTLINED, on_click=delete_company,
                          tooltip="حذف شرکت", icon_size=32, icon_color=Colors.RED_400),
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=8),
        ft.Row([
            ft.ElevatedButton("ثبت کالای جدید", on_click=open_add_item, icon=Icons.ADD_SHOPPING_CART,
                              width=250, height=55, bgcolor=Colors.ORANGE_600, color="white", elevation=5),
            ft.IconButton(Icons.CAMERA_ALT_OUTLINED, on_click=take_list_screenshot,
                          tooltip="گرفتن عکس از لیست", icon_size=32, icon_color=Colors.TEAL_700),
            search_box,
        ], alignment=ft.MainAxisAlignment.CENTER, wrap=True, spacing=12),
        ft.Divider(height=25, color=Colors.GREY_300),
        ft.Row([
            ft.Icon(Icons.LIST_ALT, color=Colors.TEAL_800),
            ft.Text("لیست سفارشات ثبت شده:", size=20,
                    weight=ft.FontWeight.BOLD, color=Colors.TEAL_800),
            ft.Container(expand=True),
            totals_text,
        ]),
        ft.Stack([
            ft.Container(content=orders_screenshot, expand=True),
            empty_state,
        ], expand=True),
    )

    def open_dialog(dlg):
        dlg.open = True
        page.update()

    rebuild_dropdown()
    refresh_orders_list()


ft.app(target=main)
