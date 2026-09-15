# قائمة ما قبل البرمجة  نظام إدارة البقالات V1.0

## الوثائق

- Product Specification 
- Smart Fields 
- UX/UI 
- Architecture 
- Database Design 
- Business Rules 
- Offline/Data Integrity 
- Permissions Matrix 
- Licensing 
- Test/Risk 
- Technology Decision 
- ERD
- BPMN
- Requirements Traceability
- Scope/Change Control

## قرارات ثابتة

- SQLite
- Modular Monolith
- Offline-First
- Arabic RTL
- Business Engine
- Weighted Average Cost
- No Direct Financial Delete
- Idempotency
- Audit
- Backup/Restore
- Local Licensing
- Installer
- Smart Fields
- Barcode

## قبل كتابة الكود

يجب التأكد من:

1. العلاقات معتمدة.
2. Business Rules معتمدة.
3. الصلاحيات معتمدة.
4. Offline Rules معتمدة.
5. طرق التكلفة معتمدة.
6. الاختبارات الأساسية محددة.
7. نطاق V1.0 مغلق.
8. بيئة العميل منفصلة عن بيئة التطوير.

## ممنوع قبل الاعتماد

- كتابة SQL تجاري داخل UI.
- تعديل الأرصدة مباشرة.
- حذف العمليات المالية.
- إضافة ميزات خارج النطاق دون Change Control.
- وضع كلمات مرور أو بيانات عملاء داخل Git.

## الحالة

PRE-CODING CHECKLIST V1.0
