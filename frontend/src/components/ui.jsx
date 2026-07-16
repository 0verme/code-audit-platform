import { useEffect, useRef, useState } from "react";

export const Ic = {
  chevron: <path d="M9 6l6 6-6 6" />,
  check: <path d="M20 6L9 17l-5-5" />,
  x: <path d="M18 6L6 18M6 6l12 12" />,
  alert: <><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 16v-4M12 8h.01" /></>,
  folder: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></>,
  git: <><circle cx="6" cy="6" r="2.5" /><circle cx="6" cy="18" r="2.5" /><circle cx="18" cy="9" r="2.5" /><path d="M18 11.5v1A3.5 3.5 0 0 1 14.5 16H6M6 8.5v7" /></>,
  branch: <><line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M18 9a9 9 0 0 1-9 9" /></>,
  db: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></>,
  terminal: <><path d="M4 17l6-5-6-5M12 19h8" /></>,
  code: <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />,
  python: <path d="M9 3h6M9 21h6M4 8h8a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2h4M20 16h-8a2 2 0 0 1-2-2v-4a2 2 0 0 0-2-2H4" />,
  cog: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" /></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  layers: <path d="M12 2l9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5" />,
  sparkle: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" />,
  link: <><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1" /><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1" /></>,
  flow: <><rect x="3" y="3" width="6" height="6" rx="1" /><rect x="15" y="9" width="6" height="6" rx="1" /><rect x="3" y="15" width="6" height="6" rx="1" /><path d="M9 6h3a2 2 0 0 1 2 2v1M9 18h3a2 2 0 0 0 2-2v-1" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
  play: <path d="M6 4l14 8-14 8V4z" />,
  download: <><path d="M12 3v12M7 10l5 5 5-5" /><path d="M5 21h14" /></>,
  copy: <><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></>,
  conflict: <><path d="M12 2v6M12 16v6M2 12h6M16 12h6" /><circle cx="12" cy="12" r="3" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
  gauge: <><path d="M12 13l4.5-4.5" /><path d="M4 19a8 8 0 1 1 16 0" /><circle cx="12" cy="13" r="1.3" /></>,
  shield: <path d="M12 3l8 3v5.5c0 4.6-3.2 7.7-8 9.2-4.8-1.5-8-4.6-8-9.2V6z" />,
  screen: <><rect x="3" y="4" width="18" height="13" rx="1.5" /><path d="M8 21h8M12 17v4" /><path d="M7 13l3-3 2 2 4-4" /></>,
  menu: <><path d="M3 6h18M3 12h18M3 18h18" /></>,
};

export function Icon({ name, size = 16, stroke = 1.8, className = "", style }) {
  return (
    <svg className={className} style={style} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
      {Ic[name] || null}
    </svg>
  );
}

export const LEVEL_META = {
  err: { cls: "err", label: "错误", icon: "x" },
  warn: { cls: "warn", label: "警告", icon: "alert" },
  info: { cls: "info", label: "提示", icon: "info" },
  ok: { cls: "ok", label: "通过", icon: "check" },
};

export function Sev({ level }) {
  const meta = LEVEL_META[level] || LEVEL_META.info;
  return (
    <span className={`sev ${meta.cls}`}>
      <Icon name={meta.icon} size={13} stroke={2.2} />
      {meta.label}
    </span>
  );
}

export function Badge({ tone, mono, lg, icon, children }) {
  return (
    <span className={`badge${tone ? ` ${tone}` : ""}${mono ? " mono" : ""}${lg ? " lg" : ""}`}>
      {icon ? <Icon name={icon} size={12} stroke={2.2} /> : null}
      {children}
    </span>
  );
}

export function Dot({ tone, pulse }) {
  return <span className={`dot${tone ? ` ${tone}` : ""}${pulse ? " pulse" : ""}`} />;
}

export function levelOf(rows) {
  if (!rows || !rows.length) return null;
  if (rows.some((row) => row.level === "err")) return "err";
  if (rows.some((row) => row.level === "warn")) return "warn";
  return "ok";
}

export function Panel({ id, icon, title, sub, right, count, countTone, accentHeader = false, defaultOpen = true, registerRef, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const ref = useRef(null);

  useEffect(() => {
    if (registerRef) {
      registerRef(id, ref, setOpen);
    }
  }, [id, registerRef]);

  return (
    <section className={`panel${accentHeader ? " accent-header" : ""}${open ? " open" : ""}`} ref={ref} id={`sec-${id}`}>
      <div className="panel-head" onClick={() => setOpen((current) => !current)}>
        <Icon name="chevron" size={15} className="panel-chev" />
        {icon ? <span className="panel-ico"><Icon name={icon} size={16} /></span> : null}
        <span className="panel-title">{title}</span>
        {sub ? <span className="panel-sub">{sub}</span> : null}
        <span className="panel-head-spacer" />
        {right}
        {count != null ? <Badge tone={countTone} mono>{count}</Badge> : null}
      </div>
      {open ? <div className="panel-body-wrap fade-in">{children}</div> : null}
    </section>
  );
}

export function ViolationTable({ rows, cols }) {
  const columns = cols || [
    { key: "file", label: "文件", cls: "file-cell" },
    { key: "line", label: "行号", cls: "num" },
    { key: "rule", label: "规则", cls: "rule-cell" },
    { key: "level", label: "级别", cls: "severity-cell", width: 84, minWidth: 84 },
    { key: "msg", label: "说明" },
  ];
  return (
    <div className="table-wrap">
      <table className="tbl">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={column.cls === "num" ? "num" : column.cls || ""}
                style={column.width || column.minWidth ? { width: column.width, minWidth: column.minWidth } : undefined}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.file || row.item}-${index}`} className={row.level === "err" ? "err-row" : row.level === "warn" ? "warn-row" : ""}>
              {columns.map((column) => (
                <td key={column.key} className={column.cls || ""}>
                  {column.key === "level" ? (
                    <Sev level={row.level} />
                  ) : column.key === "file" ? (
                    <span className="mono">{row[column.key]}</span>
                  ) : (
                    row[column.key]
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OkState({ children }) {
  return (
    <div className="okstate">
      <Icon name="check" size={16} stroke={2.4} className="okic" />
      <span>{children}</span>
    </div>
  );
}

export function Metric({ label, value, unit, tone, icon }) {
  return (
    <div className="metric">
      <span className="m-label">{icon ? <Icon name={icon} size={12} /> : null}{label}</span>
      <span className={`m-value${tone ? ` ${tone}` : ""}`}>{value}{unit ? <span className="m-unit"> {unit}</span> : null}</span>
    </div>
  );
}
