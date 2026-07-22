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
        self.assertIn("CAST(taskdate AS DATE)", sql)

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

    def test_normalizes_business_status_codes(self):
        rows = []
        for index, status in enumerate(("生产待审", "运行待审", "开发待审", "等待上线"), start=1):
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

        self.assertEqual([item["status"] for item in payload["items"]], ["pending", "pending", "pending", "passed"])
        self.assertEqual(payload["summary"]["pending"], 3)
        self.assertEqual(payload["summary"]["passed"], 1)


if __name__ == "__main__":
    unittest.main()
