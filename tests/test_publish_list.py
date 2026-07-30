import sys
import unittest
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.publish_list_service import PublishListConfigurationError, get_publish_list  # noqa: E402


class FakeProfile:
    config = {
        "schema": "dwp",
        "metadata": {
            "tables": {"publish_list": "p_publishlist"},
            "columns": {
                "publish_list": {
                    "id": "req_id",
                    "title": "req_title",
                    "status": "publish_status",
                    "date": "publish_date",
                    "owner": "developer",
                }
            },
        },
    }


class AutoMappedProfile:
    config = {"schema": "dwp"}


class FakeRunner:
    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows
        self.queries = []

    def query_all(self, sql, params=None):
        self.queries.append((sql, params))
        if "information_schema.columns" in sql:
            return [{"column_name": column} for column in self.columns]
        return self.rows


class PublishListServiceTests(unittest.TestCase):
    def test_auto_maps_task_columns_from_test_table_schema(self):
        columns = ["taskid", "tasktype", "taskuer", "tasktitle", "taskstatus", "taskdate", "tasksource", "taskremark"]
        runner = FakeRunner(columns, [])

        get_publish_list(date(2026, 7, 22), profile=AutoMappedProfile(), runner=runner)

        sql = runner.queries[1][0]
        self.assertIn("taskid AS id", sql)
        self.assertIn("taskuer AS owner", sql)
        self.assertIn("taskremark AS remark", sql)
        self.assertIn("WHERE taskdate = ?", sql)
        self.assertNotIn("CAST(", sql)
        self.assertIn("ORDER BY taskid LIMIT 1000", sql)

    def test_maps_profile_columns_and_normalizes_rows(self):
        runner = FakeRunner(
            ["req_id", "req_title", "publish_status", "publish_date", "developer", "taskremark"],
            [{
                "id": "REQ-1", "type": None, "owner": "张三", "title": "上线需求",
                "status": "已通过", "date": date(2026, 7, 22), "time": None,
                "source": None, "remark": "测试备注", "detail_url": "javascript:alert(1)",
            }],
        )
        payload = get_publish_list(date(2026, 7, 22), profile=FakeProfile(), runner=runner)

        self.assertEqual(payload["items"][0]["status"], "passed")
        self.assertEqual(payload["items"][0]["date"], "2026-07-22")
        self.assertEqual(payload["items"][0]["detailUrl"], "")
        self.assertEqual(payload["items"][0]["remark"], "测试备注")
        self.assertEqual(payload["summary"]["passed"], 1)
        self.assertIn("FROM dwp.p_publishlist", runner.queries[1][0])
        self.assertEqual(runner.queries[1][1], ("2026-07-22",))

    def test_rejects_incomplete_field_mapping(self):
        runner = FakeRunner(["req_id", "req_title"], [])
        with self.assertRaises(PublishListConfigurationError):
            get_publish_list(date(2026, 7, 22), profile=FakeProfile(), runner=runner)

    def test_uses_http_detail_field_as_new_window_link(self):
        runner = FakeRunner(
            ["req_id", "req_title", "publish_status", "publish_date", "developer", "taskremark"],
            [{
                "id": "REQ-1", "type": None, "owner": None, "title": "演示",
                "status": "审核中", "date": date(2026, 7, 22), "time": None,
                "source": None, "remark": "https://example.com/detail/REQ-1", "detail_url": None,
            }],
        )

        payload = get_publish_list(date(2026, 7, 22), profile=FakeProfile(), runner=runner)

        self.assertEqual(payload["items"][0]["detailUrl"], "https://example.com/detail/REQ-1")

    def test_normalizes_business_status_codes(self):
        rows = []
        for index, status in enumerate(("生产待审", "运行待审", "开发待审", "待审核", "待审查", "等待上线"), start=1):
            rows.append({
                "id": f"REQ-{index}", "type": None, "owner": None, "title": "演示",
                "status": status, "date": date(2026, 7, 22), "time": None,
                "source": None, "remark": None, "detail_url": None,
            })
        runner = FakeRunner(
            ["req_id", "req_title", "publish_status", "publish_date", "developer"],
            rows,
        )

        payload = get_publish_list(date(2026, 7, 22), profile=FakeProfile(), runner=runner)

        statuses_by_id = {item["id"]: item["status"] for item in payload["items"]}
        self.assertEqual(statuses_by_id, {
            "REQ-1": "reviewing", "REQ-2": "reviewing", "REQ-3": "reviewing",
            "REQ-4": "reviewing", "REQ-5": "reviewing", "REQ-6": "passed",
        })
        self.assertEqual(
            [item["statusLabel"] for item in payload["items"] if item["status"] == "reviewing"],
            ["审核中"] * 5,
        )
        self.assertEqual(payload["summary"]["pending"], 0)
        self.assertEqual(payload["summary"]["reviewing"], 5)
        self.assertEqual(payload["summary"]["passed"], 1)

    def test_sorts_by_business_status_then_requirement_type(self):
        rows = [
            {"id": "REQ-1", "type": "运行维护", "owner": None, "title": "演示", "status": "审核中", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-2", "type": "数据修改", "owner": None, "title": "演示", "status": "等待上线", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-3", "type": "开发维护", "owner": None, "title": "演示", "status": "等待上线", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-4", "type": "数据修改", "owner": None, "title": "演示", "status": "开发待审", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-5", "type": "开发维护", "owner": None, "title": "演示", "status": "开发待审", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-6", "type": "开发维护", "owner": None, "title": "演示", "status": "已上线", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-7", "type": "数据修改", "owner": None, "title": "演示", "status": "处理完成", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-8", "type": "运行维护", "owner": None, "title": "演示", "status": "处理中", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
        ]
        runner = FakeRunner(
            ["req_id", "req_title", "publish_status", "publish_date", "developer", "requirement_type"],
            rows,
        )

        payload = get_publish_list(date(2026, 7, 22), profile=FakeProfile(), runner=runner)

        self.assertEqual([item["id"] for item in payload["items"]], ["REQ-3", "REQ-2", "REQ-7", "REQ-5", "REQ-4", "REQ-1", "REQ-8", "REQ-6"])

    def test_normalizes_processing_statuses_and_counts_them_separately(self):
        rows = [
            {"id": "REQ-1", "type": "开发维护", "owner": None, "title": "演示", "status": "处理中", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
            {"id": "REQ-2", "type": "运行维护", "owner": None, "title": "演示", "status": "处理完成", "date": date(2026, 7, 22), "time": None, "source": None, "remark": None, "detail_url": None},
        ]
        runner = FakeRunner(
            ["req_id", "req_title", "publish_status", "publish_date", "developer", "requirement_type"],
            rows,
        )

        payload = get_publish_list(date(2026, 7, 22), profile=FakeProfile(), runner=runner)

        self.assertEqual([item["status"] for item in payload["items"]], ["completed", "processing"])
        self.assertEqual(payload["summary"]["processing"], 1)
        self.assertEqual(payload["summary"]["completed"], 1)
        self.assertEqual(payload["summary"]["launched"], 0)


if __name__ == "__main__":
    unittest.main()
