-- ===========================================================================
-- 代码审查平台 / svn_check 规则引擎所需的元数据表（Postgres）
-- 表名规范：schema = dwp，表名 p_ 开头（与 GaussDB 生产保持一致）
-- 全部 IF NOT EXISTS，可重复执行；列名沿用生产的 a/b/c... 占位命名。
-- ===========================================================================

CREATE SCHEMA IF NOT EXISTS dwp;

-- 作业表：代码用 `select *` 并按下标取值，需保持列顺序
--   a[0]=计划名  b[1]=作业流名  c[2]=作业名  e[4]=程序KEY(关联 p_program_hjj.b)
--   x[23]=状态(1启用/9禁用)  ab[27]=前置依赖串(形如 33:JOBNAME|...)
CREATE TABLE IF NOT EXISTS dwp.p_job_hjj (
    a  text, b  text, c  text, d  text, e  text, f  text, g  text,
    h  text, i  text, j  text, k  text, l  text, m  text, n  text,
    o  text, p  text, q  text, r  text, s  text, t  text, u  text,
    v  text, w  text, x  integer, y  text, z  text, aa text, ab text
);
-- x 是状态码（1启用/9禁用），整数列以兼容规则中 `j.x in (9,'9')` 的写法。
-- 老表若 x 为 text，下面 DO 块自动转换（空表/可空安全）。
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='dwp' AND table_name='p_job_hjj'
      AND column_name='x' AND data_type <> 'integer'
  ) THEN
    EXECUTE 'ALTER TABLE dwp.p_job_hjj ALTER COLUMN x TYPE integer USING NULLIF(x::text,'''')::integer';
  END IF;
END $$;

-- 加工程序表：a..j 常规取值；b=程序KEY(被 p_job_hjj.e 关联)；k=结果表(substr(k,5))
CREATE TABLE IF NOT EXISTS dwp.p_program_hjj (
    a text, b text, c text, d text, e text, f text,
    g text, h text, i text, j text, k text
);

-- 计划表：select a,b,c,d,e,f
CREATE TABLE IF NOT EXISTS dwp.p_plan_hjj (
    a text, b text, c text, d text, e text, f text
);

-- 角色表：select *（代码取 [0] 角色名）
CREATE TABLE IF NOT EXISTS dwp.p_role_hjj (
    a text
);

-- 帆软报表目录表：select *（代码取 [0] 报表名）
CREATE TABLE IF NOT EXISTS dwp.p_fine_hjj (
    a text
);

-- 卸数路径表：select a,b
CREATE TABLE IF NOT EXISTS dwp.p_job_outfile (
    a text, b text
);

-- 码值参数表清单
CREATE TABLE IF NOT EXISTS dwp.p_para_table_lists (
    para_table_name text
);

-- 卸数结果表（关联 recv_plan）
CREATE TABLE IF NOT EXISTS dwp.p_recv_dwf (
    table_name text, recv_plan text
);

-- 卸数计划与来源系统映射
CREATE TABLE IF NOT EXISTS dwp.p_recv_ops_mapping (
    recv_plan text, sys_name text
);

-- 词根表
CREATE TABLE IF NOT EXISTS dwp.p_term_root (
    root_code text
);
