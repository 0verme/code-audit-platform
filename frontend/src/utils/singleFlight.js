export function createSingleFlight() {
  let activePromise = null;

  return {
    run(operation) {
      if (activePromise) return activePromise;

      activePromise = Promise.resolve()
        .then(operation)
        .finally(() => {
          activePromise = null;
        });
      return activePromise;
    },
  };
}
