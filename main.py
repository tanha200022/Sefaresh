import flet as ft
import jdatetime
import traceback

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
        page.bgcolor = ft.colors.BLUE_GREY_50 # پس‌زمینه ملایم و مدرن
        page.rtl = True
        page.theme = ft.Theme(
            text_theme=ft.TextTheme(body_medium=ft.TextStyle(size=18)),
            color_scheme_seed=ft.colors.TEAL # تم رنگی سازمانی
        )
        
        # نوار بالای اپلیکیشن (AppBar)
        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.icons.SHOPPING_CART_CHECKOUT, color="white"),
            title=ft.Text("هایپر گوشت انصاری", color="white", weight=ft.FontWeight.BOLD, size=22),
            bgcolor=ft.colors.TEAL_700,
            center_title=True,
            elevation=4
        )

        # --- ۲. سیستم ذخیره‌سازی محلی (جلوگیری از پاک شدن اطلاعات) ---
        companies = page.client_storage.get("companies") or []
        orders = page.client_storage.get("orders") or []

        def save_data():
            page.client_storage.set("companies", companies)
            page.client_storage.set("orders", orders)

        # --- توابع محاسباتی ---
        def format_currency(e):
            value = e.control.value.replace(",", "")
            if value.isdigit():
                e.control.value = f"{int(value):,}"
                e.control.update()
                calculate_margin(e)

        def calculate_margin(e):
            try:
                buy = float(txt_buy_price.value.replace(",", ""))
                sell = float(txt_sell_price.value.replace(",", ""))
                if buy > 0:
                    margin = ((sell - buy) / buy) * 100
                    txt_margin.value = f"{margin:.1f}"
                    txt_margin.update()
            except ValueError:
                pass

        def move_focus(e, next_control):
            next_control.focus()

        today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")
        
        # استایل مشترک کادرهای متنی برای زیبایی بیشتر
        field_style = {"border_radius": 10, "filled": True, "fill_color": ft.colors.WHITE, "text_size": 18}

        txt_item_name = ft.TextField(label="نام کالا", on_submit=lambda e: move_focus(e, txt_buy_price), **field_style)
        txt_buy_price = ft.TextField(label="قیمت خرید", on_change=format_currency, on_submit=lambda e: move_focus(e, txt_sell_price), **field_style)
        txt_sell_price = ft.TextField(label="قیمت مصرف", on_change=format_currency, on_submit=lambda e: move_focus(e, txt_settlement), **field_style)
        txt_margin = ft.TextField(label="حاشیه سود (%)", read_only=True, **field_style)
        txt_settlement = ft.TextField(label="مدت تسویه (روز)", on_submit=lambda e: move_focus(e, txt_qty), **field_style)
        txt_qty = ft.TextField(label="تعداد سفارش (کارتن)", on_submit=lambda e: move_focus(e, txt_date), **field_style)
        txt_date = ft.TextField(label="تاریخ تحویل", value=today_shamsi, on_submit=lambda e: move_focus(e, txt_desc), **field_style)
        txt_desc = ft.TextField(label="توضیحات", multiline=True, **field_style)

        def close_item_dlg(e):
            item_dialog.open = False
            page.update()

        def clear_item_fields():
            txt_item_name.value = ""
            txt_buy_price.value = ""
            txt_sell_price.value = ""
            txt_margin.value = ""
            txt_settlement.value = ""
            txt_qty.value = ""
            txt_desc.value = ""

        def save_item(e):
            company = company_dropdown.value
            if txt_item_name.value and txt_qty.value and company:
                orders.append({
                    "company": company, 
                    "item": txt_item_name.value, 
                    "qty": txt_qty.value, 
                    "date": txt_date.value
                })
                save_data() # ذخیره در حافظه گوشی
                clear_item_fields()
                close_item_dlg(e)
                refresh_orders_list()

        item_dialog = ft.AlertDialog(
            title=ft.Text("ثبت کالای جدید", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.TEAL_800),
            content=ft.Column([
                txt_item_name, txt_buy_price, txt_sell_price, txt_margin, 
                txt_settlement, txt_qty, txt_date, txt_desc
            ], scroll=ft.ScrollMode.AUTO, height=450),
            actions=[
                ft.ElevatedButton("ثبت کالا", on_click=save_item, bgcolor=ft.colors.GREEN_600, color="white"),
                ft.TextButton("انصراف", on_click=close_item_dlg)
            ]
        )

        def open_add_item(e):
            if not company_dropdown.value:
                page.snack_bar = ft.SnackBar(ft.Text("لطفاً ابتدا یک شرکت را انتخاب کنید!", size=16), bgcolor=ft.colors.RED_600)
                page.snack_bar.open = True
                page.update()
                return
            page.dialog = item_dialog
            item_dialog.open = True
            page.update()
            txt_item_name.focus()

        # فرم افزودن شرکت
        txt_comp_name = ft.TextField(label="نام شرکت", **field_style)
        txt_visitor = ft.TextField(label="نام ویزیتور", **field_style)
        txt_phone = ft.TextField(label="شماره تلفن", **field_style)

        def close_comp_dlg(e):
            comp_dialog.open = False
            page.update()

        def save_company(e):
            new_comp = txt_comp_name.value
            if new_comp:
                if new_comp not in companies:
                    companies.append(new_comp)
                    company_dropdown.options.append(ft.dropdown.Option(new_comp))
                company_dropdown.value = new_comp
                save_data() # ذخیره در حافظه
                txt_comp_name.value = ""
                txt_visitor.value = ""
                txt_phone.value = ""
                close_comp_dlg(e)
                refresh_orders_list()

        comp_dialog = ft.AlertDialog(
            title=ft.Text("افزودن شرکت تأمین‌کننده", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.TEAL_800),
            content=ft.Column([txt_comp_name, txt_visitor, txt_phone], height=250),
            actions=[
                ft.ElevatedButton("ثبت شرکت", on_click=save_company, bgcolor=ft.colors.TEAL_600, color="white"),
                ft.TextButton("انصراف", on_click=close_comp_dlg)
            ]
        )

        def open_add_company(e):
            page.dialog = comp_dialog
            comp_dialog.open = True
            page.update()

        # بازگردانی شرکت‌های ذخیره‌شده به منوی کشویی
        dropdown_opts = [ft.dropdown.Option(c) for c in companies]
        company_dropdown = ft.Dropdown(
            label="انتخاب شرکت",
            options=dropdown_opts,
            width=260,
            border_radius=10,
            filled=True,
            fill_color=ft.colors.WHITE,
            text_size=18
        )
        company_dropdown.on_change = lambda e: refresh_orders_list()

        orders_list = ft.ListView(expand=True, spacing=15, padding=10)

        def delete_order(order_to_delete):
            if order_to_delete in orders:
                orders.remove(order_to_delete)
                save_data()
                refresh_orders_list()

        def refresh_orders_list():
            orders_list.controls.clear()
            selected_company = company_dropdown.value
            for ord in orders:
                if ord['company'] == selected_company:
                    current_ord = ord
                    orders_list.controls.append(
                        ft.Card(
                            elevation=3, # ایجاد سایه برای زیبایی
                            surface_tint_color=ft.colors.WHITE,
                            content=ft.Container(
                                padding=15,
                                content=ft.ListTile(
                                    leading=ft.Icon(ft.icons.LOCAL_SHIPPING, color=ft.colors.TEAL_500, size=35),
                                    title=ft.Text(f"{current_ord['item']} - {current_ord['qty']} کارتن", size=20, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text(f"تاریخ تحویل: {current_ord['date']}", size=16, color=ft.colors.GREY_700),
                                    trailing=ft.Row([
                                        ft.IconButton(ft.icons.DELETE_OUTLINE, tooltip="حذف", icon_color=ft.colors.RED_500, on_click=lambda e, o=current_ord: delete_order(o))
                                    ], tight=True)
                                )
                            )
                        )
                    )
            page.update()

        # چیدمان نهایی صفحه اصلی
        page.add(
            ft.Container(height=10), # فاصله از بالا
            ft.Row(
                [company_dropdown, ft.IconButton(ft.icons.ADD_BUSINESS, on_click=open_add_company, tooltip="افزودن شرکت", icon_size=35, icon_color=ft.colors.TEAL_700)], 
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton("ثبت کالای جدید", on_click=open_add_item, icon=ft.icons.ADD_SHOPPING_CART, width=320, height=55, bgcolor=ft.colors.ORANGE_600, color="white", elevation=5)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=30, color=ft.colors.GREY_300),
            ft.Row([
                ft.Icon(ft.icons.LIST_ALT, color=ft.colors.TEAL_800),
                ft.Text("لیست سفارشات ثبت شده:", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.TEAL_800)
            ]),
            orders_list
        )

    except Exception as e:
        page.add(ft.Text(f"UI Error:\n{traceback.format_exc()}", color="red", rtl=False))
        page.update()

ft.app(target=main)
