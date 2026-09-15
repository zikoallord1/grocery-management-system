# خطة الاختبارات وسجل المخاطر  نظام إدارة البقالات V1.0

## 1. الهدف

تحدد هذه الوثيقة استراتيجية اختبار النظام وسجل المخاطر قبل الإنتاج.

## 2. مستويات الاختبار

### Unit Tests
اختبار القواعد والخدمات الصغيرة.

### Integration Tests
اختبار تكامل:

- Business Engine
- Repository
- SQLite
- Inventory
- Cashbox
- Accounts

### Acceptance Tests
اختبار السيناريو التجاري الكامل.

### Regression Tests
إعادة الاختبارات بعد كل تعديل مهم.

### Installer Tests
اختبار التثبيت على جهاز نظيف.

## 3. سيناريوهات القبول الأساسية

1. إضافة صنف.
2. إنشاء شراء.
3. زيادة المخزون.
4. إنشاء بيع.
5. نقص المخزون.
6. بيع نقدي.
7. بيع آجل.
8. بيع مختلط.
9. تحصيل عميل.
10. شراء آجل.
11. سداد مورد.
12. مصروف.
13. مرتجع بيع.
14. مرتجع شراء.
15. جرد وتسوية.
16. حساب الربح.
17. إغلاق اليوم.
18. Backup.
19. Restore.
20. الصلاحيات.
21. العمل دون إنترنت.
22. تثبيت نظيف.
23. الترخيص.
24. إعادة تشغيل بعد Crash.

## 4. اختبارات السلامة

يجب اختبار:

- Transaction Rollback.
- Foreign Keys.
- Unique Constraints.
- Idempotency.
- Duplicate Submit.
- Invalid Amount.
- Invalid Quantity.
- Negative Stock.
- Credit Limit.
- Overpayment.
- Closed Day.

## 5. اختبارات الصلاحيات

لكل عملية حساسة:

- مستخدم لديه الصلاحية.
- مستخدم بدون الصلاحية.
- مستخدم لديه VIEW فقط.
- مستخدم لديه CREATE دون APPROVE.
- مستخدم معطل.
- محاولة وصول مباشرة إلى Application/API.

## 6. اختبارات البيانات

يجب التأكد من:

- عدم تغير التاريخ القديم.
- عدم تكرار الحركات.
- تطابق الأرصدة مع الحركات.
- سلامة المرفقات.
- سلامة Backup.
- سلامة Restore.

## 7. اختبارات الأداء

V1.0 يستهدف جهازا منخفض الموارد.

يجب قياس:

- فتح النظام.
- فتح شاشة البيع.
- البحث بالصنف.
- حفظ عملية بيع.
- تقرير يومي.
- فتح قائمة أصناف كبيرة.

ولا تستخدم تحسينات معقدة قبل وجود قياس فعلي.

## 8. اختبارات SQLite

- integrity_check
- foreign_key_check
- WAL
- Transaction
- Backup
- Restore
- Migration

## 9. تعريف النجاح

كل اختبار Critical يجب أن ينجح قبل الإصدار.

ولا يكفي أن تعمل الواجهة إذا كانت الآثار التجارية غير صحيحة.

## 10. سجل المخاطر

### R01  فقد البيانات
الاحتمال: متوسط
الأثر: حرج
المعالجة:
- Transactions.
- Backup.
- Restore Tests.

### R02  تكرار العملية
الاحتمال: متوسط
الأثر: حرج
المعالجة:
- Idempotency.
- Unique Constraints.

### R03  خطأ في المخزون
الاحتمال: متوسط
الأثر: حرج
المعالجة:
- Stock Movements.
- Business Rules.
- Acceptance Tests.

### R04  خطأ في الربح
الاحتمال: متوسط
الأثر: عال
المعالجة:
- Weighted Average.
- Cost Snapshot.
- Profit Tests.

### R05  تجاوز الصلاحيات
الاحتمال: متوسط
الأثر: حرج
المعالجة:
- Authorization خارج الواجهة.
- Negative Tests.
- Audit.

### R06  تلف Backup
الاحتمال: منخفض/متوسط
الأثر: حرج
المعالجة:
- Backup Verification.
- Restore Test.

### R07  فشل التحديث
الاحتمال: متوسط
الأثر: عال
المعالجة:
- Pre-update Backup.
- Migrations.
- Recovery.

### R08  ضعف الجهاز
الاحتمال: عال
الأثر: متوسط
المعالجة:
- SQLite.
- Lightweight UI.
- Pagination.
- Lazy Loading.

### R09  خطأ المستخدم
الاحتمال: عال
الأثر: متوسط
المعالجة:
- Smart Fields.
- Validation.
- Confirmations.

### R10  تجاوز الترخيص
الاحتمال: متوسط
الأثر: عال
المعالجة:
- Signed License.
- Local Verification.
- Audit.

### R11  تضخم نطاق المشروع
الاحتمال: عال
الأثر: عال
المعالجة:
- V1 Scope.
- Design Baseline.
- Change Control.

### R12  خلط المحاسبة مع الواجهة
الاحتمال: متوسط
الأثر: حرج
المعالجة:
- Business Engine.
- Rules.
- Architecture Enforcement.

## 11. بوابة الإصدار

لا يصدر V1.0 قبل:

- نجاح الاختبارات الحرجة.
- نجاح Backup/Restore.
- نجاح Installer.
- نجاح الصلاحيات.
- نجاح العمليات المالية.
- نجاح المخزون.
- نجاح العمل Offline.
- عدم وجود أخطاء Critical مفتوحة.

## 12. الحالة

TEST PLAN & RISK REGISTER V1.0  DESIGN BASELINE
