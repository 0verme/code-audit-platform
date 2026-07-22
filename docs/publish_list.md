# 当日上线清单数据库说明

`dwp.p_publishlist.taskdate` 使用 `YYYY-MM-DD` 文本格式。接口使用文本等值条件查询，避免对列执行 `CAST` 后导致普通索引失效。

测试或生产环境由数据库管理员执行以下 DDL；应用启动时不会自动修改该业务表：

```sql
CREATE INDEX IF NOT EXISTS idx_p_publishlist_taskdate_taskid
ON dwp.p_publishlist (taskdate, taskid);

ANALYZE dwp.p_publishlist;
```

上线清单使用独立的只读自动提交连接池，避免只读请求结束时产生额外的远程事务回滚开销；归还连接时仍执行回滚清理，不改变平台其他数据库访问路径。可通过 `PUBLISH_LIST_READ_POOL_SIZE` 调整每个数据库 profile 的池大小，默认值为 `4`。字段映射缓存时间为 5 分钟，业务查询结果不缓存。
