<?xml version="1.0" encoding="UTF-8"?>
<WorkBook>
  <Report class="com.fr.report.worksheet.WorkSheet" name="Demo Customer Report">
    <LayerReportAttr clientPaging="true" engineState="1" />
    <ATTR DIVIDEMODE="1"/>
  </Report>
  <Query><![CDATA[
select T.CUSTOMER_ID, T.CERT_NO, T.EMAIL
from DWF.F_FINE_CUSTOMER T
where T.ORG_ID = '${权限机构树}'
  ]]></Query>
  <DatabaseName>demo_reporting</DatabaseName>
  <Attributes dsName="表头" columnName="customer_id" />
</WorkBook>
