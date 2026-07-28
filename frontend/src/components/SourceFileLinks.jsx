import { Icon } from "./ui";
export { getSourceFiles } from "../utils/sourceFilePresentation";

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
