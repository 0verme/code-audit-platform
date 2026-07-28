export function getSourceFiles(data, section, kinds = null) {
  const allowedKinds = kinds ? new Set(kinds) : null;
  return (Array.isArray(data?.sourceFiles) ? data.sourceFiles : []).filter((file) => (
    file?.section === section
    && file.downloadUrl
    && (!allowedKinds || allowedKinds.has(file.kind))
  ));
}
