import { useCallback } from 'react'
import { useAppContext } from '../Contexts/AppContext'
import api from '../api'
import utils from '../utils'

const useSearchHandler = ({
  searchFn,
  workspaceId,
  resourceId = null, // optional second arg like benchmark_id
  searchText = "",
  searchPage = 1,
  searchSize = 10,
  searchSortField,
  searchSortOrder = "asc",
  useAggs = false,
  setDocs,
  setAggs,
  setTotal,
  setLoading,
  setHasEverSearched,
  setIsIndexEmpty,
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  return useCallback(async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    let response
    let total
    try {
      setLoading(true)
      const body = {
        text: searchText,
        page: searchPage,
        size: searchSize,
        aggs: useAggs,
      }
      if (searchSortField && searchSortOrder) {
        body.sort = {
          field: searchSortField,
          order: searchSortOrder,
        }
      }
      if (!workspaceId)
        response = await searchFn(body)
      else if (!resourceId)
        response = await searchFn(workspaceId, body)
      else
        response = await searchFn(workspaceId, resourceId, body)
      total = response?.data?.hits?.total?.value
      setDocs?.(utils.hitsToDocs(response))
      setAggs?.(utils.hitsToAggs(response))
      setTotal?.(total || 0)
    } catch (e) {
      addToast(api.errorToast(e, { title: `Search error` }))
    } finally {
      setLoading(false)
      setHasEverSearched(true)
      setIsIndexEmpty(!searchText && total === 0 ? true : false)
    }
  }, [
    searchFn,
    workspaceId,
    resourceId,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs,
    setDocs,
    setAggs,
    setTotal,
    setLoading,
    setHasEverSearched,
    setIsIndexEmpty,
  ])
}

export default useSearchHandler