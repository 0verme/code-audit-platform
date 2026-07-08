import { useState } from "react";
import { Icon } from "./ui";
import { countEnabledAdvancedSettings } from "./advancedSettingsPanelState";

function ToggleRow({ on, onChange, label, desc, icon }) {
  return (
    <button type="button" className="row-toggle" onClick={() => onChange(!on)}>
      <span className="rt-ico">
        <Icon name={icon} size={16} />
      </span>
      <span className="rt-text">
        <span className="rt-label">{label}</span>
        <span className="rt-desc">{desc}</span>
      </span>
      <span className={`switch${on ? " on" : ""}`}>
        <span className="knob" />
      </span>
    </button>
  );
}

export function AdvancedSettingsPanel({
  ai,
  dbg,
  onAiChange,
  onDbgChange,
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const enabledCount = countEnabledAdvancedSettings({ ai, dbg });

  return (
    <section className={`advanced-settings${open ? " open" : ""}`}>
      <button
        type="button"
        className="advanced-settings-trigger"
        onClick={() => setOpen((current) => !current)}
      >
        <span className="advanced-settings-icon">
          <Icon name="cog" size={16} />
        </span>
        <span className="advanced-settings-copy">
          <span className="advanced-settings-title">高级设置</span>
          <span className="advanced-settings-subtitle">
            本地 AI、调试日志等低频选项
          </span>
        </span>
        <span className="advanced-settings-meta">
          {enabledCount ? (
            <span className="advanced-settings-count">
              已开启 {enabledCount} 项
            </span>
          ) : null}
          <Icon
            name="chevron"
            size={16}
            className="advanced-settings-chevron"
          />
        </span>
      </button>

      {open ? (
        <div className="advanced-settings-body">
          <div className="toggles">
            <ToggleRow
              on={ai}
              onChange={onAiChange}
              icon="sparkle"
              label="接入本地 AI 大模型"
              desc="启用后追加 AI 语义分析与修复建议（默认关闭）。"
            />
            <ToggleRow
              on={dbg}
              onChange={onDbgChange}
              icon="terminal"
              label="调试日志"
              desc="输出检测、分类与规则执行的详细日志（默认关闭）。"
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
