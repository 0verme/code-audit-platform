export const CHANGE_LIST_DEFAULT_OPEN_LIMIT = 10;

export function shouldDefaultOpenChangeList(changeCount) {
  return changeCount <= CHANGE_LIST_DEFAULT_OPEN_LIMIT;
}
