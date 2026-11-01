import { useState } from "react";

export function usePagination(items, itemsPerPage) {
  const [page, setPage] = useState(0);
  const pageCount = Math.ceil(items.length / itemsPerPage);

  const currentItems = items.slice(
    page * itemsPerPage,
    (page + 1) * itemsPerPage
  );

  const goToNext = () => setPage(p => Math.min(p + 1, pageCount - 1));
  const goToPrev = () => setPage(p => Math.max(p - 1, 0));

  const goToPage = (pageIndex) => {
    if (pageIndex >= 0 && pageIndex < pageCount) {
      setPage(pageIndex);
    }
  };

  return { currentItems, page, pageCount, goToNext, goToPrev, goToPage };
}