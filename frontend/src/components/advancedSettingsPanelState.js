export function countEnabledAdvancedSettings({ ai = false, dbg = false }) {
  return Number(Boolean(ai)) + Number(Boolean(dbg));
}
