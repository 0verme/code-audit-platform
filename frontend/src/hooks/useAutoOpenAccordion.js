import { useEffect, useState } from "react";

export function syncAutoOpenIds(
  currentIds,
  items,
  dismissedIds,
  getKey,
  isActionable,
) {
  const next = new Set(currentIds);
  let changed = false;

  for (const item of Array.isArray(items) ? items : []) {
    const itemKey = getKey(item);
    if (
      itemKey &&
      isActionable(item) &&
      !dismissedIds.has(itemKey) &&
      !next.has(itemKey)
    ) {
      next.add(itemKey);
      changed = true;
    }
  }

  return changed ? next : currentIds;
}

export function toggleAccordionId(currentIds, itemId, dismissedIds) {
  const next = new Set(currentIds);
  if (next.has(itemId)) {
    next.delete(itemId);
    dismissedIds.add(itemId);
  } else {
    next.add(itemId);
    dismissedIds.delete(itemId);
  }
  return next;
}

export function closeAccordionIds(currentIds, dismissedIds) {
  currentIds.forEach((itemId) => dismissedIds.add(itemId));
  return new Set();
}

export function openAccordionId(currentIds, itemId, dismissedIds) {
  dismissedIds.delete(itemId);
  if (currentIds.has(itemId)) return currentIds;
  const next = new Set(currentIds);
  next.add(itemId);
  return next;
}

export function useAutoOpenAccordion({
  items,
  getKey,
  isActionable,
  jumpRequest,
  getElementId,
}) {
  const [dismissedIds] = useState(() => new Set());
  const [openIds, setOpenIds] = useState(() =>
    syncAutoOpenIds(new Set(), items, dismissedIds, getKey, isActionable),
  );

  const toggle = (itemId) => {
    setOpenIds((current) => toggleAccordionId(current, itemId, dismissedIds));
  };

  useEffect(() => {
    setOpenIds((current) =>
      syncAutoOpenIds(current, items, dismissedIds, getKey, isActionable),
    );
  }, [dismissedIds, getKey, isActionable, items]);

  useEffect(() => {
    const closeAll = (event) => {
      if (event.key !== "Escape") return;
      setOpenIds((current) => closeAccordionIds(current, dismissedIds));
    };
    window.addEventListener("keydown", closeAll);
    return () => window.removeEventListener("keydown", closeAll);
  }, [dismissedIds]);

  useEffect(() => {
    const itemKey = jumpRequest?.key;
    if (!itemKey) return;

    setOpenIds((current) => openAccordionId(current, itemKey, dismissedIds));

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.getElementById(getElementId(itemKey))?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    });
  }, [dismissedIds, getElementId, jumpRequest]);

  return { openIds, toggle };
}
