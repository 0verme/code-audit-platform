import time
import unittest

from app.modules.audit.executor import AuditTaskOutcome, BoundedAuditExecutor, ExecutableAuditTask
from app.modules.audit.run import AuditRunState, AuditTask


def executable(key, label=None, *, deps=(), weight=1, handler=None, **kwargs):
    return ExecutableAuditTask(
        task=AuditTask(key, label or key, dependencies=deps, weight=weight),
        handler=handler or (lambda _run: key),
        **kwargs,
    )


class BoundedAuditExecutorTest(unittest.TestCase):
    def test_prerequisites_run_serially_before_parallel_modules(self):
        events = []

        def prereq_one(_run):
            events.append("pre-1")

        def prereq_two(_run):
            events.append("pre-2")

        def module_handler(name):
            def run(_run):
                self.assertEqual(events[:2], ["pre-1", "pre-2"])
                time.sleep(0.05)
                events.append(name)
            return run

        run_state = AuditRunState(run_id=1, workflow="hcyt")
        BoundedAuditExecutor(max_workers=2).run(
            run_state,
            prerequisites=[
                executable("pre-1", handler=prereq_one),
                executable("pre-2", handler=prereq_two),
            ],
            modules=[
                executable("dws", handler=module_handler("dws")),
                executable("hive", handler=module_handler("hive")),
            ],
        )

        self.assertEqual(events[:2], ["pre-1", "pre-2"])
        self.assertEqual(set(events[2:]), {"dws", "hive"})
        self.assertEqual(run_state.status.value, "success")

    def test_independent_modules_run_in_parallel_with_worker_bound(self):
        def slow_module(name):
            def run(_run):
                time.sleep(0.15)
                return AuditTaskOutcome(result=name, summary={"name": name})
            return run

        run_state = AuditRunState(run_id=2, workflow="hcyt")
        start = time.perf_counter()
        BoundedAuditExecutor(max_workers=2).run(
            run_state,
            modules=[
                executable("dws", handler=slow_module("dws")),
                executable("hive", handler=slow_module("hive")),
            ],
        )
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.27)
        self.assertEqual(run_state.get_task("dws").to_dict(include_result=True)["result"], "dws")
        self.assertEqual(run_state.get_task("hive").summary, {"name": "hive"})

    def test_dependency_task_waits_for_dependency_result(self):
        events = []

        def schedule(_run):
            time.sleep(0.05)
            events.append("schedule")
            return AuditTaskOutcome(sections={"schedule": {"rows": [1]}})

        def lineage(run):
            self.assertEqual(run.partial_report["schedule"], {"rows": [1]})
            events.append("lineage")
            return {"lineageSummary": {"resultTables": []}}

        run_state = AuditRunState(run_id=3, workflow="hcyt")
        BoundedAuditExecutor(max_workers=2).run(
            run_state,
            modules=[
                executable("lineage", deps=("schedule",), handler=lineage, result_section="lineage"),
                executable("schedule", handler=schedule),
            ],
        )

        self.assertEqual(events, ["schedule", "lineage"])
        self.assertEqual(run_state.partial_report["lineage"], {"lineageSummary": {"resultTables": []}})

    def test_degradable_module_failure_does_not_stop_other_modules_or_finalizer(self):
        def broken(_run):
            raise ValueError("Excel shape mismatch")

        def finalizer(run):
            return AuditTaskOutcome(
                sections={
                    "finalReport": {
                        "dws": run.get_task("dws").status.value,
                        "schedule": run.get_task("schedule").status.value,
                    }
                },
                summary={"compatible": True},
            )

        run_state = AuditRunState(run_id=4, workflow="hcyt")
        BoundedAuditExecutor(max_workers=2).run(
            run_state,
            modules=[
                executable("dws", handler=lambda _run: ["ok"], result_section="dws"),
                executable("schedule", handler=broken),
            ],
            finalizers=[executable("summary", handler=finalizer)],
        )

        self.assertEqual(run_state.status.value, "success")
        self.assertEqual(run_state.get_task("schedule").status.value, "failed")
        self.assertEqual(run_state.get_task("dws").status.value, "success")
        self.assertEqual(run_state.partial_report["finalReport"], {"dws": "success", "schedule": "failed"})

    def test_failed_dependency_skips_dependent_task(self):
        run_state = AuditRunState(run_id=5, workflow="hcyt")
        BoundedAuditExecutor(max_workers=2).run(
            run_state,
            modules=[
                executable("schedule", handler=lambda _run: (_ for _ in ()).throw(RuntimeError("bad xls"))),
                executable("lineage", deps=("schedule",), handler=lambda _run: "should not run"),
            ],
        )

        self.assertEqual(run_state.get_task("schedule").status.value, "failed")
        self.assertEqual(run_state.get_task("lineage").status.value, "skipped")


if __name__ == "__main__":
    unittest.main()
