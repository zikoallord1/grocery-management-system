# ERD التنفيذي  نظام إدارة البقالات V1.0

## الهدف
تحويل تصميم قاعدة البيانات إلى مخطط علاقات واضح قبل إنشاء ORM والجداول الفعلية.

## المجموعات
System:
users, roles, permissions, user_roles, role_permissions, settings, audit_logs

Products:
categories, units, unit_conversions, products, product_barcodes, stock_locations, stock_movements, stock_balances

Sales:
sales, sale_items, sale_payments, sale_returns, sale_return_items

Purchases:
purchases, purchase_items, purchase_payments, purchase_returns, purchase_return_items

Customers:
customers, customer_account_movements, customer_payments

Suppliers:
suppliers, supplier_account_movements, supplier_payments

Finance:
payment_methods, cashboxes, cashbox_movements

Expenses:
expense_categories, expenses, expense_payments

Operations:
business_days

Attachments:
attachments, attachment_links

Licensing:
license, license_events

## العلاقات الرئيسية

categories 1:N products
units 1:N products
products 1:N product_barcodes
products 1:N sale_items
products 1:N purchase_items
products 1:N stock_movements

sales 1:N sale_items
sales 1:N sale_payments
sales 1:N sale_returns

purchases 1:N purchase_items
purchases 1:N purchase_payments
purchases 1:N purchase_returns

customers 1:N sales
customers 1:N customer_account_movements
customers 1:N customer_payments

suppliers 1:N purchases
suppliers 1:N supplier_account_movements
suppliers 1:N supplier_payments

cashboxes 1:N cashbox_movements
expenses 1:N expense_payments
attachments 1:N attachment_links
license 1:N license_events

## قواعد العلاقات

- Foreign Keys مفعلة.
- المستند المالي لا يحذف بطريقة تكسر التاريخ.
- الحركات المالية والمخزنية لها مصدر واضح.
- stock_movements هو مصدر حقيقة المخزون.
- customer_account_movements هو مصدر حقيقة العميل.
- supplier_account_movements هو مصدر حقيقة المورد.
- cashbox_movements هو مصدر حقيقة الصندوق.
- stock_balances مشتق/Cache وليس مصدر الحقيقة.
- CASCADE غير مسموح عشوائيا على السجلات التاريخية.

## الحالة

ERD EXECUTABLE DESIGN V1.0  DESIGN BASELINE
