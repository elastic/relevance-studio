import React, { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  EuiButtonGroup,
  EuiFieldSearch,
  EuiFilterButton,
  EuiFilterGroup,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiFormRow,
  EuiIcon,
  EuiInputPopover,
  EuiPanel,
  EuiPopover,
  EuiSpacer,
  EuiSelectable,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import { Page } from '../../Layout'
import JudgementsCard from './JudgementsCard'
import api from '../../api'

const Judgements = () => {

  const location = useLocation()

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project } = useProjectContext()

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
  const [loadingDisplays, setLoadingDisplays] = useState(false)
  const [loadingResults, setLoadingResults] = useState(false)
  const [loadingScenarios, setLoadingScenarios] = useState(false)
  const [numResults, setNumResults] = useState(0)
  const [queryString, setQueryString] = useState('')
  const [results, setResults] = useState([])
  const [resultsPerRow, setResultsPerRow] = useState(3)
  const [scenario, setScenario] = useState(null)
  const [scenariosOpen, setScenariosOpen] = useState(false)
  const [scenariosOptions, setScenariosOptions] = useState([])
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
        setLoadingDisplays(true)
        response = await api.get_displays(project._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get displays'
        }))
      } finally {
        setLoadingDisplays(false)
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

  /**
   * Get scenarios for project
   */
  useEffect(() => {
    if (!project?._id)
      return
    (async () => {

      // Submit API request
      let response
      try {
        setLoadingScenarios(true)
        response = await api.get_scenarios(project._id)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to get scenarios'
        }))
      } finally {
        setLoadingScenarios(false)
      }

      // Handle API response
      const options = []
      response.data.hits.hits.forEach((doc) => {
        const option = { _id: doc._id, label: doc._source.name }
        if (location.state?.query_on_load?.scenario_id == doc._id)
          option.checked = 'on'
        options.push(option)
      })
      setScenariosOptions(options)
      setLoadingScenarios(false)
    })()
  }, [project])

  useEffect(() => {
    if (!project?._id || !scenariosOptions)
      return
    for (const i in scenariosOptions) {
      if (scenariosOptions[i].checked) {
        setScenario(scenariosOptions[i])
        setScenarioSearchString(scenariosOptions[i].checked === 'on' ? scenariosOptions[i].label : '')
        break
      }
    }
  }, [scenariosOptions])

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
   * Handle search bar submission
   */
  const onSearch = () => {
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
        setLoadingResults(true)
        response = await api.get_judgements_docs(project._id, scenario._id, body)
      } catch (error) {
        return addToast(api.errorToast(error, {
          title: 'Failed to search docs'
        }))
      } finally {
        setLoadingResults(false)
      }

      // Handle API response
      setResults(response.data.hits.hits)
      setNumResults(response.data.hits.total.value)
    })()
  }

  /**
   * Given an index name, find the display whose index pattern matches it
   * with the most specificity.
   */
  const resolveIndexToDisplay = (index) => {
    const matches = []
    for (const indexPattern in indexPatternRegexes)
      if (indexPatternRegexes[indexPattern].test(index))
        matches.push(indexPattern)
    if (matches.length === 0)
      return null
    const bestMatch = matches.reduce((mostSpecific, current) =>
      current.length > mostSpecific.length ? current : mostSpecific
    )
    return displays[bestMatch]
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderSelectScenarios = () => {
    return <EuiSelectable
      options={scenariosOptions}
      onChange={(newOptions, event, changedOption) => {
        setScenariosOptions(newOptions)
        setScenariosOpen(false)
        setLoadingScenarios(false)
      }}
      singleSelection
      searchable
      searchProps={{
        value: scenarioSearchString,
        isClearable: false,
        isLoading: loadingScenarios,
        onChange: (value) => {
          setScenarioSearchString(value)
          setLoadingScenarios(true)
        },
        onKeyDown: (event) => {
          if (event.key === 'Tab') return setScenariosOpen(false)
          if (event.key !== 'Escape') return setScenariosOpen(true)
        },
        onClick: () => setScenariosOpen(true),
        onFocus: () => setScenariosOpen(true),
        placeholder: loadingScenarios ? '' : 'Choose a scenario'
      }}
      isPreFiltered={loadingScenarios ? false : { highlightSearch: false }} // Shows the full list when not actively typing to search
      listProps={{
        css: { '.euiSelectableList__list': { maxBlockSize: 200 } },
      }}
    >
      {(scenariosOptions, scenarioSearchString) => (
        <EuiInputPopover
          closeOnScroll
          closePopover={() => setScenariosOpen(false)}
          disableFocusTrap
          fullWidth
          input={scenarioSearchString}
          isOpen={scenariosOpen}
          panelPaddingSize='none'
        >
          {scenariosOptions}
        </EuiInputPopover>
      )}
    </EuiSelectable>
  }

  const renderSelectFilters = () => {
    return <EuiSelectable
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
  }

  const renderSelectSort = () => {
    return <EuiSelectable
      options={sortOptions}
      onChange={(newOptions, event, changedOption) => {
        setSortOptions(newOptions)
        // Sorting by anything with ratings requires filtering by rated docs
        if (changedOption.value.startsWith('rating')) {
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
  }


  const renderResults = () => {
    const cards = []
    results.forEach((result) => {
      cards.push(
        <JudgementsCard
          key={result.doc._id}
          doc={result.doc}
          project={project}
          scenario={scenario}
          rating={result.rating}
          author={result['@author']}
          timestamp={result['@timestamp']}
          template={resolveIndexToDisplay(result.doc._index)?.template}
        />
      )
    })
    const grid = <>
      <EuiFlexGrid columns={parseInt(resultsPerRow)} direction='row'>
        {cards.map((card, i) => {
          return (
            <EuiFlexItem key={i}>
              {card}
            </EuiFlexItem>
          )
        })}
      </EuiFlexGrid>
    </>
    return grid
  }

  return (<>
    <Page title='Judgements'>
      <EuiFlexGroup gutterSize='m' alignItems='flexStart'>
        <EuiFlexItem grow>

          {/* Top bar */}
          <EuiFlexItem style={{
            boxShadow: '0 10px 10px -10px rgba(0, 0, 0, 0.25)',
            margin: '0 -20px 10px -20px',
            padding: '0 20px',
            position: 'sticky',
            top: 0,
            zIndex: 999
          }}>
            <EuiPanel
              hasBorder={false}
              hasShadow={false}
              paddingSize='none'
              style={{ borderRadius: 0 }}
            >
              <EuiSpacer size='s' />
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
                        <EuiFlexItem grow={6}>
                          <EuiFieldSearch
                            fullWidth
                            isLoading={loadingResults}
                            placeholder="Find documents..."
                            value={queryString}
                            onChange={(e) => setQueryString(e.target.value)}
                            onSearch={onSearch}
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
                      </EuiFlexGroup>
                    </EuiFormRow>
                  }
                </EuiFlexItem>
              </EuiFlexGroup>
              <EuiSpacer size='s' />
              <EuiPanel hasBorder={false} hasShadow={false} paddingSize='none'>
                {!!results.length &&
                  <EuiFlexGroup alignItems='center' gutterSize='s'>
                    <EuiFlexItem grow={5}>
                      <EuiText color='subdued' size='xs'>
                        Showing {results.length.toLocaleString()} of {numResults.toLocaleString()}{numResults >= 10000 ? '+' : ''} result{numResults != 1 ? 's' : ''}
                      </EuiText>
                    </EuiFlexItem>
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
              <EuiSpacer size='s' />
            </EuiPanel>
          </EuiFlexItem>

          <EuiSpacer size='m' />

          {/* Display results */}
          <EuiFlexItem>
            {!!results.length &&
              renderResults()
            }
          </EuiFlexItem>
        </EuiFlexItem>
      </EuiFlexGroup>
    </Page>
  </>)
}

export default Judgements