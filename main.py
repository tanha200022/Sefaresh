import re

import flet as ft

# توجه: با flet==0.24.1 نام‌ها ft.icons / ft.colors است.
# اگر flet را به 0.25+ ارتقا دادید، به ft.Icons / ft.Colors تغییر دهید.

DARK_GREEN = "#116040"
BG_COLOR = "#F7F9F7"
STORAGE_KEY = "companies"

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PHONE_RE = re.compile(r"^09\d{9}$")


def main(page: ft.Page):
    page.title = "سفارش‌یار - ثبت شرکت"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG_COLOR
    page.padding = 0

    # فونت فارسی (فایل در assets/fonts قرار دارد)
    page.fonts = {"Vazir": "fonts/Vazirmatn-Regular.ttf"}
    page.theme = ft.Theme(font_family="Vazir")

    # اندازه پنجره فقط برای اجرای دسکتاپ (روی اندروید نادیده گرفته می‌شود)
    page.window_width = 400
    page.window_height = 700

    # ---------- فیلدها ----------
    def make_field(hint, **kwargs):
        return ft.TextField(
            hint_text=hint,
            hint_style=ft.TextStyle(color=ft.colors.GREY_400),
            border_color=ft.colors.TRANSPARENT,
            focused_border_color=DARK_GREEN,
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            text_size=14,
            content_padding=15,
            **kwargs,
        )

    company_field = make_field("مثلاً شرکت پخش بهار")
    visitor_field = make_field("نام و نام خانوادگی")
    phone_field = make_field(
        "09123456789",
        keyboard_type=ft.KeyboardType.PHONE,
        input_filter=ft.NumbersOnlyInputFilter(),
        max_length=11,
        counter_text="",
        text_direction=ft.TextDirection.LTR,  # اعداد چپ‌به‌راست نمایش داده شوند
    )

    def labeled(label, field):
        return ft.Column(
            controls=[ft.Text(label, size=14, color=ft.colors.BLACK87), field],
            spacing=8,
        )

    # ---------- منطق ----------
    def show_message(text, error=False):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(text, color=ft.colors.WHITE),
            bgcolor=ft.colors.RED_700 if error else DARK_GREEN,
        )
        page.snack_bar.open = True
        page.update()

    def clear_form(e=None):
        for f in (company_field, visitor_field, phone_field):
            f.value = ""
            f.error_text = None
        page.update()

    def validate():
        ok = True
        for f in (company_field, visitor_field, phone_field):
            f.error_text = None

        if not (company_field.value or "").strip():
            company_field.error_text = "نام شرکت را وارد کنید"
            ok = False
        if not (visitor_field.value or "").strip():
            visitor_field.error_text = "نام ویزیتور را وارد کنید"
            ok = False

        phone = (phone_field.value or "").translate(PERSIAN_DIGITS)
        if not PHONE_RE.match(phone):
            phone_field.error_text = "شماره موبایل معتبر نیست (مثال: 09123456789)"
            ok = False
        return ok

    def on_submit(e):
        if not validate():
            page.update()
            return

        record = {
            "company": company_field.value.strip(),
            "visitor": visitor_field.value.strip(),
            "phone": phone_field.value.translate(PERSIAN_DIGITS),
        }
        try:
            companies = page.client_storage.get(STORAGE_KEY) or []
            companies.append(record)
            page.client_storage.set(STORAGE_KEY, companies)
        except Exception:
            show_message("ذخیره‌سازی انجام نشد", error=True)
            return

        clear_form()
        show_message(f"شرکت «{record['company']}» ثبت شد")

    # ---------- چیدمان ----------
    header = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.icons.CLOSE,
                icon_color=ft.colors.GREY_600,
                tooltip="بستن",
                on_click=clear_form,  # به ناوبری/بستن صفحه وصل شود
            ),
            ft.Text("شرکت جدید", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK87),
            ft.Container(width=40),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    subtitle = ft.Container(
        content=ft.Text("یک‌بار ثبت کنید؛ همیشه در دسترس است.", color=ft.colors.GREY_500, size=13),
        alignment=ft.alignment.center,
        margin=ft.margin.only(bottom=15, top=5),
    )

    form = ft.Column(
        controls=[
            labeled("نام شرکت", company_field),
            ft.Container(height=6),
            labeled("نام ویزیتور", visitor_field),
            ft.Container(height=6),
            labeled("تلفن ویزیتور", phone_field),
        ],
        scroll=ft.ScrollMode.AUTO,  # با باز شدن کیبورد قابل اسکرول باشد
        expand=True,
    )

    submit_btn = ft.FilledButton(
        text="ثبت شرکت",
        icon=ft.icons.CHECK,
        on_click=on_submit,
        height=52,
        style=ft.ButtonStyle(
            bgcolor=DARK_GREEN,
            color=ft.colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
        ),
    )

    page.add(
        ft.SafeArea(
            ft.Container(
                padding=20,
                expand=True,
                content=ft.Column(
                    controls=[
                        header,
                        subtitle,
                        form,
                        ft.Row([ft.Container(submit_btn, expand=True)]),
                    ],
                    expand=True,
                ),
            ),
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.app(target=main)
