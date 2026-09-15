# القرار التقني النهائي  نظام إدارة البقالات V1.0

## 1. الهدف

تثبيت الاختيارات التقنية الأساسية قبل بدء البرمجة.

## 2. قاعدة البيانات

المعتمد:

SQLite

الأسباب:

- Offline.
- خفيفة.
- مناسبة لجهاز العميل.
- Backup سهل.
- لا تحتاج خادما منفصلا في V1.0.

## 3. المعمارية

المعتمد:

Modular Monolith

مع طبقات:

Presentation
 Application
 Domain/Business Engine
 Repository
 SQLite

## 4. واجهة المستخدم

المطلوب:

- Windows Desktop.
- Arabic RTL.
- Responsive داخل التطبيق.
- Keyboard-first.
- Smart Fields.
- Barcode Support.
- Low-resource.

لا تعتمد الواجهة على الإنترنت.

## 5. Business Engine

هو المسؤول عن:

- قواعد البيع.
- الشراء.
- المخزون.
- الصندوق.
- العملاء.
- الموردين.
- المرتجعات.
- المصروفات.
- الصلاحيات التجارية.
- Idempotency.

## 6. ORM / Data Access

يجب اختيار طبقة Repository تمنع SQL من الوصول مباشرة إلى الواجهة.

الاختيار التنفيذي النهائي يثبت عند إنشاء الهيكل البرمجي مع الالتزام بالمبدأ:

UI لا يعرف تفاصيل قاعدة البيانات.

## 7. SQLite Configuration

يجب اختبار:

- Foreign Keys.
- WAL عند اعتماده.
- Busy Timeout.
- Transactions.
- Backup API.

## 8. الأداء

نظرا للجهاز المستهدف:

- تقليل الذاكرة.
- عدم تحميل كل البيانات مرة واحدة.
- Pagination.
- Lazy Loading.
- فهارس مدروسة.
- عدم وجود عمليات خلفية ثقيلة دون حاجة.

## 9. التخزين

فصل:

- Database.
- Attachments.
- Backups.
- Logs.
- Configuration.

عن ملفات المصدر البرمجي.

## 10. الأمان

- Password Hash.
- Roles/Permissions.
- Authorization خارج الواجهة.
- Audit.
- Signed Licensing.
- عدم حفظ الأسرار في Git.

## 11. النسخ الاحتياطي

- SQLite Backup API أو آلية مكافئة آمنة.
- Verification.
- Restore Test.
- Pre-Restore Backup.

## 12. التثبيت

المستخدم النهائي يستلم Installer.

لا يحتاج:

- Python.
- Node.
- Git.
- Terminal.

## 13. التطوير

بيئة التطوير منفصلة عن بيئة العميل.

بيانات العملاء الحقيقية لا تدخل Git.

## 14. الاختبارات

- Unit.
- Integration.
- Acceptance.
- Regression.
- Installer.

## 15. التوسع المستقبلي

التصميم يسمح لاحقا بـ:

- PostgreSQL.
- Multi-Branch.
- Cloud Sync.
- Mobile.
- Advanced Accounting.

لكن لا يتم إدخال هذه التعقيدات في V1.0 دون حاجة.

## 16. القرار النهائي

المعتمد:

Windows Desktop
+
Arabic RTL UI
+
Modular Monolith
+
Local Application
+
Business Engine
+
SQLite
+
Offline-First
+
Smart Fields
+
Barcode
+
Audit
+
Backup/Restore
+
Local Licensing
+
Installer

## 17. قاعدة عدم تغيير التقنية أثناء التنفيذ

لا تغير التقنية الأساسية لمجرد تفضيل شخصي أثناء التنفيذ.

أي تغيير جوهري يجب أن يبرر بـ:

- مشكلة فعلية.
- اختبار.
- أثر واضح.
- تحديث الوثائق.
- مراجعة قبل التنفيذ.

## 18. الحالة

TECHNOLOGY DECISION V1.0  DESIGN BASELINE
