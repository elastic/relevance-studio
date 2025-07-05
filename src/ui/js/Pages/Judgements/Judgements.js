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
import { usePageResources } from '../../Contexts/ResourceContext'
import {
  Page,
  SearchCount,
  SelectScenario,
  SearchResultsJudgements,
} from '../../Layout'
import api from '../../api'

const Judgements = () => {

  const location = useLocation()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast, darkMode } = useAppContext()
  const { project } = usePageResources()

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

  const [displays, setDisplays] = useState({})
  const [filterSelected, setFilterSelected] = useState({ label: 'All docs', value: 'all', checked: 'on' })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [filtersOptions, setFiltersOptions] = useState(defaultFilterOptions.map(o => ({ ...o })))
  const [indexPatternRegexes, setIndexPatternRegexes] = useState({})
  const [isLoadingDisplays, setIsLoadingDisplays] = useState(false)
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

  /**
   * Get displays for project
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoadingDisplays(true)
        response = await api.displays_search(project._id, { text: '*' })
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to get displays' }))
      } finally {
        setIsLoadingDisplays(false)
      }

      // Handle API response
      const _displays = {}
      const _fields = {}
      const _indexPatternsRegexes = {}
      response.data.hits.hits?.forEach((doc) => {
        _displays[doc._source.index_pattern] = doc._source
        doc._source.fields?.forEach((field) => {
          _fields[field] = true
        })
      })
      for (var index_pattern in _displays) {
        const re = new RegExp(`^${index_pattern.replace(/\*/g, '.*')}$`)
        _indexPatternsRegexes[index_pattern] = re
      }
      setDisplays(_displays)
      setIndexPatternRegexes(_indexPatternsRegexes)
      setSourceFilters(Object.keys(_fields))
    })()
  }, [project])

  // Fetch scenarios immediately when opening the dropdown
  useEffect(() => {
    if (!project?._id || !isScenariosOpen)
      return
    onSearchScenarios(`*${scenarioSearchString}*`)
  }, [project?._id, isScenariosOpen])

  // Fetch scenarios with debounce when typing
  useEffect(() => {
    if (!project?._id || !isScenariosOpen)
      return
    const debounced = debounce(() => {
      onSearchScenarios(`*${scenarioSearchString}*`)
    }, 300)
    debounced()
    return () => debounced.cancel()
  }, [scenarioSearchString])

  useEffect(() => {
    if (!project?._id || !scenarioOptions)
      return
    for (const i in scenarioOptions) {
      if (scenarioOptions[i].checked) {
        setScenario(scenarioOptions[i])
        setScenarioSearchString(scenarioOptions[i].checked === 'on' ? scenarioOptions[i].label : '')
        break
      }
    }
  }, [scenarioOptions])

  useEffect(() => {
    setIsScenariosOpen(true) // will trigger the fetch useEffect above
  }, [])

  /**
   * Search on page load
   */
  useEffect(() => {
    if (!location.state?.query_on_load)
      return
    const _filterOptions = defaultFilterOptions.map(obj => ({ ...obj }))
    if (location.state?.query_on_load.filter) {
      for (const i in _filterOptions) {
        if (location.state?.query_on_load.filter == _filterOptions[i].value)
          _filterOptions[i].checked = 'on'
      }
    }
    setFiltersOptions(_filterOptions)
  }, [location])


  /**
   * Search when filters or sorts change
   */
  useEffect(() => {
    if (!project?._id || !scenario)
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
      const response = await api.scenarios_search(project._id, { text })
      const options = response.data.hits.hits.map((doc) => ({
        _id: doc._id,
        label: doc._source.name,
        checked: location.state?.query_on_load?.scenario_id === doc._id ? 'on' : undefined
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
        index_pattern: project.index_pattern,
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
        response = await api.judgements_search(project._id, scenario._id, body)
      } catch (e) {
        return addToast(api.errorToast(e, { title: 'Failed to search docs' }))
      } finally {
        setIsLoadingResults(false)
      }

      // Handle API response
      setResults(response.data.hits.hits)
      setNumResults(response.data.hits.total.value)
    })()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderSelectScenarios = () => (
    <SelectScenario
      autoFocus={true}
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
      indexPatternRegexes={indexPatternRegexes}
      project={project}
      scenario={scenario}
      results={results}
      resultsPerRow={resultsPerRow}
    />
  )

  return (
    <Page title='Judgements' color='subdued' panelled={true}>
      <EuiFlexGroup gutterSize='m' alignItems='flexStart'>
        <EuiFlexItem grow>

          {/* Top bar */}
          <EuiForm
            component='form'
            onSubmit={onSearch}
            style={{
              margin: '-16px -20px 10px -20px',
              position: 'sticky',
              top: 0,
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