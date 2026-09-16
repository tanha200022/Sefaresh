import flet as ft
import jdatetime

def main(page: ft.Page):
    page.title = "مدیریت سفارشات"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 700
    page.theme = ft.Theme(text_theme=ft.TextTheme(body_medium=ft.TextStyle(size=20)))
    page.rtl = True

    companies = [] 
    orders = [] 

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
    
    txt_item_name = ft.TextField(label="نام کالا (مانند کاکائو، گوشت...)", text_size=20, on_submit=lambda e: move_focus(e, txt_buy_price))
    txt_buy_price = ft.TextField(label="قیمت خرید", text_size=20, on_change=format_currency, on_submit=lambda e: move_focus(e, txt_sell_price))
    txt_sell_price = ft.TextField(label="قیمت مصرف", text_size=20, on_change=format_currency, on_submit=lambda e: move_focus(e, txt_settlement))
    txt_margin = ft.TextField(label="حاشیه سود (%)", text_size=20, read_only=True)
    txt_settlement = ft.TextField(label="مدت تسویه (روز)", text_size=20, on_submit=lambda e: move_focus(e, txt_qty))
    txt_qty = ft.TextField(label="تعداد سفارش (کارتن)", text_size=20, on_submit=lambda e: move_focus(e, txt_date))
    txt_date = ft.TextField(label="تاریخ تحویل", value=today_shamsi, text_size=20, on_submit=lambda e: move_focus(e, txt_desc))
    txt_desc = ft.TextField(label="توضیحات", text_size=20, multiline=True)

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
        if txt_item_name.value and txt_qty.value:
            orders.append({
                "company": company, 
                "item": txt_item_name.value, 
                "qty": txt_qty.value, 
                "date": txt_date.value
            })
            clear_item_fields()
            close_item_dlg(e)
            refresh_orders_list()

    item_dialog = ft.AlertDialog(
        title=ft.Text("ثبت کالای جدید", size=22, weight=ft.FontWeight.BOLD),
        content=ft.Column([
            txt_item_name, txt_buy_price, txt_sell_price, txt_margin, 
            txt_settlement, txt_qty, txt_date, txt_desc
        ], scroll=ft.ScrollMode.AUTO, height=450),
        actions=[
            ft.TextButton("ثبت کالا", on_click=save_item),
            ft.TextButton("انصراف", on_click=close_item_dlg)
        ]
    )

    def open_add_item(e):
        if not company_dropdown.value:
            page.snack_bar = ft.SnackBar(ft.Text("ابتدا یک شرکت را انتخاب کنید!", size=20))
            page.snack_bar.open = True
            page.update()
            return
        page.dialog = item_dialog
        item_dialog.open = True
        page.update()
        txt_item_name.focus()

    txt_comp_name = ft.TextField(label="نام شرکت", text_size=20)
    txt_visitor = ft.TextField(label="نام ویزیتور", text_size=20)
    txt_phone = ft.TextField(label="شماره تلفن", text_size=20)

    def close_comp_dlg(e):
        comp_dialog.open = False
        page.update()

    def save_company(e):
        new_comp = txt_comp_name.value
        if new_comp:
            companies.append(new_comp)
            company_dropdown.options.append(ft.dropdown.Option(new_comp))
            company_dropdown.value = new_comp
            txt_comp_name.value = ""
            txt_visitor.value = ""
            txt_phone.value = ""
            close_comp_dlg(e)
            refresh_orders_list()

    comp_dialog = ft.AlertDialog(
        title=ft.Text("افزودن شرکت جدید", size=22, weight=ft.FontWeight.BOLD),
        content=ft.Column([txt_comp_name, txt_visitor, txt_phone], height=250),
        actions=[
            ft.TextButton("ثبت شرکت", on_click=save_company),
            ft.TextButton("انصراف", on_click=close_comp_dlg)
        ]
    )

    def open_add_company(e):
        page.dialog = comp_dialog
        comp_dialog.open = True
        page.update()

    company_dropdown = ft.Dropdown(
        label="انتخاب شرکت",
        options=[],
        width=250,
        text_size=20
    )
    company_dropdown.on_change = lambda e: refresh_orders_list()

    orders_list = ft.ListView(expand=True, spacing=10)

    def delete_order(order_to_delete):
        if order_to_delete in orders:
            orders.remove(order_to_delete)
            refresh_orders_list()

    def refresh_orders_list():
        orders_list.controls.clear()
        selected_company = company_dropdown.value
        for ord in orders:
            if ord['company'] == selected_company:
                current_ord = ord
                orders_list.controls.append(
                    ft.Card(
                        content=ft.ListTile(
                            title=ft.Text(f"{current_ord['item']} - {current_ord['qty']} کارتن", size=20, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"تاریخ سفارش: {current_ord['date']}", size=16),
                            trailing=ft.Row([
                                ft.IconButton(ft.icons.EDIT, tooltip="ویرایش", icon_color="blue"),
                                ft.IconButton(ft.icons.DELETE, tooltip="حذف", icon_color="red", on_click=lambda e, o=current_ord: delete_order(o))
                            ], tight=True)
                        )
                    )
                )
        page.update()

    page.add(
        ft.Row([company_dropdown, ft.IconButton(ft.icons.ADD_BUSINESS, on_click=open_add_company, tooltip="افزودن شرکت", icon_size=30)], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.ElevatedButton("ثبت کالای جدید", on_click=open_add_item, icon=ft.icons.ADD_SHOPPING_CART, width=300, height=50, style=ft.ButtonStyle(text_style=ft.TextStyle(size=20))),
        ft.Divider(),
        ft.Text("لیست سفارشات این شرکت:", size=20, weight=ft.FontWeight.BOLD),
        orders_list
    )

ft.app(target=main)
