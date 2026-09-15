# تصميم قاعدة البيانات  نظام إدارة البقالات V1.0

## 1. الهدف

تصميم قاعدة بيانات محلية Offline-First لنظام إدارة البقالات V1.0 بحيث تكون قاعدة البيانات مصدر الحقيقة للعمليات والبيانات مع الحفاظ على الترابط الكامل بين المبيعات والمشتريات والمخزون والعملاء والموردين والصندوق والمصروفات والتقارير.

المبدأ الأساسي:

> يدخل المستخدم العملية التجارية مرة واحدة ويقوم النظام تلقائيا بإنشاء وتحديث جميع الآثار المرتبطة بها.

## 2. نطاق V1.0

تشمل قاعدة البيانات في V1.0 على الأقل:

- الأصناف.
- التصنيفات.
- الوحدات.
- الباركودات.
- المخزون.
- المبيعات.
- مرتجعات المبيعات.
- المشتريات.
- مرتجعات المشتريات.
- العملاء.
- حسابات العملاء.
- الموردين.
- حسابات الموردين.
- الصندوق.
- وسائل الدفع.
- المصروفات.
- أيام العمل.
- المستخدمين والصلاحيات.
- سجل التدقيق.
- المرفقات.
- إعدادات النظام.
- الترخيص المحلي.

ويجب أن يكون التصميم قابلا لإضافة وظائف مستقبلية دون كسر العمليات الأساسية.

## 3. المبادئ الأساسية

1. SQLite هي قاعدة البيانات المعتمدة في V1.0.
2. قاعدة البيانات محلية وتعمل بدون إنترنت.
3. قاعدة البيانات هي مصدر الحقيقة الأساسي للبيانات.
4. لا توجد أرصدة مالية يتم تعديلها يدويا.
5. الأرصدة تستنتج من الحركات المرتبطة بالمستندات.
6. لا يجوز حذف العمليات المالية المعتمدة مباشرة.
7. التصحيح المالي يتم عبر الإلغاء أو العكس أو المرتجع أو تصحيح موثق.
8. كل حركة مخزون يجب أن تكون قابلة للتتبع إلى مصدرها.
9. كل حركة صندوق يجب أن تكون قابلة للتتبع إلى مصدرها.
10. كل حركة حساب عميل أو مورد يجب أن تكون قابلة للتتبع إلى مصدرها.
11. العمليات المركبة تنفذ داخل Transaction واحدة.
12. العمليات الحساسة تستخدم Idempotency UUID أو مفتاحا فريدا مناسبا.
13. يجب الاحتفاظ بسجل تدقيق Audit Trail.
14. يجب دعم المرفقات.
15. يجب حفظ القيمة التاريخية للعمليات المالية.
16. لا تتخذ قاعدة البيانات القرارات التجارية القرارات التجارية تنفذ في Business Engine.
17. لا تنفذ الواجهة SQL مباشرا.
18. يجب أن تكون العلاقات والقيود الأساسية محمية من مستوى قاعدة البيانات نفسها.
19. يمكن استخدام الجداول المشتقة أو Cache لتحسين الأداء لكنها لا تصبح مصدر الحقيقة.
20. لا يسمح بالتوسع العشوائي في V1.0 على حساب سلامة التصميم.

## 4. المسار المعماري

المسار المعتمد للوصول إلى قاعدة البيانات:

UI
 Application Service
 Business Engine
 Repository
 Database

ولا يسمح بالمسار:

UI
 SQL مباشر

## 5. المجموعات الرئيسية للبيانات

### 5.1 النظام والأمان
- users
- roles
- permissions
- user_roles
- role_permissions
- settings
- audit_logs

### 5.2 الأصناف والمخزون
- categories
- units
- unit_conversions (للتوسع عند الحاجة)
- products
- product_barcodes
- stock_locations
- stock_movements
- stock_balances

### 5.3 المبيعات
- sales
- sale_items
- sale_payments
- sale_returns
- sale_return_items

### 5.4 المشتريات
- purchases
- purchase_items
- purchase_payments
- purchase_returns
- purchase_return_items

### 5.5 العملاء
- customers
- customer_account_movements
- customer_payments

### 5.6 الموردون
- suppliers
- supplier_account_movements
- supplier_payments

### 5.7 الصندوق ووسائل الدفع
- cashboxes
- payment_methods
- cashbox_movements

### 5.8 المصروفات
- expense_categories
- expenses
- expense_payments

### 5.9 أيام العمل والتقارير
- business_days
- report_snapshots (اختياري وعند الحاجة فقط)

### 5.10 المرفقات
- attachments
- attachment_links

### 5.11 الترخيص
- license
- license_events

## 6. قواعد عامة للمفاتيح والمعرفات

1. كل جدول رئيسي يستخدم معرفا داخليا فريدا.
2. يفضل استخدام UUID كمفتاح مرجعي للكيانات والعمليات الحساسة.
3. أرقام المستندات التجارية مثل رقم الفاتورة أو السند لا تكون هي المفتاح الأساسي.
4. يجب أن تكون أرقام المستندات فريدة ضمن النطاق المحدد لها.
5. يجب عدم الاعتماد على واجهة المستخدم وحدها لمنع تكرار رقم المستند.
6. كل عملية حساسة يجب أن تحتوي على idempotency_key فريد عندما تكون قابلة لإعادة الإرسال.
7. يجب دعم UUID للعمليات التي قد يعاد إرسالها بعد انقطاع أو فشل في الاتصال الداخلي بين طبقات التطبيق.

## 7. الأصناف

### 7.1 categories

- id
- name
- description
- is_active
- created_at
- updated_at

### 7.2 units

- id
- name
- symbol
- is_active

أمثلة:

- حبة
- كرتون
- باكت
- كيلو
- لتر

### 7.3 products

يمثل الصنف التجاري.

الحقول الأساسية:

- id
- sku
- name
- short_name
- category_id
- default_unit_id
- purchase_price
- sale_price
- minimum_stock
- reorder_level
- is_active
- created_at
- updated_at

### قواعد المنتجات

- SKU يجب أن يكون فريدا.
- يمكن تعطيل الصنف بدل حذفه إذا كان مرتبطا بعمليات سابقة.
- لا يجوز تغيير البيانات التاريخية التي تؤثر على نتائج المستندات السابقة.
- أسعار المستندات التاريخية تحفظ داخل بنود المستند نفسها.

## 8. الباركود

### product_barcodes

- id
- product_id
- barcode
- barcode_type
- is_primary
- is_active
- created_at

القواعد:

- يمكن للصنف أن يمتلك أكثر من باركود.
- barcode يجب أن يكون فريدا.
- يمكن تحديد باركود أساسي.
- قارئ الباركود يستخدم هذا الجدول للوصول للصنف.

## 9. الوحدات والتحويلات

V1.0 يجب أن تكون بسيطة ويمكنها العمل بوحدة أساسية واحدة للصنف.

لكن التصميم يجب ألا يمنع التوسع.

### unit_conversions

اختياري في المرحلة الأولى ويجهز للتوسع لاحقا:

- id
- product_id
- from_unit_id
- to_unit_id
- conversion_factor
- is_active

مثال مستقبلي:

1 كرتون = 24 حبة

ولا يتم تفعيل التعقيد التشغيلي لهذا الجدول إلا عند الحاجة الفعلية.

## 10. مواقع التخزين

### stock_locations

- id
- code
- name
- location_type
- is_active
- created_at

يمكن أن يمثل V1.0 مخزنا واحدا لكن التصميم يسمح بإضافة أكثر من مخزن لاحقا.

## 11. المبيعات

### 11.1 sales

رأس عملية البيع:

- id
- document_no
- customer_id
- business_date
- sale_date
- subtotal
- discount
- tax
- total
- paid_amount
- credit_amount
- status
- payment_status
- idempotency_key
- created_by
- created_at
- updated_at

### 11.2 sale_items

- id
- sale_id
- product_id
- unit_id
- quantity
- unit_price
- discount
- total
- cost_price_snapshot
- created_at

### قاعدة مهمة

يجب الاحتفاظ بـ cost_price_snapshot وقت البيع حتى لا تتغير أرباح العمليات التاريخية عند تغير تكلفة الصنف لاحقا.

## 12. دفعات البيع

### sale_payments

تمثل وسائل الدفع الفعلية المرتبطة بعملية البيع.

- id
- sale_id
- payment_method_id
- cashbox_id (عند الحاجة)
- amount
- currency
- reference_no
- created_at

يجب دعم الدفع المختلط.

مثال:

- 10,000 نقدا
- 5,000 محفظة
- 5,000 آجل

ولا يجوز إجبار كل عملية بيع على وسيلة دفع واحدة.

## 13. المشتريات

### 13.1 purchases

- id
- document_no
- supplier_id
- business_date
- purchase_date
- subtotal
- discount
- tax
- total
- paid_amount
- credit_amount
- status
- payment_status
- idempotency_key
- created_by
- created_at
- updated_at

### 13.2 purchase_items

- id
- purchase_id
- product_id
- unit_id
- quantity
- unit_cost
- discount
- total
- created_at

ويجب الاحتفاظ بتكلفة الشراء التاريخية داخل المستند.

## 14. دفعات المشتريات

### purchase_payments

- id
- purchase_id
- payment_method_id
- cashbox_id (عند الحاجة)
- amount
- currency
- reference_no
- created_at

ويجب دعم الدفع المختلط عند الشراء أيضا.

## 15. المخزون

المخزون يبنى أساسا من الحركات.

### stock_movements

- id
- product_id
- stock_location_id
- movement_type
- quantity
- unit_id
- unit_cost
- direction
- reference_type
- reference_id
- business_date
- movement_date
- created_by
- idempotency_key
- created_at

### أنواع الحركة

- PURCHASE
- SALE
- SALE_RETURN
- PURCHASE_RETURN
- ADJUSTMENT_IN
- ADJUSTMENT_OUT
- OPENING_BALANCE
- TRANSFER_IN
- TRANSFER_OUT

### القواعد

1. حركة المخزون الناتجة عن عملية تجارية يجب أن ترتبط بمصدرها.
2. `reference_type + reference_id` يستخدمان لمعرفة المستند المصدر.
3. لا يجوز إنشاء حركة مجهولة المصدر في العمليات التلقائية.
4. التسوية اليدوية يجب أن تحمل سببا ومستخدما.
5. لا يسمح بكمية صفر أو سالبة عندما تكون القاعدة لا تسمح بذلك.
6. أي حركة ناتجة عن البيع أو الشراء يجب أن تكون ضمن نفس Transaction للمستند.

## 16. رصيد المخزون

### stock_balances

يمكن استخدامه كـ Cache أو جدول مشتق لتحسين سرعة العرض.

لكن:

> stock_movements هو مصدر الحقيقة.

ولا يجوز أن يؤدي تعديل stock_balances وحده إلى تغيير الحقيقة المالية أو المخزنية.

## 17. سياسة تكلفة المخزون

V1.0 يجب أن تحدد سياسة تكلفة واضحة قبل البرمجة.

السياسة الأساسية المعتمدة في التصميم:

- حفظ تكلفة الشراء التاريخية لكل دفعة شراء.
- حفظ cost_price_snapshot داخل بند البيع.
- عدم إعادة حساب تكلفة بيع قديم بمجرد تغيير سعر الشراء لاحقا.

طريقة حساب التكلفة التشغيلية الفعلية للمخزون والربح يجب تثبيتها في Business Rules قبل تنفيذ محرك الربح ولا تترك لاجتهاد المبرمج.

## 18. مرتجعات المبيعات

### sale_returns

- id
- document_no
- original_sale_id
- customer_id
- business_date
- return_date
- subtotal
- discount
- total
- status
- idempotency_key
- created_by
- created_at

### sale_return_items

- id
- sale_return_id
- original_sale_item_id
- product_id
- quantity
- unit_price
- cost_price_snapshot
- total
- created_at

### قواعد

1. يجب ربط المرتجع بالبيع الأصلي عندما يكون ذلك ممكنا.
2. لا يجوز تجاوز الكمية القابلة للإرجاع.
3. المرتجع يعكس أثر المخزون.
4. المرتجع يعكس أثر العميل أو النقد حسب طريقة التسوية.
5. لا يجوز أن يؤدي تكرار إرسال المرتجع إلى تكرار الأثر.

## 19. مرتجعات المشتريات

### purchase_returns

- id
- document_no
- original_purchase_id
- supplier_id
- business_date
- return_date
- subtotal
- discount
- total
- status
- idempotency_key
- created_by
- created_at

### purchase_return_items

- id
- purchase_return_id
- original_purchase_item_id
- product_id
- quantity
- unit_cost
- total
- created_at

### قواعد

1. يجب ربط المرتجع بالشراء الأصلي عندما يكون ذلك ممكنا.
2. لا يجوز تجاوز الكمية القابلة للإرجاع.
3. المرتجع يقلل المخزون.
4. المرتجع يعكس أثر المورد أو الدفع حسب التسوية.

## 20. العملاء

### customers

- id
- code
- name
- phone
- address
- notes
- credit_limit
- is_active
- created_at
- updated_at

### القاعدة

لا يجوز تغيير رصيد العميل مباشرة داخل customers.

## 21. حساب العميل

### customer_account_movements

- id
- customer_id
- movement_type
- amount
- currency
- direction
- reference_type
- reference_id
- business_date
- created_by
- created_at

### أنواع الحركة

- SALE_CREDIT
- CUSTOMER_PAYMENT
- SALE_RETURN
- CREDIT_ADJUSTMENT
- DEBIT_ADJUSTMENT

كل حركة يجب أن يكون لها مصدر واضح.

### customer_payments

- id
- customer_id
- payment_date
- business_date
- amount
- currency
- payment_method_id
- cashbox_id (عند الحاجة)
- reference_no
- notes
- idempotency_key
- created_by
- created_at

## 22. الموردون

### suppliers

- id
- code
- name
- phone
- address
- notes
- credit_limit
- is_active
- created_at
- updated_at

### supplier_account_movements

- id
- supplier_id
- movement_type
- amount
- currency
- direction
- reference_type
- reference_id
- business_date
- created_by
- created_at

### الأنواع

- PURCHASE_CREDIT
- SUPPLIER_PAYMENT
- PURCHASE_RETURN
- CREDIT_ADJUSTMENT
- DEBIT_ADJUSTMENT

### supplier_payments

- id
- supplier_id
- payment_date
- business_date
- amount
- currency
- payment_method_id
- cashbox_id (عند الحاجة)
- reference_no
- notes
- idempotency_key
- created_by
- created_at

## 23. وسائل الدفع

### payment_methods

يجب أن تكون قابلة للإعداد.

أمثلة:

- CASH
- BANK
- ELECTRONIC_WALLET
- CREDIT

ولا يجوز ربط منطق الأعمال بأسماء ثابتة لا يمكن إعدادها.

يجب التفريق بين:

### وسيلة الدفع
كيف تم الدفع

### الصندوق/الحساب
أين سجل الأثر المالي

هذا الفصل ضروري لدعم:

- نقد.
- بنك.
- محفظة إلكترونية.
- حسابات أخرى مستقبلا.

## 24. الصندوق

### cashboxes

- id
- code
- name
- account_type
- currency
- opening_balance
- is_active
- created_at

يمكن تمثيل كل صندوق أو وسيلة مالية تشغيلية بحساب مستقل بحسب التصميم التنفيذي.

### cashbox_movements

- id
- cashbox_id
- movement_type
- amount
- currency
- direction
- reference_type
- reference_id
- business_date
- movement_date
- created_by
- idempotency_key
- created_at

### أنواع الحركة

- SALE_RECEIPT
- CUSTOMER_PAYMENT
- PURCHASE_PAYMENT
- SUPPLIER_PAYMENT
- EXPENSE_PAYMENT
- OPENING_BALANCE
- TRANSFER_IN
- TRANSFER_OUT
- ADJUSTMENT

### القاعدة

الرصيد يعرض من الحركة وليس من تعديل يدوي لرقم الرصيد.

## 25. المصروفات

### expense_categories

- id
- name
- description
- is_active

### expenses

- id
- expense_no
- category_id
- description
- amount
- currency
- business_date
- expense_date
- status
- payment_status
- idempotency_key
- created_by
- created_at

### expense_payments

- id
- expense_id
- payment_method_id
- cashbox_id
- amount
- currency
- reference_no
- created_at

## 26. أيام العمل

### business_days

- id
- business_date
- status
- opened_at
- closed_at
- opened_by
- closed_by

### الحالات

- OPEN
- CLOSED

ويجب أن يحتوي كل مستند تشغيلي مهم على business_date.

يجب التفريق بين:

- business_date: اليوم التجاري الذي تنتمي إليه العملية.
- created_at: وقت تسجيل العملية.
- updated_at: وقت آخر تعديل مسموح.

## 27. إغلاق اليوم

بعد إغلاق اليوم:

- تمنع العمليات المحاسبية والتشغيلية غير المصرح بها.
- لا يتم تعديل البيانات التاريخية مباشرة.
- أي تصحيح يتطلب صلاحية وقاعدة تصحيح واضحة.
- يسجل الإجراء في Audit Trail.

## 28. حالات المستندات

الحالات الأساسية:

- DRAFT
- CONFIRMED
- CANCELLED
- RETURNED
- CLOSED

ولا يستخدم الحذف الفيزيائي لتصحيح العمليات المالية المؤكدة.

## 29. الإلغاء والعكس

يجب أن يكون لكل مستند مالي مهم آلية لمعرفة:

- المستند الأصلي.
- مستند الإلغاء أو العكس.
- سبب الإلغاء أو التصحيح.
- المستخدم الذي نفذ الإجراء.
- وقت التنفيذ.

عند الحاجة يمكن استخدام:

- reversal_of_id
- cancellation_reason

ولا يجوز إنشاء أثر عكسي دون مرجع واضح.

## 30. الترقيم

كل نوع مستند يجب أن يمتلك سياسة ترقيم مستقلة قابلة للضبط.

أمثلة:

- بيع
- شراء
- مرتجع بيع
- مرتجع شراء
- سند قبض
- سند صرف
- مصروف

يجب ضمان عدم تكرار رقم المستند داخل نطاقه المحدد.

## 31. العملات

كل حركة مالية يجب أن تحفظ:

- amount
- currency

وعند استخدام سعر تحويل:

- exchange_rate
- base_amount

ويجب عدم إعادة تقييم العمليات التاريخية تلقائيا بسبب تغير سعر الصرف.

العملة الأساسية للنظام قابلة للإعداد.

## 32. القيود على القيم

يجب استخدام CHECK Constraints أو التحقق في طبقة Business Engine حسب الحاجة لمنع:

- كميات غير منطقية.
- مبالغ سالبة غير مسموحة.
- أسعار غير صالحة.
- خصومات تتجاوز الحدود.
- نسب تحويل غير منطقية.

## 33. المرفقات

### attachments

- id
- file_name
- stored_name
- file_path
- mime_type
- file_size
- checksum
- created_by
- created_at

### attachment_links

- id
- attachment_id
- entity_type
- entity_id
- created_at

### قواعد

- يمكن ربط أكثر من مرفق بالمستند.
- يجب منع الرابط المكرر لنفس المرفق ونفس السجل.
- يجب التحقق من وجود المرفق ومساره.
- حذف السجل التجاري لا يؤدي تلقائيا إلى فقدان سجل المرفق دون سياسة واضحة.

## 34. التدقيق Audit Trail

### audit_logs

- id
- user_id
- action
- entity_type
- entity_id
- before_data
- after_data
- reason
- created_at

يجب تسجيل العمليات الحساسة على الأقل:

- إنشاء مستند مؤكد.
- إلغاء.
- مرتجع.
- تصحيح.
- تعديل إعدادات مهمة.
- فتح يوم.
- إغلاق يوم.
- تعديل صلاحيات.
- محاولات العمليات الحساسة عند الحاجة.

## 35. المستخدمون والصلاحيات

### users

- id
- username
- password_hash
- display_name
- is_active
- created_at
- updated_at

### roles

- id
- name
- description
- is_active

### permissions

- id
- code
- name
- description

### user_roles

- user_id
- role_id

### role_permissions

- role_id
- permission_id

الصلاحيات يجب أن تطبق في:

- الواجهة.
- Application Layer.
- Business Engine.

ولا تعتمد الواجهة وحدها كحاجز أمان.

## 36. الإعدادات

### settings

- id
- key
- value
- value_type
- category
- updated_by
- updated_at

يستخدم لإعدادات مثل:

- اسم المتجر.
- العملة الأساسية.
- رقم المستندات.
- إعدادات الطباعة.
- إعدادات البيع.
- إعدادات المخزون.

ولا يسمح بوضع الإعدادات التشغيلية المهمة بشكل Hard-coded داخل عدة وحدات.

## 37. منع التكرار

كل عملية مركبة يجب أن تكون قابلة للحماية من التكرار باستخدام:

- idempotency_key
- Unique Constraints
- business rules

مثال:

إذا أعاد المستخدم الضغط على حفظ بسبب بطء الشاشة لا يتم تسجيل البيع مرتين.

## 38. Transactions

مثال البيع:

1. التحقق من المستخدم والصلاحية.
2. إنشاء رأس البيع.
3. إنشاء بنود البيع.
4. التحقق من المخزون.
5. إنشاء حركة المخزون.
6. إنشاء دفعات البيع.
7. إنشاء حركة الصندوق عند الدفع.
8. إنشاء حركة حساب العميل عند وجود آجل.
9. إنشاء Audit Log.
10. Commit.

كل الخطوات السابقة يجب أن تشكل Transaction منطقية واحدة للعملية.

إذا فشل عنصر أساسي:
- Rollback.

## 39. مبدأ مصدر الحقيقة

### المبيعات
sales + sale_items

### المشتريات
purchases + purchase_items

### المخزون
stock_movements

### الصندوق
cashbox_movements

### العميل
customer_account_movements

### المورد
supplier_account_movements

### المستندات
المستند + بنوده

### الأرصدة المشتقة
تستخدم للعرض والتسريع فقط ولا تعتبر مصدرا مستقلا للحقيقة.

## 40. العلاقات الأساسية

### البيع

Product
 Sale Item
 Sale
 Sale Payment
 Cashbox Movement
أو
 Customer Account Movement

وفي جميع الحالات:

Sale
 Stock Movement

### الشراء

Product
 Purchase Item
 Purchase
 Purchase Payment
 Cashbox Movement
أو
 Supplier Account Movement

وفي جميع الحالات:

Purchase
 Stock Movement

### المرتجع

Sale Return
 Original Sale
 Sale Return Items
 Reverse Stock Effect
 Customer/Cash Effect حسب التسوية

Purchase Return
 Original Purchase
 Purchase Return Items
 Reverse Stock Effect
 Supplier/Cash Effect حسب التسوية

### المصروف

Expense
 Expense Payment
 Cashbox Movement

## 41. الفهارس

يجب إنشاء فهارس مناسبة على الأقل على:

- products.sku
- products.name
- product_barcodes.barcode
- sales.document_no
- sales.business_date
- sales.customer_id
- purchases.document_no
- purchases.business_date
- purchases.supplier_id
- stock_movements.product_id
- stock_movements.stock_location_id
- stock_movements.business_date
- customer_account_movements.customer_id
- supplier_account_movements.supplier_id
- cashbox_movements.cashbox_id
- cashbox_movements.business_date
- audit_logs.entity_type + entity_id

ويجب إنشاء الفهارس بناء على الاستعلامات الفعلية وعدم الإفراط فيها.

## 42. Unique Constraints

يجب دراسة وإنشاء قيود Unique مناسبة على الأقل لـ:

- products.sku
- product_barcodes.barcode
- document numbers ضمن نطاقها
- idempotency_key للعمليات التي تستخدمه
- usernames
- settings.key

ويجب أن تمنع القيود تكرار البيانات الحرجة حتى إذا تجاوز التطبيق فحص الواجهة.

## 43. Foreign Keys

يجب استخدام Foreign Keys للحفاظ على العلاقات الرئيسية بين:

- المنتجات والتصنيفات والوحدات.
- البنود ورؤوس المستندات.
- الحركات والمستندات المصدر.
- العملاء وحركات حساباتهم.
- الموردين وحركات حساباتهم.
- وسائل الدفع وحركاتها.
- المرفقات والسجلات المرتبطة.
- المستخدمين وسجل التدقيق.

## 44. الحذف

### البيانات غير المالية

يفضل استخدام:

is_active = false

بدل الحذف إذا كانت البيانات مرتبطة بالسجل التاريخي.

### البيانات المالية

لا يسمح بالحذف المباشر للمستندات المؤكدة أو الحركات المالية.

التصحيح يتم باستخدام:

- CANCEL
- REVERSAL
- RETURN
- ADJUSTMENT موثق

## 45. الأداء

لأن V1.0 تستهدف أجهزة ضعيفة نسبيا:

1. SQLite.
2. استعلامات بسيطة ومفهرسة.
3. عدم تحميل جداول ضخمة كاملة إلى الواجهة.
4. Pagination.
5. Lazy Loading.
6. عدم حساب الرصيد بطريقة مكلفة في كل شاشة دون حاجة.
7. استخدام stock_balances أو Cache عند إثبات الحاجة.
8. إبقاء عمليات الكتابة داخل Transactions صغيرة ومحددة.

## 46. النسخ الاحتياطي

قاعدة البيانات يجب أن تكون قابلة للنسخ الاحتياطي المحلي.

النسخة الاحتياطية يجب أن تتضمن:

- قاعدة البيانات.
- بيانات الإعدادات الضرورية.
- بيانات الترخيص اللازمة وفق السياسة.
- المرفقات إذا كانت سياسة النسخ الاحتياطي تشملها.

ويجب دعم Restore مع التحقق من سلامة النسخة.

## 47. الترخيص

### license

يحفظ معلومات الترخيص المحلي.

### license_events

يسجل:

- التفعيل.
- التجديد.
- التغيير.
- التعطيل.
- محاولات التحقق المهمة.

منطق الترخيص يجب أن يبقى منفصلا عن منطق البيع والمخزون.

## 48. التقارير

التقارير لا تنشئ أرصدة مستقلة.

التقرير يقرأ من مصادر الحقيقة:

- المبيعات.
- المشتريات.
- حركات المخزون.
- حركات الصندوق.
- حسابات العملاء.
- حسابات الموردين.
- المصروفات.

ويمكن لاحقا إنشاء report_snapshots للأداء فقط إذا أثبت القياس الحاجة إليها.

## 49. Business Event Principle

لا يكفي إنشاء السجلات فقط.

كل عملية رئيسية يجب أن تمر عبر Business Event.

أمثلة:

- SALE_CREATED
- SALE_CONFIRMED
- SALE_CANCELLED
- SALE_RETURN_CREATED
- PURCHASE_CREATED
- PURCHASE_CONFIRMED
- PURCHASE_RETURN_CREATED
- CUSTOMER_PAYMENT
- SUPPLIER_PAYMENT
- EXPENSE_CREATED
- STOCK_ADJUSTMENT
- DAY_CLOSED

المسار:

Business Event
 Rule
 Business Engine
 Domain Effects
 Persistence
 Audit

## 50. قاعدة منع الاجتهاد البرمجي

لا يجوز ترك القرارات التجارية التالية لاجتهاد المبرمج أثناء التنفيذ:

- متى ينقص المخزون.
- متى يزيد المخزون.
- كيف يسجل البيع الآجل.
- كيف يسجل التحصيل.
- كيف تسجل دفعة المورد.
- كيف يعالج المرتجع.
- كيف يحسب الربح.
- كيف يعالج إغلاق اليوم.
- كيف يمنع التكرار.
- كيف تعالج العملية الملغاة.

هذه القواعد تثبت في Business Rules قبل التنفيذ.

## 51. ERD المتوقع

على مستوى العلاقات الرئيسية:

Users
 Roles
 Permissions

Products
 Categories
 Units
 Product Barcodes
 Stock Locations
 Stock Movements

Sales
 Sale Items
 Sale Payments
 Sale Returns
 Sale Return Items

Purchases
 Purchase Items
 Purchase Payments
 Purchase Returns
 Purchase Return Items

Customers
 Customer Account Movements
 Customer Payments

Suppliers
 Supplier Account Movements
 Supplier Payments

Cashboxes
 Cashbox Movements

Expenses
 Expense Payments

Documents
 Attachments

Users
 Audit Logs

## 52. الاختبارات المطلوبة قبل التنفيذ

قبل إنشاء الجداول الفعلية يجب اختبار التصميم منطقيا عبر السيناريوهات التالية:

1. إضافة صنف.
2. شراء نقدي.
3. شراء آجل.
4. بيع نقدي.
5. بيع مختلط.
6. بيع آجل.
7. تحصيل من عميل.
8. سداد مورد.
9. مصروف نقدي.
10. مرتجع بيع.
11. مرتجع شراء.
12. تسوية مخزون.
13. فتح يوم.
14. إغلاق يوم.
15. تكرار إرسال نفس العملية.
16. محاولة حذف عملية مالية.
17. تغيير سعر الصنف بعد وجود مبيعات سابقة.
18. تغيير سعر شراء الصنف.
19. العمل بدون إنترنت.
20. استعادة نسخة احتياطية.

## 53. معيار اعتماد التصميم

لا يعتمد تصميم قاعدة البيانات قبل التأكد من:

- سلامة العلاقات.
- سلامة Foreign Keys.
- سلامة Unique Constraints.
- عدم وجود أكثر من مصدر للحقيقة.
- دعم الدفع المختلط.
- دعم البيع والشراء الآجل.
- دعم المرتجعات.
- دعم المخزون.
- دعم العملاء والموردين.
- دعم الإلغاء والعكس.
- دعم التدقيق.
- دعم Idempotency.
- دعم الأيام التجارية.
- دعم العملات.
- توافقه مع Architecture V1.0.
- قابليته للتوسع دون كسر V1.0.

## 54. حالة الوثيقة

هذه الوثيقة هي النسخة المنقحة من تصميم قاعدة البيانات V1.0.

تم تصميمها كمرجع قبل التنفيذ وليس كبديل عن:

- ERD النهائي.
- Business Rules.
- قواعد المحاسبة.
- خطة الاختبارات.

لا يبدأ تنفيذ الجداول النهائية أو ORM قبل اعتماد هذا التصميم وإكمال الوثائق المرتبطة.

## 55. الخلاصة

القاعدة الذهبية:

> عملية تجارية واحدة تدخل للنظام مرة واحدة ثم يقوم Business Engine بإنشاء جميع آثارها المترابطة بينما تبقى قاعدة البيانات مصدرا منظما وآمنا للحقيقة التاريخية.

المبدأ التنفيذي النهائي:

UI
 Application Service
 Business Event
 Business Rule
 Business Engine
 Repository
 SQLite

والنتيجة المطلوبة:

- لا تكرار.
- لا أرصدة يدوية.
- لا حذف مالي مباشر.
- لا حركات مجهولة المصدر.
- لا قرارات مالية مخفية داخل الواجهة.
- كل عملية قابلة للتتبع.
- كل أثر قابل للمراجعة.
- التصميم جاهز للتوسع مستقبلا.

---
الحالة: DATABASE DESIGN V1.0  REVISED FOR REVIEW
