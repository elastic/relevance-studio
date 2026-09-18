/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api'
import utils from '../utils'

/**
 * Derive everything that pages need from the displays of a workspace:
 *
 *   - sourceFilters:          the fields to include in the _source of search results
 *   - resolveIndexToDisplay:  the display to render a document of a given index
 *
 * A display can name an alias rather than a concrete index, but documents
 * report the concrete index they live in. So fetch the aliases of the indices
 * of the workspace, which lets a document match a display that names one of
 * its aliases.
 */
const useDisplays = (displays, indexPattern) => {

  ////  State  /////////////////////////////////////////////////////////////////

  const [aliasMap, setAliasMap] = useState({})

  ////  Effects  ///////////////////////////////////////////////////////////////

  useEffect(() => {
    // Drop the aliases of any prior index pattern, so that displays never
    // match a document through the aliases of another workspace.
    setAliasMap((prior) => Object.keys(prior).length ? {} : prior)
    if (!indexPattern)
      return
    let isStale = false;
    (async () => {
      let response
      try {
        // Trim the index pattern, which Elasticsearch would otherwise read
        // as index names with leading whitespace.
        response = await api.content_aliases(utils.splitIndexPatterns(indexPattern).join(','))
      } catch (e) {
        // Fall back to matching displays on index names alone.
        return console.debug(`Failed to get aliases for ${indexPattern}`, e)
      }
      // Ignore a response that lost the race with a newer index pattern.
      if (isStale)
        return
      if (response?.status < 300 && response?.data instanceof Object)
        setAliasMap(response.data)
    })()
    return () => { isStale = true }
  }, [indexPattern])

  ////  Values  ////////////////////////////////////////////////////////////////

  const matchers = useMemo(() => utils.makeDisplayMatchers(displays), [displays])
  const sourceFilters = useMemo(() => utils.makeSourceFilters(displays), [displays])
  const resolveIndexToDisplay = useCallback(
    (index) => utils.resolveIndexToDisplay(matchers, index, aliasMap),
    [matchers, aliasMap]
  )

  return { sourceFilters, resolveIndexToDisplay }
}

export default useDisplays
