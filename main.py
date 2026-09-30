import flet as ft

def main(page: ft.Page):
    # تنظیمات اولیه صفحه
    page.title = "سفارش‌یار - ثبت شرکت"
    page.rtl = True  # راست‌چین کردن قالب برای زبان فارسی
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 700
    page.bgcolor = "#F7F9F7"  # رنگ پس‌زمینه روشن مشابه عکس

    # رنگ سازمانی
    DARK_GREEN = "#116040"

    # بخش هدر (دکمه بستن و عنوان)
    header = ft.Row(
        controls=[
            ft.IconButton(icon=ft.icons.CLOSE, icon_color=ft.colors.GREY_600, tooltip="بستن"),
            ft.Text("شرکت جدید", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK87),
            ft.Container(width=40)  # یک فضای خالی برای وسط‌چین ماندن عنوان
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    # زیرنویس راهنما
    subtitle = ft.Container(
        content=ft.Text(
            "یک‌بار ثبت کنید؛ همیشه در دسترس است.",
            color=ft.colors.GREY_500,
            size=13,
        ),
        alignment=ft.alignment.center,
        margin=ft.margin.only(bottom=25, top=10)
    )

    # تابع سازنده فیلدهای ورودی (برای جلوگیری از تکرار کد)
    def create_textfield(label, hint, is_phone=False):
        return ft.Column(
            controls=[
                ft.Text(label, size=14, color=ft.colors.BLACK87),
                ft.TextField(
                    hint_text=hint,
                    hint_style=ft.TextStyle(color=ft.colors.GREY_400),
                    border_color=ft.colors.TRANSPARENT,
                    bgcolor=ft.colors.WHITE,
                    border_radius=12,
                    text_size=14,
                    content_padding=15,
                    keyboard_type=ft.KeyboardType.PHONE if is_phone else ft.KeyboardType.TEXT
                )
            ],
            spacing=8
        )

    # ایجاد فیلدها بر اساس عکس
    company_name_field = create_textfield("نام شرکت", "مثلاً شرکت پخش بهار")
    visitor_name_field = create_textfield("نام ویزیتور", "نام و نام خانوادگی")
    visitor_phone_field = create_textfield("تلفن ویزیتور", "09...", is_phone=True)

    # دکمه ثبت در پایین صفحه
    submit_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.CHECK, color=ft.colors.WHITE),
                ft.Text("ثبت شرکت", color=ft.colors.WHITE, size=16, weight=ft.FontWeight.BOLD),
                ft.Container(width=24) # فضای خالی برای حفظ تقارن
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        bgcolor=DARK_GREEN,
        padding=ft.padding.all(15),
        border_radius=12,
        on_click=lambda e: print(f"شرکت {company_name_field.controls[1].value} ثبت شد.")
    )

    # چیدمان نهایی المان‌ها در صفحه
    main_layout = ft.Column(
        controls=[
            header,
            subtitle,
            company_name_field,
            ft.Container(height=10),
            visitor_name_field,
            ft.Container(height=10),
            visitor_phone_field,
            ft.Container(expand=True), # هل دادن دکمه به پایین صفحه
            submit_btn
        ],
        expand=True
    )

    page.add(
        ft.Container(
            content=main_layout,
            padding=20,
            expand=True
        )
    )

ft.app(target=main)
