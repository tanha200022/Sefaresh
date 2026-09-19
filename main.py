import flet as ft
import jdatetime
import traceback
import uuid
import os

global_error = ""
try:
    import jdatetime
except Exception as e:
    global_error = traceback.format_exc()


def main(page: ft.Page):
    if global_error != "":
        page.add(ft.Text(f"خطای راه‌اندازی:\n{global_error}", color="red", rtl=False))
        return

    try:
        # --- ۱. تنظیمات حرفه‌ای ظاهر برنامه ---
        page.title = "سفارشات انصاری"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = ft.colors.BLUE_GREY_50
        page.rtl = True
        page.theme = ft.Theme(
            text_theme=ft.TextTheme(body_medium=ft.TextStyle(size=18)),
            color_scheme_seed=ft.colors.TEAL
        )

        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.icons.SHOPPING_CART_CHECKOUT, color="white"),
            title=ft.Text("هایپر گوشت انصاری", color="white", weight=ft.FontWeight.BOLD, size=22),
            bgcolor=ft.colors.TEAL_700,
            center_title=True,
            elevation=4
        )

        # --- پیام‌های زیرصفحه (یک نمونهٔ ثابت، نه ساخت مجدد هر بار) ---
        snack_text = ft.Text("", size=16)
        snack_bar = ft.SnackBar(content=snack_text)
        page.overlay.append(snack_bar)

        def show_message(text, is_error=True):
            snack_text.value = text
            snack_bar.bgcolor = ft.colors.RED_600 if is_error else ft.colors.GREEN_600
            snack_bar.open = True
            page.update()

        # --- دیالوگ تأیید عمومی (یک نمونهٔ ثابت برای همهٔ حذف‌ها) ---
        confirm_title = ft.Text("")
        confirm_content = ft.Text("")

        def confirm_yes(e):
            confirm_dialog.open = False
            page.update()
            action = confirm_pending["action"]
            if action:
                action()

        def confirm_no(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=confirm_title,
            content=confirm_content,
            actions=[
                ft.TextButton("حذف", on_click=confirm_yes),
                ft.TextButton("انصراف", on_click=confirm_no),
            ]
        )
        page.overlay.append(confirm_dialog)
        confirm_pending = {"action": None}

        def ask_confirm(title, message, action):
            confirm_title.value = title
            confirm_content.value = message
            confirm_pending["action"] = action
            confirm_dialog.open = True
            page.update()

        # --- ۲. سیستم ذخیره‌سازی محلی ---
        companies = page.client_storage.get("companies") or []
        orders = page.client_storage.get("orders") or []

        def save_data():
            page.client_storage.set("companies", companies)
            page.client_storage.set("orders", orders)

        def migrate_data():
            """سازگاری با داده‌های ذخیره‌شده از نسخهٔ قدیمی برنامه (شرکت=رشته، سفارش بدون id/company_id)."""
            changed = False
            name_to_id = {}

            if companies and isinstance(companies[0], str):
                old_names = list(companies)
                companies.clear()
                for name in old_names:
                    cid = str(uuid.uuid4())
                    companies.append({"id": cid, "name": name, "visitor": "", "phone": ""})
                    name_to_id[name] = cid
                changed = True
            else:
                name_to_id = {c["name"]: c["id"] for c in companies if isinstance(c, dict) and "id" in c}

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
                for k, default in [("buy_price", None), ("sell_price", None), ("margin", ""), ("settlement", ""), ("desc", "")]:
                    if k not in o:
                        o[k] = default
                        changed = True

            if changed:
                save_data()

        migrate_data()

        # --- توابع کمکی ---
        def to_number(value):
            if value is None:
                return None
            cleaned = value.replace(",", "").strip()
            if cleaned == "":
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None

        def format_currency(e):
            value = e.control.value.replace(",", "")
            if value.isdigit():
                e.control.value = f"{int(value):,}"
                e.control.update()
            calculate_margin(e)

        def calculate_margin(e):
            buy = to_number(txt_buy_price.value)
            sell = to_number(txt_sell_price.value)
            if buy and buy > 0 and sell is not None:
                margin = ((sell - buy) / buy) * 100
                txt_margin.value = f"{margin:.1f}"
            else:
                txt_margin.value = ""
            txt_margin.update()

        def move_focus(e, next_control):
            next_control.focus()

        today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")

        field_style = {"border_radius": 10, "filled": True, "fill_color": ft.colors.WHITE, "text_size": 18}

        # --- فرم افزودن کالا/سفارش ---
        txt_item_name = ft.TextField(label="نام کالا", **field_style)
        txt_buy_price = ft.TextField(label="قیمت خرید", on_change=format_currency, keyboard_type=ft.KeyboardType.NUMBER, **field_style)
        txt_sell_price = ft.TextField(label="قیمت مصرف", on_change=format_currency, keyboard_type=ft.KeyboardType.NUMBER, **field_style)
        txt_margin = ft.TextField(label="حاشیه سود (%)", read_only=True, **field_style)
        txt_settlement = ft.TextField(label="مدت تسویه (روز)", keyboard_type=ft.KeyboardType.NUMBER, **field_style)
        txt_qty = ft.TextField(label="تعداد سفارش (کارتن)", keyboard_type=ft.KeyboardType.NUMBER, **field_style)
        txt_date = ft.TextField(label="تاریخ تحویل", value=today_shamsi, **field_style)
        txt_desc = ft.TextField(label="توضیحات", multiline=True, min_lines=2, max_lines=4, **field_style)

        txt_item_name.on_submit = lambda e: move_focus(e, txt_buy_price)
        txt_buy_price.on_submit = lambda e: move_focus(e, txt_sell_price)
        txt_sell_price.on_submit = lambda e: move_focus(e, txt_settlement)
        txt_settlement.on_submit = lambda e: move_focus(e, txt_qty)
        txt_qty.on_submit = lambda e: move_focus(e, txt_date)
        txt_date.on_submit = lambda e: move_focus(e, txt_desc)

        editing_order_id = {"value": None}

        def close_item_dlg(e=None):
            item_dialog.open = False
            page.update()

        def clear_item_fields():
            txt_item_name.value = ""
            txt_buy_price.value = ""
            txt_sell_price.value = ""
            txt_margin.value = ""
            txt_settlement.value = ""
            txt_qty.value = ""
            txt_date.value = today_shamsi
            txt_desc.value = ""
            editing_order_id["value"] = None
            item_dialog.title.value = "ثبت کالای جدید"

        def save_item(e):
            try:
                company_id = company_dropdown.value
                if not company_id:
                    show_message("لطفاً ابتدا یک شرکت را انتخاب کنید!")
                    return
                if not txt_item_name.value or not txt_item_name.value.strip():
                    show_message("نام کالا الزامی است!")
                    return
                if not txt_qty.value or to_number(txt_qty.value) is None:
                    show_message("تعداد سفارش باید عدد معتبر باشد!")
                    return

                buy_price = to_number(txt_buy_price.value)
                sell_price = to_number(txt_sell_price.value)
                if txt_buy_price.value.strip() and buy_price is None:
                    show_message("قیمت خرید نامعتبر است!")
                    return
                if txt_sell_price.value.strip() and sell_price is None:
                    show_message("قیمت مصرف نامعتبر است!")
                    return

                record = {
                    "id": editing_order_id["value"] or str(uuid.uuid4()),
                    "company_id": company_id,
                    "item": txt_item_name.value.strip(),
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "margin": txt_margin.value,
                    "settlement": txt_settlement.value.strip(),
                    "qty": txt_qty.value.strip(),
                    "date": txt_date.value.strip() or today_shamsi,
                    "desc": txt_desc.value.strip(),
                }

                if editing_order_id["value"]:
                    for i, o in enumerate(orders):
                        if o["id"] == editing_order_id["value"]:
                            orders[i] = record
                            break
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
            title=ft.Text("ثبت کالای جدید", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.TEAL_800),
            content=ft.Column([
                txt_item_name, txt_buy_price, txt_sell_price, txt_margin,
                txt_settlement, txt_qty, txt_date, txt_desc
            ], scroll=ft.ScrollMode.AUTO, height=470, tight=True),
            actions=[
                ft.ElevatedButton("ثبت کالا", on_click=save_item, bgcolor=ft.colors.GREEN_600, color="white"),
                ft.TextButton("انصراف", on_click=close_item_dlg)
            ]
        )
        page.overlay.append(item_dialog)

        def open_add_item(e):
            if not company_dropdown.value:
                show_message("لطفاً ابتدا یک شرکت را انتخاب کنید!")
                return
            clear_item_fields()
            item_dialog.open = True
            page.update()
            txt_item_name.focus()

        def open_edit_item(order):
            editing_order_id["value"] = order["id"]
            item_dialog.title.value = "ویرایش کالا"
            txt_item_name.value = order["item"]
            txt_buy_price.value = f'{int(order["buy_price"]):,}' if order["buy_price"] else ""
            txt_sell_price.value = f'{int(order["sell_price"]):,}' if order["sell_price"] else ""
            txt_margin.value = order.get("margin", "")
            txt_settlement.value = order.get("settlement", "")
            txt_qty.value = order["qty"]
            txt_date.value = order["date"]
            txt_desc.value = order.get("desc", "")
            item_dialog.open = True
            page.update()

        # --- فرم افزودن شرکت ---
        txt_comp_name = ft.TextField(label="نام شرکت", **field_style)
        txt_visitor = ft.TextField(label="نام ویزیتور", **field_style)
        txt_phone = ft.TextField(label="شماره تلفن", keyboard_type=ft.KeyboardType.PHONE, **field_style)

        def close_comp_dlg(e=None):
            comp_dialog.open = False
            page.update()

        def get_company(company_id):
            for c in companies:
                if c["id"] == company_id:
                    return c
            return None

        def save_company(e):
            try:
                name = txt_comp_name.value.strip() if txt_comp_name.value else ""
                if not name:
                    show_message("نام شرکت الزامی است!")
                    return
                if any(c["name"] == name for c in companies):
                    show_message("این شرکت قبلاً ثبت شده است!")
                    return

                new_comp = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "visitor": txt_visitor.value.strip() if txt_visitor.value else "",
                    "phone": txt_phone.value.strip() if txt_phone.value else "",
                }
                companies.append(new_comp)
                company_dropdown.options.append(ft.dropdown.Option(key=new_comp["id"], text=new_comp["name"]))
                company_dropdown.value = new_comp["id"]
                save_data()

                txt_comp_name.value = ""
                txt_visitor.value = ""
                txt_phone.value = ""
                close_comp_dlg()
                refresh_orders_list()
            except Exception:
                show_message(f"خطا: {traceback.format_exc()[-200:]}")

        comp_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("افزودن شرکت تأمین‌کننده", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.TEAL_800),
            content=ft.Column([txt_comp_name, txt_visitor, txt_phone], height=250, tight=True),
            actions=[
                ft.ElevatedButton("ثبت شرکت", on_click=save_company, bgcolor=ft.colors.TEAL_600, color="white"),
                ft.TextButton("انصراف", on_click=close_comp_dlg)
            ]
        )
        page.overlay.append(comp_dialog)

        def open_add_company(e):
            comp_dialog.open = True
            page.update()

        def delete_company(e):
            company_id = company_dropdown.value
            if not company_id:
                return
            company = get_company(company_id)
            if not company:
                return

            def do_delete():
                companies.remove(company)
                orders[:] = [o for o in orders if o["company_id"] != company_id]
                company_dropdown.options = [ft.dropdown.Option(key=c["id"], text=c["name"]) for c in companies]
                company_dropdown.value = None
                save_data()
                refresh_orders_list()

            ask_confirm(
                "حذف شرکت",
                f'آیا از حذف شرکت "{company["name"]}" و تمام سفارشات آن مطمئن هستید؟',
                do_delete
            )

        dropdown_opts = [ft.dropdown.Option(key=c["id"], text=c["name"]) for c in companies]
        company_dropdown = ft.Dropdown(
            label="انتخاب شرکت",
            options=dropdown_opts,
            width=240,
            border_radius=10,
            filled=True,
            fill_color=ft.colors.WHITE,
            text_size=18,
            on_change=lambda e: refresh_orders_list()
        )

        orders_list = ft.ListView(expand=True, spacing=15, padding=10)

        def delete_order(order_id):
            def do_delete():
                orders[:] = [o for o in orders if o["id"] != order_id]
                save_data()
                refresh_orders_list()

            ask_confirm("حذف سفارش", "آیا از حذف این سفارش مطمئن هستید؟", do_delete)

        def format_price(value):
            return f"{int(value):,} تومان" if value else "—"

        def refresh_orders_list():
            orders_list.controls.clear()
            selected_company = company_dropdown.value
            for ord in orders:
                if ord["company_id"] != selected_company:
                    continue

                subtitle_parts = [f"تاریخ تحویل: {ord['date']}"]
                if ord.get("buy_price"):
                    subtitle_parts.append(f"خرید: {format_price(ord['buy_price'])}")
                if ord.get("sell_price"):
                    subtitle_parts.append(f"فروش: {format_price(ord['sell_price'])}")
                if ord.get("margin"):
                    subtitle_parts.append(f"سود: {ord['margin']}٪")
                if ord.get("settlement"):
                    subtitle_parts.append(f"تسویه: {ord['settlement']} روز")

                subtitle_text = "  |  ".join(subtitle_parts)
                if ord.get("desc"):
                    subtitle_text += f"\n{ord['desc']}"

                orders_list.controls.append(
                    ft.Card(
                        elevation=3,
                        surface_tint_color=ft.colors.WHITE,
                        content=ft.Container(
                            padding=15,
                            content=ft.ListTile(
                                leading=ft.Icon(ft.icons.LOCAL_SHIPPING, color=ft.colors.TEAL_500, size=35),
                                title=ft.Text(f"{ord['item']} - {ord['qty']} کارتن", size=20, weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(subtitle_text, size=15, color=ft.colors.GREY_700),
                                trailing=ft.Row([
                                    ft.IconButton(ft.icons.EDIT_OUTLINED, tooltip="ویرایش", icon_color=ft.colors.TEAL_700, on_click=lambda e, o=ord: open_edit_item(o)),
                                    ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="حذف", icon_color=ft.colors.RED_500, on_click=lambda e, oid=ord["id"]: delete_order(oid)),
                                ], tight=True)
                            )
                        )
                    )
                )
            page.update()

        # --- گرفتن عکس از لیست سفارشات ---
        has_screenshot = hasattr(ft, "Screenshot")
        orders_screenshot = ft.Screenshot(content=orders_list) if has_screenshot else orders_list

        async def take_list_screenshot(e):
            if not has_screenshot:
                show_message("این قابلیت نیاز به بروزرسانی کتابخانه flet دارد (pip install --upgrade flet)")
                return
            if not orders_list.controls:
                show_message("سفارشی برای عکس گرفتن وجود ندارد!")
                return
            try:
                image_bytes = await orders_screenshot.capture()
                folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
                os.makedirs(folder, exist_ok=True)
                filename = f"orders_{jdatetime.date.today().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}.png"
                full_path = os.path.join(folder, filename)
                with open(full_path, "wb") as f:
                    f.write(image_bytes)
                show_message(f"عکس ذخیره شد: {full_path}", is_error=False)
            except Exception:
                show_message(f"خطا در گرفتن عکس: {traceback.format_exc()[-200:]}")

        page.add(
            ft.Container(height=10),
            ft.Row(
                [
                    company_dropdown,
                    ft.IconButton(ft.icons.ADD_BUSINESS, on_click=open_add_company, tooltip="افزودن شرکت", icon_size=32, icon_color=ft.colors.TEAL_700),
                    ft.IconButton(ft.icons.DELETE_FOREVER_OUTLINED, on_click=delete_company, tooltip="حذف شرکت", icon_size=32, icon_color=ft.colors.RED_400),
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton("ثبت کالای جدید", on_click=open_add_item, icon=ft.icons.ADD_SHOPPING_CART, width=250, height=55, bgcolor=ft.colors.ORANGE_600, color="white", elevation=5),
                ft.IconButton(ft.icons.CAMERA_ALT_OUTLINED, on_click=take_list_screenshot, tooltip="گرفتن عکس از لیست", icon_size=32, icon_color=ft.colors.TEAL_700),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=30, color=ft.colors.GREY_300),
            ft.Row([
                ft.Icon(ft.icons.LIST_ALT, color=ft.colors.TEAL_800),
                ft.Text("لیست سفارشات ثبت شده:", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.TEAL_800)
            ]),
            orders_screenshot
        )

    except Exception as e:
        page.add(ft.Text(f"UI Error:\n{traceback.format_exc()}", color="red", rtl=False))
        page.update()


ft.app(target=main)
