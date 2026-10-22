/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import {
  EuiButton,
  EuiButtonEmpty,
  EuiEmptyPrompt,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutFooter,
  EuiFlyoutHeader,
  EuiForm,
  EuiLoadingSpinner,
  EuiSearchBar,
  EuiSpacer,
  EuiTabbedContent,
  EuiTitle,
} from '@elastic/eui'
import { SearchCount, SearchPagination, SelectTags } from '../../Layout'
import TableRuntimeIndices from './TableRuntimeIndices'
import TableRuntimeJudgements from './TableRuntimeJudgements'
import TableRuntimeScenarios from './TableRuntimeScenarios'
import TableRuntimeStrategies from './TableRuntimeStrategies'
import api from '../../api'

// Matches SearchPagination's itemsPerPageOptions ([10, 50, 100]) so the
// "Rows per page" selector highlights a valid default.
const DEFAULT_PAGE_SIZE = 10

// Each paginated runtime collection is fetched independently, server-side, only
// when its tab is first opened (or on mount, for whichever tab opens first).
// A small controlled-pagination hook per collection keeps the payload bounded
// even for runs with thousands of scenarios/judgements, and real
// EuiTablePagination controls (same pattern as the Scenarios/Strategies/
// Displays list pages) drive a fresh server request on every page or
// page-size change. Strategies and Scenarios also support a Tags filter,
// which likewise re-fetches from the server rather than filtering whatever
// happens to already be loaded client-side.
const FlyoutRuntime = ({ workspaceId, benchmarkId, runId, strategies, onClose }) => {

  // Reshape the pre-loaded strategies map ({id: item}) into table rows. This
  // is the UNFILTERED set, loaded once by the parent (RunsView) for the
  // Summary table/heatmap; it's reused here so opening the flyout with no
  // tags selected doesn't require an extra request.
  const strategyRows = Object.entries(strategies || {})
    .map(([key, value]) => ({ _id: key, ...value }))

  // Lazily-fetched, paginated collections: { items, total, page, size, loading, loaded }.
  const emptyState = () => ({
    items: [], total: 0, page: 1, size: DEFAULT_PAGE_SIZE, loading: false, loaded: false,
  })
  const [indices, setIndices] = useState(emptyState)
  const [scenarios, setScenarios] = useState(emptyState)
  const [judgements, setJudgements] = useState(emptyState)

  const states = { indices, scenarios, judgements }
  const fetchers = {
    indices: (opts) => api.runs_get_runtime_indices(workspaceId, benchmarkId, runId, opts),
    scenarios: (opts) => api.runs_get_runtime_scenarios(workspaceId, benchmarkId, runId, opts),
    judgements: (opts) => api.runs_get_runtime_judgements(workspaceId, benchmarkId, runId, opts),
  }
  const setters = { indices: setIndices, scenarios: setScenarios, judgements: setJudgements }
  const idFields = { indices: 'index', scenarios: 'scenario_id', judgements: 'judgement_id' }

  // Tracks each collection's current page size and (for scenarios) tags/text
  // filters synchronously (not via setState), because SearchPagination's
  // "rows per page" control fires onChangeSize(size) immediately followed by
  // onChangePage(1) in the same tick; reading from React state in the second
  // call would see a stale value.
  const sizeRefs = useRef({ indices: DEFAULT_PAGE_SIZE, scenarios: DEFAULT_PAGE_SIZE, judgements: DEFAULT_PAGE_SIZE })
  const tagsRefs = useRef({ scenarios: [] })
  const textRefs = useRef({ scenarios: '' })

  // Fetch a page of a collection from the server. `size`/`tags`/`text`
  // default to the collection's last-known values (e.g. when only `page` is
  // changing).
  const loadPage = (
    collection,
    page = 1,
    size = sizeRefs.current[collection],
    tags = tagsRefs.current[collection],
    text = textRefs.current[collection],
  ) => {
    sizeRefs.current[collection] = size
    if (collection === 'scenarios') {
      tagsRefs.current.scenarios = tags || []
      textRefs.current.scenarios = text || ''
    }
    const setState = setters[collection]
    setState((prev) => ({ ...prev, loading: true, size }))
    fetchers[collection]({
      size,
      page,
      tags: collection === 'scenarios' ? (tags || []) : undefined,
      text: collection === 'scenarios' ? (text || '') : undefined,
    })
      .then((response) => {
        const data = response?.data ?? {}
        const idField = idFields[collection]
        const rows = (data.items ?? []).map((d) => {
          // The item body is stored under `item`; lift it and attach _id.
          const base = { _id: d[idField], ...(d.item || {}) }
          // Judgements: no scenario-name join at scale; surface the scenario_id.
          if (collection === 'judgements') base.scenario = d.scenario_id || base.scenario_id
          return base
        })
        setState({
          items: rows, total: data.total ?? 0, page: data.page ?? page, size, loading: false, loaded: true,
        })
      })
      .catch(() => setState({ items: [], total: 0, page, size, loading: false, loaded: true }))
  }

  // Load the first page of a collection the first time its tab becomes
  // selected. The flyout opens with "indices" already selected, so load it
  // eagerly on mount (EuiTabbedContent's onTabClick only fires on clicks).
  useEffect(() => { loadPage('indices', 1) }, [])

  const onTabClick = (collection) => {
    const state = states[collection]
    if (state && !state.loaded && !state.loading) loadPage(collection, 1)
    if (collection === 'strategies') loadStrategyTagOptions()
    if (collection === 'scenarios') loadScenarioTagOptions()
  }

  ////  Tags: Strategies  //////////////////////////////////////////////////////

  // Strategies aren't paginated (bounded by the run's task), but tag
  // selection still re-fetches from the server rather than filtering the
  // already-loaded `strategies` prop client-side.
  const [strategyTags, setStrategyTags] = useState([])
  const [strategyText, setStrategyText] = useState('')
  const [strategyTagOptions, setStrategyTagOptions] = useState([])
  const [isLoadingStrategyTagOptions, setIsLoadingStrategyTagOptions] = useState(false)
  const [strategiesFilteredRows, setStrategiesFilteredRows] = useState(null) // null = no filter applied
  const [strategiesFilteredTotal, setStrategiesFilteredTotal] = useState(null) // null = no filter applied
  const [isLoadingStrategies, setIsLoadingStrategies] = useState(false)

  const loadStrategyTagOptions = () => {
    if (strategyTagOptions.length || isLoadingStrategyTagOptions) return
    setIsLoadingStrategyTagOptions(true)
    api.runs_get_runtime_strategies_tags(workspaceId, benchmarkId, runId)
      .then((response) => setStrategyTagOptions(response?.data?.tags ?? []))
      .catch(() => setStrategyTagOptions([]))
      .finally(() => setIsLoadingStrategyTagOptions(false))
  }

  // Shared fetch for both the Tags filter (auto-fetches on every change) and
  // the free-text Search button (only fetches on explicit submit).
  const fetchStrategies = (tags, text) => {
    if (!tags.length && !text) {
      setStrategiesFilteredRows(null) // revert to the unfiltered prop, no request needed
      setStrategiesFilteredTotal(null)
      return
    }
    setIsLoadingStrategies(true)
    api.runs_get_runtime_strategies(workspaceId, benchmarkId, runId, { tags, text })
      .then((response) => {
        const rows = (response?.data?.items ?? []).map((d) => ({ _id: d.strategy_id, ...(d.item || {}) }))
        setStrategiesFilteredRows(rows)
        setStrategiesFilteredTotal(response?.data?.total ?? rows.length)
      })
      .catch(() => {
        setStrategiesFilteredRows([])
        setStrategiesFilteredTotal(0)
      })
      .finally(() => setIsLoadingStrategies(false))
  }

  const onChangeStrategyTags = (tags) => {
    setStrategyTags(tags)
    fetchStrategies(tags, strategyText)
  }

  const onSubmitStrategySearch = (e) => {
    e?.preventDefault()
    fetchStrategies(strategyTags, strategyText)
  }

  const displayedStrategyRows = strategiesFilteredRows ?? strategyRows
  const displayedStrategyTotal = strategiesFilteredTotal ?? strategyRows.length

  ////  Tags: Scenarios  ///////////////////////////////////////////////////////

  const [scenarioTags, setScenarioTags] = useState([])
  const [scenarioText, setScenarioText] = useState('')
  const [scenarioTagOptions, setScenarioTagOptions] = useState([])
  const [isLoadingScenarioTagOptions, setIsLoadingScenarioTagOptions] = useState(false)

  const loadScenarioTagOptions = () => {
    if (scenarioTagOptions.length || isLoadingScenarioTagOptions) return
    setIsLoadingScenarioTagOptions(true)
    api.runs_get_runtime_scenarios_tags(workspaceId, benchmarkId, runId)
      .then((response) => setScenarioTagOptions(response?.data?.tags ?? []))
      .catch(() => setScenarioTagOptions([]))
      .finally(() => setIsLoadingScenarioTagOptions(false))
  }

  // Tags filter auto-fetches on every change, preserving whatever text was
  // last submitted (the `text` arg is left undefined so loadPage's default
  // parameter picks up textRefs.current.scenarios).
  const onChangeScenarioTags = (tags) => {
    setScenarioTags(tags)
    loadPage('scenarios', 1, undefined, tags)
  }

  // Free-text search only fetches on explicit submit (Search button or
  // Enter), preserving whatever tags are currently selected.
  const onSubmitScenarioSearch = (e) => {
    e?.preventDefault()
    loadPage('scenarios', 1, undefined, scenarioTags, scenarioText)
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  // Inline free-text search bar + Tags dropdown + Search button, matching
  // the Strategies/Scenarios list pages' SearchTable layout. Tags auto-fetch
  // on change (via `onChangeTags`); text only fetches on explicit submit.
  const renderSearchRow = ({ text, onChangeText, onSubmit, isLoading, tagOptions, isLoadingTagOptions, tags, onChangeTags }) => (
    <EuiForm component='form' onSubmit={onSubmit}>
      <EuiFlexGroup gutterSize='s'>
        <EuiFlexItem grow>
          <EuiSearchBar
            box={{ incremental: true, schema: true }}
            defaultQuery={text}
            onChange={(q) => onChangeText(q.query?.text || '')}
          />
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <SelectTags
            isLoading={isLoadingTagOptions}
            options={tagOptions}
            selected={tags}
            onChange={onChangeTags}
          />
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButton isLoading={isLoading} iconType='search' type='submit'>
            Search
          </EuiButton>
        </EuiFlexItem>
      </EuiFlexGroup>
    </EuiForm>
  )

  const renderPaginated = (collection, state, Table, extraControls) => {
    if (!state.loaded && state.loading)
      return <EuiEmptyPrompt icon={<EuiLoadingSpinner size='xl' />} title={<h3>Loading…</h3>} />
    return (<>
      <EuiSpacer size='l' />
      {extraControls}
      {state.loaded && state.total === 0
        ? <EuiEmptyPrompt title={<h3>No results</h3>} />
        : (<>
          <SearchCount showing={state.items.length} total={state.total} />
          <EuiSpacer size='s' />
          <Table items={state.items} />
          <EuiSpacer size='m' />
          <SearchPagination
            page={state.page}
            size={state.size}
            total={state.total}
            onChangePage={(page) => loadPage(collection, page)}
            onChangeSize={(size) => loadPage(collection, 1, size)}
          />
        </>)
      }
    </>)
  }

  return (
    <EuiFlyout hideCloseButton onClose={onClose} ownFocus size='l'>
      <EuiFlyoutHeader>
        <EuiTitle size='m'>
          <h2>Runtime assets</h2>
        </EuiTitle>
      </EuiFlyoutHeader>
      <EuiFlyoutBody>
        <EuiTabbedContent
          onTabClick={(tab) => onTabClick(tab.id)}
          tabs={[
            {
              id: 'indices',
              name: <div>Indices</div>,
              content: renderPaginated('indices', indices, TableRuntimeIndices),
            },
            {
              id: 'strategies',
              name: <div>Strategies</div>,
              content: (<>
                <EuiSpacer size='l' />
                {renderSearchRow({
                  text: strategyText,
                  onChangeText: setStrategyText,
                  onSubmit: onSubmitStrategySearch,
                  isLoading: isLoadingStrategies,
                  tagOptions: strategyTagOptions,
                  isLoadingTagOptions: isLoadingStrategyTagOptions,
                  tags: strategyTags,
                  onChangeTags: onChangeStrategyTags,
                })}
                <EuiSpacer size='m' />
                {isLoadingStrategies
                  ? <EuiEmptyPrompt icon={<EuiLoadingSpinner size='xl' />} title={<h3>Loading…</h3>} />
                  : (<>
                    <SearchCount showing={displayedStrategyRows.length} total={displayedStrategyTotal} />
                    <EuiSpacer size='s' />
                    <TableRuntimeStrategies items={displayedStrategyRows} />
                  </>)
                }
              </>),
            },
            {
              id: 'scenarios',
              name: <div>Scenarios</div>,
              content: renderPaginated('scenarios', scenarios, TableRuntimeScenarios, (
                <>
                  {renderSearchRow({
                    text: scenarioText,
                    onChangeText: setScenarioText,
                    onSubmit: onSubmitScenarioSearch,
                    isLoading: scenarios.loading,
                    tagOptions: scenarioTagOptions,
                    isLoadingTagOptions: isLoadingScenarioTagOptions,
                    tags: scenarioTags,
                    onChangeTags: onChangeScenarioTags,
                  })}
                  <EuiSpacer size='m' />
                </>
              )),
            },
            {
              id: 'judgements',
              name: <div>Judgements</div>,
              content: renderPaginated('judgements', judgements, TableRuntimeJudgements),
            },
          ]}
        />
      </EuiFlyoutBody>
      <EuiFlyoutFooter>
        <EuiButtonEmpty flush='left' iconType='cross' onClick={onClose}>
          Close
        </EuiButtonEmpty>
      </EuiFlyoutFooter>
    </EuiFlyout>
  )
}

export default FlyoutRuntime
