import { useCallback, useEffect, useState } from 'react';

/**
 * Generic hook to manage paginated, filterable resources.
 * @param {Object} options
 * @param {Function} options.fetcher - Async function that accepts params and returns { data, total, limit, offset }
 * @param {Object} options.initialFilters - Default filters for the resource
 * @param {boolean} [options.enabled=true] - Controls whether data fetching should be active
 */
const usePaginatedResource = ({ fetcher, initialFilters = {}, enabled = true }) => {
  const [data, setData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: initialFilters.limit ?? 10,
    total: 0,
  });

  const loadData = useCallback(
    async (overrideFilters = {}) => {
      if (!enabled) {
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const params = {
          ...filters,
          ...overrideFilters,
          limit: overrideFilters.limit ?? filters.limit ?? pagination.pageSize,
          offset:
            overrideFilters.offset ?? filters.offset ?? (pagination.current - 1) * pagination.pageSize,
        };

        const result = await fetcher(params);
        setData(result.data ?? result.users ?? result.admins ?? []);
        setPagination((prev) => ({
          ...prev,
          current: Math.floor((result.offset ?? 0) / (result.limit ?? prev.pageSize)) + 1,
          pageSize: result.limit ?? prev.pageSize,
          total: result.total ?? prev.total ?? 0,
        }));
      } catch (fetchError) {
        console.error('Error loading resource:', fetchError);
        setError(fetchError);
      } finally {
        setIsLoading(false);
      }
    },
    [enabled, fetcher, filters, pagination.current, pagination.pageSize]
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }

    loadData();
  }, [enabled, loadData]);

  const handleTableChange = (paginationConfig, newFilters) => {
    const { current, pageSize } = paginationConfig;
    setPagination((prev) => ({
      ...prev,
      current,
      pageSize,
    }));

    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      limit: pageSize,
      offset: (current - 1) * pageSize,
    }));

    loadData({
      limit: pageSize,
      offset: (current - 1) * pageSize,
      ...newFilters,
    });
  };

  const applyFilters = (newFilters) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      offset: 0,
    }));

    setPagination((prev) => ({
      ...prev,
      current: 1,
    }));

    loadData({
      ...newFilters,
      offset: 0,
    });
  };

  const resetFilters = () => {
    setFilters(initialFilters);
    setPagination((prev) => ({
      ...prev,
      current: 1,
      pageSize: initialFilters.limit ?? prev.pageSize,
    }));

    loadData({ ...initialFilters, offset: 0 });
  };

  return {
    data,
    isLoading,
    error,
    filters,
    pagination,
    loadData,
    handleTableChange,
    applyFilters,
    resetFilters,
  };
};

export default usePaginatedResource;
