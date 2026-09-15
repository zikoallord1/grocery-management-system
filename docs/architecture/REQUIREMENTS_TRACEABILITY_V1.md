# تتبع المتطلبات  نظام إدارة البقالات V1.0

## القاعدة

كل متطلب مهم يجب أن يمتلك المسار:

Requirement  Design  Business Rule  Implementation  Test  Acceptance

## المتطلبات الرئيسية

| المتطلب | التصميم | القواعد | الاختبار |
|---|---|---|---|
| المبيعات | Architecture + Database | Business Rules | Sales |
| المشتريات | Architecture + Database | Business Rules | Purchases |
| المخزون | Database + ERD | Stock Rules | Stock |
| العملاء | Database | Customer Rules | Customer |
| الموردون | Database | Supplier Rules | Supplier |
| الصندوق | Database | Cash Rules | Cashbox |
| المصروفات | Database | Expense Rules | Expenses |
| المرتجعات | Database + ERD | Return Rules | Returns |
| Smart Fields | Smart Fields + UX | Validation Rules | Integration |
| Barcode | Smart Fields + UX | Product Rules | Barcode |
| Offline | Architecture | Offline Rules | Offline |
| Backup/Restore | Architecture | Integrity Rules | Backup |
| Permissions | Permissions Matrix | Authorization Rules | Security |
| Audit | Architecture + Database | Audit Rules | Audit |
| Licensing | Licensing | License Rules | Licensing |
| Installer | Architecture + Licensing | Deployment Rules | Installer |
| Profit | Database | Accounting Rules | Profit |

## قاعدة التغيير

أي متطلب جديد يجب أن يضاف هنا قبل تنفيذه.

## الحالة

REQUIREMENTS TRACEABILITY V1.0  DESIGN BASELINE
