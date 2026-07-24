import { Icon } from "./ui";

export function getSourceFiles(data, section, kinds = null) {
  const allowedKinds = kinds ? new Set(kinds) : null;
  return (Array.isArray(data?.sourceFiles) ? data.sourceFiles : []).filter((file) => (
    file?.section === section
    && file.downloadUrl
    && (!allowedKinds || allowedKinds.has(file.kind))
  ));
}

export function SourceFileLinks({ files = [], label = "源文件" }) {
  if (!files.length) return null;
  return (
    <div className="script-bar source-file-links">
      <Icon name="file" size={12} /> {label}：
      {files.map((file) => (
        <a
          key={`${file.kind}-${file.path}`}
          className="dl-link"
          href={file.downloadUrl}
          target="_blank"
          rel="noreferrer"
          title={file.path}
        >
          <Icon name="download" size={12} /> {file.name}
        </a>
      ))}
    </div>
  );
}
