from __future__ import annotations


def select_hcyt_ai_targets(*, py_lists, dws_url):
    return py_lists or ([dws_url] if dws_url else [])


def run_hcyt_ai_review(*, py_lists, dws_url, errors, warnings, ai_enabled, update_progress, build_ai):
    update_progress(progress=85, step="AI 分析" if ai_enabled else "汇总报告")
    return build_ai(select_hcyt_ai_targets(py_lists=py_lists, dws_url=dws_url), errors, warnings)
