import { Icon } from "./ui";

const TABLE_TYPE_META = {
  result: { className: "result" },
  mid: { className: "mid" },
  src: { className: "src" },
  temp: { className: "temp" },
};

function normalizeItem(item) {
  if (typeof item === "string") return { name: item };
  return item || {};
}

export function ReferenceTableList({ items = [], emptyText = "无" }) {
  if (!items.length) return <div className="sd-empty">{emptyText}</div>;

  return (
    <div className="chips">
      {items.map((rawItem, index) => {
        const item = normalizeItem(rawItem);
        const type = TABLE_TYPE_META[item.type] || TABLE_TYPE_META.src;
        const notes = [
          item.disabled ? "禁用" : null,
          item.sysNames?.length ? item.sysNames.join("/") : null,
        ].filter(Boolean);
        return (
          <span key={`${item.name || "table"}-${index}`} className={`chip ${type.className}`}>
            <span className="cdot" />
            <span className="mono">{item.name || "未命名表"}</span>
            {notes.length ? <span>（{notes.join(" / ")}）</span> : null}
            {item.disabled ? <Icon name="alert" size={11} /> : null}
          </span>
        );
      })}
    </div>
  );
}
