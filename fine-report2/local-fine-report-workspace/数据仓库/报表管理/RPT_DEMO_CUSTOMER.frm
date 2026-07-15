<?xml version="1.0" encoding="UTF-8"?>
<WorkBook>
  <Report class="com.fr.report.worksheet.WorkSheet" name="Demo Customer Report">
    <LayerReportAttr clientPaging="true" engineState="1" />
  </Report>
  <Query>select customer_id, customer_name, email from demo_customer</Query>
  <DatabaseName>demo_reporting</DatabaseName>
  <Attributes dsName="表头" columnName="customer_id" />
</WorkBook>
