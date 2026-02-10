/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  EuiButton,
  EuiButtonGroup,
  EuiFieldSearch,
  EuiFilterButton,
  EuiFilterGroup,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiIcon,
  EuiPanel,
  EuiPopover,
  EuiSpacer,
  EuiSelectable,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import { debounce } from 'lodash'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources, useAdditionalResources } from '../../Contexts/ResourceContext'
import {
  Page,
  SearchCount,
  SelectScenario,
  SearchResultsJudgements,
} from '../../Layout'
import api from '../../api'
import utils from '../../utils'
import { getHistory } from '../../history'

const Judgements = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const location = useLocation()
  const history = getHistory()
  const { addToast, darkMode } = useAppContext()
  const { workspace, displays } = usePageResources()
  useAdditionalResources(['displays'])
  const isReady = useResources().hasResources(['workspace', 'displays'])

  ////  Defaults  //////////////////////////////////////////////////////////////

  const defaultFilterOptions = [
    { label: 'All docs', value: 'all' },
    { label: 'Rated docs', value: 'rated' },
    { label: 'Rated by human', value: 'rated-human' },
    { label: 'Rated by AI', value: 'rated-ai' },
    { label: 'Unrated docs', value: 'unrated' }
  ]
  const defaultSortOptions = [
    { label: 'By match', value: 'match' },
    { label: 'By newest ratings', value: 'rating-newest' },
    { label: 'By oldest ratings', value: 'rating-oldest' }
  ]

  ////  State  /////////////////////////////////////////////////////////////////

  const [filterSelected, setFilterSelected] = useState({ label: 'All docs', value: 'all', checked: 'on' })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [filtersOptions, setFiltersOptions] = useState(defaultFilterOptions.map(o => ({ ...o })))
  const [indexPatternMap, setIndexPatternMap] = useState({})
  const [isLoadingResults, setIsLoadingResults] = useState(false)
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false)
  const [isScenariosOpen, setIsScenariosOpen] = useState(false)
  const [numResults, setNumResults] = useState(0)
  const [queryString, setQueryString] = useState('')
  const [results, setResults] = useState([])
  const [resultsPerRow, setResultsPerRow] = useState(3)
  const [scenario, setScenario] = useState(null)
  const [scenarioOptions, setScenarioOptions] = useState([])
  const [scenarioSearchString, setScenarioSearchString] = useState('')
  const [sortOpen, setSortOpen] = useState(false)
  const [sortOptions, setSortOptions] = useState(defaultSortOptions.map(o => ({ ...o })))
  const [sortSelected, setSortSelected] = useState({ label: 'By match', value: 'match', checked: 'on' })
  const [sourceFilters, setSourceFilters] = useState([])

  // Helper to get URL params
  const getUrlParams = () => {
    const params = new URLSearchParams(location.search)
    return {
      scenario: params.get('scenario'),
      filter: params.get('filter'),
      sort: params.get('sort'),
      query: params.get('query')
    }
  }

  // Helper to update URL without adding to history
  const updateUrl = (newParams) => {
    const params = new URLSearchParams(location.search)
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        params.set(key, value)
      } else {
        params.delete(key)
      }
    })
    history.replace(`${location.pathname}?${params.toString()}`)
  }

  ////  Effects  ///////////////////////////////////////////////////////////////

  // Initialize state from URL params
  useEffect(() => {
    const urlParams = getUrlParams()
    if (urlParams.filter) {
      const _filterOptions = defaultFilterOptions.map(obj => ({ ...obj }))
      for (const option of _filterOptions)
        option.checked = option.value === urlParams.filter ? 'on' : undefined
      setFiltersOptions(_filterOptions)
    }
    if (urlParams.sort) {
      const _sortOptions = defaultSortOptions.map(obj => ({ ...obj }))
      for (const option of _sortOptions)
        option.checked = option.value === urlParams.sort ? 'on' : undefined
      setSortOptions(_sortOptions)
    }
    if (urlParams.query)
      setQueryString(urlParams.query)
  }, []) // Only run on mount

  // Search on page load a scenario was given in the URL
  useEffect(() => {
    if (!isReady || !scenario)
      return
    onSearch()
  }, [isReady, scenario])

  /**
   * Get index patterns and source filters from displays
   */
  useEffect(() => {
    if (!displays)
      return
    const _indexPatternMap = {}
    const _sourceFilters = {}
    displays.forEach((display) => {
      _indexPatternMap[display.index_pattern] = {
        display: display,
        regex: new RegExp(`^${display.index_pattern.replace(/\*/g, '.*')}$`)
      }
      display.fields?.forEach((field) => {
        _sourceFilters[field] = true
      })
    })
    setIndexPatternMap(_indexPatternMap)
    setSourceFilters(Object.keys(_sourceFilters))
  }, [displays])

  // Fetch scenarios immediately when opening the dropdown OR when component mounts
  useEffect(() => {
    if (!isReady)
      return

    // Only fetch scenarios when dropdown is open, not when options are empty
    if (isScenariosOpen) {
      onSearchScenarios(`*${scenarioSearchString}*`)
    }
  }, [isReady, isScenariosOpen])

  // Fetch scenarios with debounce when typing
  useEffect(() => {
    if (!isReady)
      return
    const debounced = debounce(() => {
      onSearchScenarios(`*${scenarioSearchString}*`)
    }, 300)
    debounced()
    return () => debounced.cancel()
  }, [scenarioSearchString])

  useEffect(() => {
    if (!isReady || !scenarioOptions)
      return
    const urlParams = getUrlParams()

    // Check if we have a scenario from URL params
    if (urlParams.scenario) {
      for (const option of scenarioOptions) {
        if (option._id === urlParams.scenario) {
          option.checked = 'on'
          setScenario(option)
          setScenarioSearchString(option.label)
          return
        }
      }
    }

    // Otherwise, use the first checked option
    for (const option of scenarioOptions) {
      if (option.checked) {
        setScenario(option)
        setScenarioSearchString(option.checked === 'on' ? option.label : '')
        break
      }
    }
  }, [scenarioOptions])

  // Automatically open the scenarios dropdown if no scenario is given in URL
  useEffect(() => {
    const urlParams = getUrlParams()
    if (!urlParams.scenario)
      setIsScenariosOpen(true)
  }, [])

  // Fetch scenarios on mount to populate options
  useEffect(() => {
    if (!isReady)
      return
    // If we have a scenario in URL but no options loaded yet, fetch scenarios
    const urlParams = getUrlParams()
    if (urlParams.scenario && scenarioOptions.length === 0)
      onSearchScenarios(`*${scenarioSearchString}*`)
  }, [isReady, scenarioOptions.length])

  /**
   * Search when filters or sorts change
   */
  useEffect(() => {
    if (!isReady || !scenario)
      return
    onSearch()
  }, [filterSelected, sortSelected])

  /**
   * Change selected filter when the checked option changes.
   */
  useEffect(() => {
    for (const option of filtersOptions) {
      if (option.checked == 'on') {
        setFilterSelected(option)
        break
      }
    }
  }, [filtersOptions])

  /**
   * Change selected sort when the checked option changes.
   */
  useEffect(() => {
    for (const option of sortOptions) {
      if (option.checked == 'on') {
        setSortSelected(option)
        break
      }
    }
  }, [sortOptions])

  /**
   * Search for scenarios
   */
  const onSearchScenarios = async (text) => {
    try {
      setIsLoadingScenarios(true)
      const response = await api.scenarios_search(workspace._id, { text })
      const urlParams = getUrlParams()
      const options = response.data.hits.hits.map((doc) => ({
        _id: doc._id,
        label: doc._source.name,
        checked: (urlParams.scenario === doc._id) ? 'on' : undefined
      }))
      setScenarioOptions(options)
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to get scenarios' }))
    } finally {
      setIsLoadingScenarios(false)
    }
  }

  /**
   * Handle search bar submission
   */
  const onSearch = (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    (async () => {

      // Submit API request
      const body = {
        index_pattern: workspace.index_pattern,
        query_string: queryString,
      }
      if (filterSelected.value)
        body.filter = filterSelected.value
      if (sortSelected.value)
        body.sort = sortSelected.value
      if (sourceFilters)
        body._source = { includes: sourceFilters }
      let response
      try {
        setIsLoadingResults(true)
        response = await api.judgements_search(workspace._id, scenario._id, body)
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to search docs' }))
      } finally {
        setIsLoadingResults(false)
      }
      if (response.status > 299)
        return addToast(utils.toastClientResponse(response))

      // Handle API response
      if (response?.data?.hits?.hits) {
        setResults(response.data.hits.hits)
        setNumResults(response.data.hits.total.value)
      }
    })()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderSelectScenarios = () => (
    <SelectScenario
      autoFocus={!getUrlParams().scenario}
      isLoading={isLoadingScenarios}
      isOpen={isScenariosOpen}
      options={scenarioOptions}
      searchString={scenarioSearchString}
      setSearchString={setScenarioSearchString}
      setIsLoading={setIsLoadingScenarios}
      setIsOpen={setIsScenariosOpen}
      setOptions={setScenarioOptions}
    />
  )

  const renderSelectFilters = () => (
    <EuiSelectable
      options={filtersOptions}
      onChange={(newOptions, event, changedOption) => {
        setFiltersOptions(newOptions)

        // Update URL when user changes filter
        updateUrl({ filter: changedOption.value !== 'all' ? changedOption.value : null })

        // Filtering by unrated docs requires sorting not by anything with ratings
        if (changedOption.value == 'unrated') {
          setSortOptions(prev => {
            const newOptions = defaultSortOptions.map(obj => ({ ...obj }))
            for (const obj of newOptions) {
              if (obj.value === 'match') {
                obj.checked = 'on'
                break
              }
            }
            return newOptions
          })
        }
        setFiltersOpen(false)
      }}
      singleSelection
      listProps={{
        css: { '.euiSelectableList__list': { maxBlockSize: 200 } },
      }}
    >
      {(list, search) => (
        <div style={{ width: 300 }}>
          {list}
        </div>
      )}
    </EuiSelectable>
  )

  const renderSelectSort = () => (
    <EuiSelectable
      options={sortOptions}
      onChange={(newOptions, event, changedOption) => {
        setSortOptions(newOptions)

        // Update URL when user changes sort
        updateUrl({ sort: changedOption.value !== 'match' ? changedOption.value : null })

        // Sorting by anything with ratings requires filtering by rated docs
        if (changedOption.value.startsWith('rating') && !filterSelected.value.startsWith('rated')) {
          setFiltersOptions(prev => {
            const newOptions = defaultFilterOptions.map(obj => ({ ...obj }))
            for (const obj of newOptions) {
              if (obj.value === 'rated') {
                obj.checked = 'on'
                break
              }
            }
            return newOptions
          })
        }
        setSortOpen(false)
      }}
      singleSelection
      listProps={{
        css: { '.euiSelectableList__list': { maxBlockSize: 200 } },
      }}
    >
      {(list, search) => (
        <div style={{ width: 300 }}>
          {list}
        </div>
      )}
    </EuiSelectable>
  )

  const renderResults = () => (
    <SearchResultsJudgements
      displays={displays}
      indexPatternMap={indexPatternMap}
      workspace={workspace}
      scenario={scenario}
      results={results}
      resultsPerRow={resultsPerRow}
    />
  )

  return (
    <Page title='Judgements' color='subdued'>
      <EuiFlexGroup gutterSize='m' alignItems='flexStart'>
        <EuiFlexItem grow>

          {/* Top bar */}
          <EuiForm
            component='form'
            onSubmit={onSearch}
            style={{
              margin: '-16px -20px 10px -20px',
              position: 'sticky',
              top: '-16px',
              zIndex: 9
            }}
          >
            <EuiFlexItem style={{
              boxShadow: darkMode ? '0 10px 10px -10px rgba(0, 0, 0, 1)' : '0 10px 10px -10px rgba(0, 0, 0, 0.25)',
            }}>
              <EuiPanel
                hasBorder={false}
                hasShadow={false}
                paddingSize='none'
                style={{ borderRadius: 0, padding: '24px 24px 10px 24px' }}
              >
                <EuiFlexGroup gutterSize='s'>

                  {/* Select scenario */}
                  <EuiFlexItem grow={2}>
                    <EuiFormRow fullWidth label='Scenario'>
                      {renderSelectScenarios()}
                    </EuiFormRow>
                  </EuiFlexItem>

                  {/* Search */}
                  <EuiFlexItem grow={8}>
                    {!!scenario &&
                      <EuiFormRow fullWidth label='Search'>
                        <EuiFlexGroup gutterSize='s'>

                          {/* Search bar */}
                          <EuiFlexItem grow={5}>
                            <EuiFieldSearch
                              fullWidth
                              placeholder="Find documents..."
                              value={queryString}
                              onChange={(e) => setQueryString(e.target.value)}
                            />
                          </EuiFlexItem>

                          {/* Filter and sort */}
                          <EuiFlexItem grow={4}>
                            <EuiFilterGroup>

                              {/* Filter */}
                              <EuiPopover
                                button={
                                  <EuiFilterButton
                                    iconType='arrowDown'
                                    onClick={(e) => setFiltersOpen(!filtersOpen)}
                                    isSelected={filtersOpen}
                                  >
                                    {filterSelected.label}
                                  </EuiFilterButton>
                                }
                                closePopover={(e) => setFiltersOpen(false)}
                                isOpen={filtersOpen}
                                panelPaddingSize='none'
                                style={{ width: '50%' }}
                              >
                                {renderSelectFilters()}
                              </EuiPopover>

                              {/* Sort */}
                              <EuiPopover
                                button={
                                  <EuiFilterButton
                                    iconType='arrowDown'
                                    onClick={(e) => setSortOpen(!sortOpen)}
                                    isSelected={sortOpen}
                                  >
                                    {sortSelected.label}
                                  </EuiFilterButton>
                                }
                                closePopover={(e) => setSortOpen(false)}
                                isOpen={sortOpen}
                                panelPaddingSize='none'
                                style={{ width: '50%' }}
                              >
                                {renderSelectSort()}
                              </EuiPopover>

                            </EuiFilterGroup>
                          </EuiFlexItem>

                          {/* Search submit button */}
                          <EuiFlexItem grow={1}>
                            <EuiButton
                              isLoading={isLoadingResults}
                              iconType='search'
                              type='submit'
                            >
                              Search
                            </EuiButton>
                          </EuiFlexItem>
                        </EuiFlexGroup>
                      </EuiFormRow>
                    }
                  </EuiFlexItem>
                </EuiFlexGroup>

                {/* Show number of results and change grid size */}
                <EuiSpacer size='s' />
                {!!results.length &&
                  <EuiFlexGroup alignItems='center' gutterSize='s'>

                    {/* Show number of results */}
                    <EuiFlexItem grow={5}>
                      <SearchCount showing={results.length} total={numResults} />
                    </EuiFlexItem>

                    {/* Change grid size */}
                    <EuiFlexItem grow={5}>
                      <EuiText color='subdued' size='xs' style={{ textAlign: 'right' }}>
                        <EuiIcon
                          color='subdued'
                          type='grid'
                          size='xs'
                          style={{ marginRight: '6px' }}
                        />
                        <EuiToolTip content='Change grid size' position='bottom'>
                          <EuiButtonGroup
                            buttonSize='compressed'
                            prepend='Grid size'
                            idSelected={`grid-size-${resultsPerRow}`}
                            legend='Grid size'
                            onChange={(id) => setResultsPerRow(id.slice(-1))}
                            options={[
                              { id: 'grid-size-1', label: <EuiText size='xs'><small>1</small></EuiText> },
                              { id: 'grid-size-2', label: <EuiText size='xs'><small>2</small></EuiText> },
                              { id: 'grid-size-3', label: <EuiText size='xs'><small>3</small></EuiText> },
                              { id: 'grid-size-4', label: <EuiText size='xs'><small>4</small></EuiText> }
                            ]}
                          />
                        </EuiToolTip>
                      </EuiText>
                    </EuiFlexItem>
                  </EuiFlexGroup>
                }
              </EuiPanel>
            </EuiFlexItem>
          </EuiForm>

          <EuiSpacer size='s' />

          {/* Display results */}
          <EuiFlexItem>
            {!!results.length &&
              renderResults()
            }
          </EuiFlexItem>
        </EuiFlexItem>
      </EuiFlexGroup>
    </Page>
  )
}

export default Judgements