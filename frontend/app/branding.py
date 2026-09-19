from dataclasses import dataclass


@dataclass(frozen=True)
class Branding:
    program_name: str = "نظام الماركت المحاسبي"
    designer_credit: str = "تصميم وتنفيذ المهندس : زكريا الحاج"
    contact_text: str = "لطلب البرنامج أو تصميم برامج أخرى التواصل على الرقم 772233564"
    phone_display: str = "772233564"
    phone_uri: str = "tel:+967772233564"
    whatsapp_uri: str = "https://wa.me/967772233564"


BRANDING = Branding()
