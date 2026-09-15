# تدفقات الأعمال BPMN  نظام إدارة البقالات V1.0

## 1. البيع

User
 Create Sale
 Validate
 Check Permission
 Check Stock
 Confirm
 Business Event SALE_CONFIRMED
 Update Stock
 Record Payment / Customer Credit
 Record Cashbox Effect
 Record Audit
 Commit
 Receipt/Report

## 2. الشراء

User
 Create Purchase
 Validate
 Check Permission
 Confirm
 Business Event PURCHASE_CONFIRMED
 Increase Stock
 Record Payment / Supplier Credit
 Record Cashbox Effect
 Audit
 Commit

## 3. تحصيل عميل

Customer Payment
 Validate
 Authorization
 Customer Account Movement
 Cashbox/Payment Account Movement
 Audit
 Commit

## 4. سداد مورد

Supplier Payment
 Validate
 Authorization
 Supplier Account Movement
 Cashbox/Payment Account Movement
 Audit
 Commit

## 5. مرتجع بيع

Sale Return
 Validate Original Sale
 Validate Eligible Quantity
 Authorization
 Business Event SALE_RETURN_CREATED
 Reverse Stock Effect
 Reverse Customer/Cash Effect
 Reverse Revenue/COGS Effect
 Audit
 Commit

## 6. مرتجع شراء

Purchase Return
 Validate Original Purchase
 Validate Eligible Quantity
 Authorization
 Business Event PURCHASE_RETURN_CREATED
 Reverse Stock Effect
 Reverse Supplier/Cash Effect
 Audit
 Commit

## 7. المصروف

Expense
 Validate
 Authorization
 Expense Record
 Payment
 Cashbox Effect
 Audit
 Commit

## 8. إغلاق اليوم

Open Business Day
 Execute Operations
 Review
 Close Day
 Audit
 Block Normal Changes

## 9. قاعدة الفشل

أي فشل في خطوة إلزامية قبل Commit:

Rollback
 No Partial Financial Effect

## 10. المبدأ العام

Business Event  Rule  Engine  Effects  Audit  Reports

## الحالة

BPMN BUSINESS FLOWS V1.0  DESIGN BASELINE
