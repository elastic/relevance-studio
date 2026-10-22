/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
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
  EuiHorizontalRule,
  EuiLoadingSpinner,
  EuiSpacer,
  EuiTabbedContent,
  EuiTitle,
} from '@elastic/eui'
import TableRuntimeIndices from './TableRuntimeIndices'
import TableRuntimeJudgements from './TableRuntimeJudgements'
import TableRuntimeScenarios from './TableRuntimeScenarios'
import TableRuntimeStrategies from './TableRuntimeStrategies'
import api from '../../api'

const PAGE_SIZE = 25

// Each paginated runtime collection is fetched independently, server-side, only
// when its tab is first opened. Strategies are passed in whole (bounded by the
// run's task). A small controlled-pagination hook per collection keeps the
// payload bounded even for runs with thousands of scenarios/judgements.
const FlyoutRuntime = ({ workspaceId, benchmarkId, runId, strategies, onClose }) => {

  // Reshape the pre-loaded strategies map ({id: item}) into table rows.
  const strategyRows = Object.entries(strategies || {})
    .map(([key, value]) => ({ _id: key, ...value }))

  // Lazily-fetched, paginated collections: { items, total, page, loading, loaded }.
  const empty = { items: [], total: 0, page: 1, loading: false, loaded: false }
  const [indices, setIndices] = useState(empty)
  const [scenarios, setScenarios] = useState(empty)
  const [judgements, setJudgements] = useState(empty)

  const fetchers = {
    indices: (opts) => api.runs_get_runtime_indices(workspaceId, benchmarkId, runId, opts),
    scenarios: (opts) => api.runs_get_runtime_scenarios(workspaceId, benchmarkId, runId, opts),
    judgements: (opts) => api.runs_get_runtime_judgements(workspaceId, benchmarkId, runId, opts),
  }
  const setters = { indices: setIndices, scenarios: setScenarios, judgements: setJudgements }
  const idFields = { indices: 'index', scenarios: 'scenario_id', judgements: 'judgement_id' }

  const loadPage = (collection, page = 1) => {
    const setState = setters[collection]
    setState((prev) => ({ ...prev, loading: true }))
    fetchers[collection]({ size: PAGE_SIZE, page })
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
        setState({ items: rows, total: data.total ?? 0, page: data.page ?? page, loading: false, loaded: true })
      })
      .catch(() => setState({ items: [], total: 0, page, loading: false, loaded: true }))
  }

  // Load the first page of a collection the first time its tab becomes selected.
  const onTabClick = (collection) => {
    const state = { indices, scenarios, judgements }[collection]
    if (!state.loaded && !state.loading) loadPage(collection, 1)
  }

  const renderPager = (collection, state) => {
    const pages = Math.max(1, Math.ceil(state.total / PAGE_SIZE))
    if (state.total <= PAGE_SIZE) return null
    return (<>
      <EuiHorizontalRule margin='s' />
      <EuiFlexGroup justifyContent='flexEnd' alignItems='center' gutterSize='s'>
        <EuiFlexItem grow={false}><small>Page {state.page} of {pages} ({state.total} total)</small></EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButton size='s' iconType='arrowLeft' isDisabled={state.page <= 1 || state.loading}
            onClick={() => loadPage(collection, state.page - 1)}>Previous</EuiButton>
        </EuiFlexItem>
        <EuiFlexItem grow={false}>
          <EuiButton size='s' iconType='arrowRight' iconSide='right' isDisabled={state.page >= pages || state.loading}
            onClick={() => loadPage(collection, state.page + 1)}>Next</EuiButton>
        </EuiFlexItem>
      </EuiFlexGroup>
    </>)
  }

  const renderPaginated = (collection, state, Table) => {
    if (!state.loaded && state.loading)
      return <EuiEmptyPrompt icon={<EuiLoadingSpinner size='xl' />} title={<h3>Loading…</h3>} />
    return (<>
      <EuiSpacer size='l' />
      <Table items={state.items} />
      {renderPager(collection, state)}
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
              id: 'strategies',
              name: <div>Strategies</div>,
              content: (<><EuiSpacer size='l' /><TableRuntimeStrategies items={strategyRows} /></>),
            },
            {
              id: 'indices',
              name: <div>Indices</div>,
              content: renderPaginated('indices', indices, TableRuntimeIndices),
            },
            {
              id: 'scenarios',
              name: <div>Scenarios</div>,
              content: renderPaginated('scenarios', scenarios, TableRuntimeScenarios),
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
