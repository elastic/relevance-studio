/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  EuiButton,
  EuiNotificationBadge,
  EuiCallOut,
  EuiCodeBlock,
  EuiFilterButton,
  EuiFilterGroup,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiFormRow,
  EuiPanel,
  EuiPopover,
  EuiSelect,
  EuiSelectable,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiSwitch,
  EuiTabbedContent,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { Page } from '../../Layout'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import FlyoutRuntime from './FlyoutRuntime'
import ChartMetricsHeatmap, { buildVariantOverride } from './ChartMetricsHeatmap'
import ChartMetricsTradeoff from './ChartMetricsTradeoff'
import ChartSensitivity, { optimizedStrategies } from './ChartSensitivity'
import PanelUnratedDocs from './PanelUnratedDocs'
import TableMetrics from './TableMetrics'
import { getHistory } from '../../history'
import api from '../../api'
import hp from '../../hyperparameters'
import utils from '../../utils'

const RunsView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const location = useLocation()
  const history = getHistory()
  const { addToast } = useAppContext()
  const { workspace, benchmark, run } = usePageResources()
  const isReady = useResources().hasResources(['workspace', 'benchmark', 'run'])

  ////  State  /////////////////////////////////////////////////////////////////

  // The active tab (summary/chart/heatmap/unrated) is mirrored to the `?tab=`
  // query param so the view is shareable via URL. Updates use history.replace
  // (not push) so clicking between tabs doesn't pile up browser-history
  // entries -- the back button leaves the page instead of cycling tabs.
  const [selectedTabId, setSelectedTabId] = useState(
    () => new URLSearchParams(location.search).get('tab') || 'summary'
  )
  const onTabClick = (tab) => {
    setSelectedTabId(tab.id)
    const params = new URLSearchParams(location.search)
    params.set('tab', tab.id)
    history.replace(`${location.pathname}?${params.toString()}`)
  }

  const [strategyInFocus, setStrategyInFocus] = useState(null)
  const [isFlyoutRuntimeOpen, setIsFlyoutRuntimeOpen] = useState(false)
  // A run's forensics live in per-collection data streams, fetched independently
  // and paginated server-side. Only what a given view needs is requested:
  //  - On page load: ALL runtime strategies (bounded by the run's task — labels
  //    the summary table + heatmap y-axis) and the FIRST PAGE of unrated docs.
  //  - The runtime-assets flyout loads indices/scenarios/judgements per tab,
  //    paginated, only when that tab is opened.
  const [runtimeStrategies, setRuntimeStrategies] = useState(null)  // {id: item} map, whole
  const [unratedPage, setUnratedPage] = useState(null)              // { items, total, size, page }
  const [isDownloading, setIsDownloading] = useState(false)
  // Hyperparameter optimization: a compact summary of the run (winners,
  // sensitivity, warnings), the unrated docs filter, and the Breakdown tab's
  // variant selection.
  const [optimizationSummary, setOptimizationSummary] = useState(null)
  const [unratedWinnersOnly, setUnratedWinnersOnly] = useState(false)
  const [variantStrategyId, setVariantStrategyId] = useState('')
  const [variantOptions, setVariantOptions] = useState([])
  const [variantId, setVariantId] = useState('')
  const [variantOverride, setVariantOverride] = useState(null)
  const [isLoadingVariant, setIsLoadingVariant] = useState(false)
  const [metricOpen, setMetricOpen] = useState(false)
  const [metricOptions, setMetricOptions] = useState([])
  const [metricSelected, setMetricSelected] = useState(null)
  const [xGroupByOpen, setXGroupByOpen] = useState(false)
  const [xGroupByOptions, setXGroupByOptions] = useState([
    { _id: 'scenario_id', label: 'Scenario', checked: 'on' },
    { _id: 'scenario_tag', label: 'Scenario Tag' },
  ])
  const [xGroupBySelected, setXGroupBySelected] = useState({
    _id: 'scenario_id', label: 'Scenario', checked: 'on'
  })
  const [xSortByOpen, setXSortByOpen] = useState(false)
  const [xSortByOptions, setXSortByOptions] = useState([])
  const [xSortBySelected, setXSortBySelected] = useState([])
  const [yGroupByOpen, setYGroupByOpen] = useState(false)
  const [yGroupByOptions, setYGroupByOptions] = useState([
    { _id: 'strategy_id', label: 'Strategy', checked: 'on' },
    { _id: 'strategy_tag', label: 'Strategy Tag' },
  ])
  const [yGroupBySelected, setYGroupBySelected] = useState({
    _id: 'strategy_id', label: 'Strategy', checked: 'on'
  })
  const [ySortByOpen, setYSortByOpen] = useState(false)
  const [ySortByOptions, setYSortByOptions] = useState([
    { _id: { by: 'value', order: 'desc' }, label: 'Metric', checked: 'on' },
    { _id: { by: 'name', order: 'asc' }, label: 'Name' },
  ])
  const [ySortBySelected, setYSortBySelected] = useState({
    _id: { by: 'value', order: 'asc' }, label: 'Metric', checked: 'on'
  })

  // Metrics derived from benchmark
  const labelForMetric = (id) => {
    const map = { ndcg: 'NDCG', mrr: 'MRR', precision: 'Precision', recall: 'Recall' }
    return map[id?.toLowerCase?.()] ?? (id ? String(id).toUpperCase() : '')
  }

  const normalizedBenchmarkMetrics = useMemo(() => {
    // Accept strings or objects; keep order from benchmark
    const list = (benchmark?.task?.metrics ?? []).map((m) => {
      if (typeof m === 'string') return m.toLowerCase()
      if (m?._id) return String(m._id).toLowerCase()
      if (m?.id) return String(m.id).toLowerCase()
      if (m?.name) return String(m.name).toLowerCase()
      return null
    }).filter(Boolean)
    return [...new Set(list)] // dedupe, preserve order
  }, [benchmark])

  // Initialize options + selected once benchmark is ready.
  useEffect(() => {
    if (!normalizedBenchmarkMetrics.length) return
    // Don’t overwrite if user already picked one
    if (metricSelected?._id) return
    const first = normalizedBenchmarkMetrics[0]
    const opts = normalizedBenchmarkMetrics.map((id, i) => ({
      _id: id,
      label: labelForMetric(id),
      ...(i === 0 ? { checked: 'on' } : {})
    }))
    setMetricOptions(opts)
    setMetricSelected({ _id: first, label: labelForMetric(first), checked: 'on' })
  }, [normalizedBenchmarkMetrics])

  // On load, fetch ALL runtime strategies (bounded by the run's task) so the
  // Summary table and heatmap y-axis can show strategy names. Reshaped into a
  // {strategy_id: item} map to match what the child components expect.
  useEffect(() => {
    if (!workspace?._id || !benchmark?._id || !run?._id) return
    if (runtimeStrategies !== null) return
    let cancelled = false
    api.runs_get_runtime_strategies(workspace._id, benchmark._id, run._id)
      .then((response) => {
        if (cancelled) return
        const map = {}
        for (const d of (response?.data?.items ?? []))
          map[d.strategy_id] = d.item
        setRuntimeStrategies(map)
      })
      .catch(() => { if (!cancelled) setRuntimeStrategies({}) })
    return () => { cancelled = true }
  }, [workspace?._id, benchmark?._id, run?._id])

  // Fetch the FIRST PAGE of unrated docs on load (the panel paginates the rest).
  const loadUnratedPage = (page = 1, size = 25, winnersOnly = unratedWinnersOnly) => {
    if (!workspace?._id || !benchmark?._id || !run?._id) return
    api.runs_get_unrated_docs(workspace._id, benchmark._id, run._id, { page, size, winners_only: winnersOnly })
      .then((response) => {
        const data = response?.data ?? {}
        // Normalize stored shape (doc_id/doc_index) back to _id/_index for the panel.
        const items = (data.items ?? []).map((d) => ({
          _id: d.doc_id, _index: d.doc_index,
          count: d.count, strategies: d.strategies, scenarios: d.scenarios, variants: d.variants,
        }))
        setUnratedPage({ items, total: data.total ?? 0, size: data.size ?? size, page: data.page ?? page })
      })
      .catch(() => { setUnratedPage({ items: [], total: 0, size, page }) })
  }
  useEffect(() => {
    if (unratedPage !== null) return
    loadUnratedPage(1)
  }, [workspace?._id, benchmark?._id, run?._id])

  // Fetch the compact optimization summary of a run that searched hyperparameters.
  const isOptimized = hp.isOptimizedRun(run)
  useEffect(() => {
    if (!isOptimized || !run?.summary || !workspace?._id || !benchmark?._id) return
    let cancelled = false
    api.runs_get_optimization_summary(workspace._id, benchmark._id, run._id)
      .then((response) => {
        if (!cancelled && response.status < 300)
          setOptimizationSummary(response.data)
      })
      .catch(() => { /* The run view works without the summary */ })
    return () => { cancelled = true }
  }, [isOptimized, workspace?._id, benchmark?._id, run?._id, !!run?.summary])

  const optimizedList = useMemo(() => optimizedStrategies(optimizationSummary), [optimizationSummary])

  // Load the variants of the chosen strategy for the Breakdown tab's selector.
  useEffect(() => {
    setVariantId('')
    setVariantOverride(null)
    setVariantOptions([])
    if (!variantStrategyId || !workspace?._id || !benchmark?._id || !run?._id) return
    let cancelled = false
    api.runs_get_variants(workspace._id, benchmark._id, run._id, {
      strategy_id: variantStrategyId, size: 100, page: 1, sort: 'rank',
    }).then((response) => {
      if (!cancelled && response.status < 300)
        setVariantOptions(response.data.items || [])
    }).catch(() => {})
    return () => { cancelled = true }
  }, [variantStrategyId])

  // Load every scenario score of the chosen variant to show it in the heatmap.
  useEffect(() => {
    setVariantOverride(null)
    if (!variantStrategyId || !variantId) return
    let cancelled = false
    ;(async () => {
      try {
        setIsLoadingVariant(true)
        const results = []
        for (let page = 1; ; page++) {
          const response = await api.runs_get_results(workspace._id, benchmark._id, run._id, {
            strategy_id: variantStrategyId, variant_id: variantId, size: 1000, page,
          })
          const items = response?.data?.items ?? []
          results.push(...items)
          if (!items.length || results.length >= (response?.data?.total ?? 0)) break
        }
        if (!cancelled)
          setVariantOverride(buildVariantOverride(variantStrategyId, variantId, results))
      } catch (e) {
        if (!cancelled)
          addToast(api.errorToast(e, { title: 'Failed to get the variant results' }))
      } finally {
        if (!cancelled)
          setIsLoadingVariant(false)
      }
    })()
    return () => { cancelled = true }
  }, [variantId])

  // A run-shaped object carrying the loaded strategy metadata, so the summary
  // table and heatmap keep working. It deliberately carries ONLY strategies
  // (not scenarios/judgements, which are paginated in the flyout) — the heatmap
  // x-axis falls back to scenario ids, which is acceptable at scale.
  const runWithForensics = useMemo(() => {
    if (!run) return run
    return {
      ...run,
      runtime: { strategies: runtimeStrategies || {} },
      unrated_docs: unratedPage?.items ?? [],
    }
  }, [run, runtimeStrategies, unratedPage])

  // Download everything about the run (results, runtime, unrated docs,
  // failures -- not just the slim run doc). The full object is assembled
  // server-side in a single call (api.runs.get_full), so the browser makes
  // one request and isn't left orchestrating N paginated round trips itself.
  const downloadRun = async () => {
    if (!workspace?._id || !benchmark?._id || !run?._id) return
    setIsDownloading(true)
    try {
      const response = await api.runs_get_full(workspace._id, benchmark._id, run._id)
      const full = response?.data ?? {}
      const blob = new Blob([utils.jsonStringifySortedKeys(full, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `run-${run._id}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      addToast(api.errorToast(e, { title: 'Failed to download run' }))
    } finally {
      setIsDownloading(false)
    }
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderSelectMetric = () => {
    return (
      <EuiPopover
        button={
          <EuiFilterButton
            iconType='arrowDown'
            onClick={(e) => setMetricOpen(!metricOpen)}
            isSelected={metricOpen}
          >
            {metricSelected?.label ?? 'Metric'}
          </EuiFilterButton>
        }
        closePopover={(e) => setMetricOpen(false)}
        isOpen={metricOpen}
        panelPaddingSize='none'
        style={{ width: '150px' }}
      >
        <EuiSelectable
          options={metricOptions}
          onChange={(newOptions, event, changedOption) => {
            setMetricOptions(newOptions)
            setMetricOpen(false)
            setMetricSelected(changedOption)
          }}
          singleSelection='always'
          listProps={{ css: { '.euiSelectableList__list': { maxBlockSize: 250 } } }}
        >
          {(list, search) => (
            <div style={{ width: 250 }}>
              {list}
            </div>
          )}
        </EuiSelectable>
      </EuiPopover>
    )
  }

  const renderSelectXGroupBy = () => {
    return (
      <EuiPopover
        button={
          <EuiFilterButton
            iconType='arrowDown'
            onClick={(e) => setXGroupByOpen(!xGroupByOpen)}
            isSelected={xGroupByOpen}
          >
            {xGroupBySelected.label}
          </EuiFilterButton>
        }
        closePopover={(e) => setXGroupByOpen(false)}
        isOpen={xGroupByOpen}
        panelPaddingSize='none'
        style={{ width: '150px' }}
      >
        <EuiSelectable
          options={xGroupByOptions}
          onChange={(newOptions, event, changedOption) => {
            setXGroupByOptions(newOptions)
            setXGroupByOpen(false)
            setXGroupBySelected(changedOption)
          }}
          singleSelection='always'
          listProps={{ css: { '.euiSelectableList__list': { maxBlockSize: 250 } } }}
        >
          {(list, search) => (
            <div style={{ width: 250 }}>
              {list}
            </div>
          )}
        </EuiSelectable>
      </EuiPopover>
    )
  }

  const renderSelectYGroupBy = () => {
    return (
      <EuiPopover
        button={
          <EuiFilterButton
            iconType='arrowDown'
            onClick={(e) => setYGroupByOpen(!yGroupByOpen)}
            isSelected={yGroupByOpen}
          >
            {yGroupBySelected.label}
          </EuiFilterButton>
        }
        closePopover={(e) => setYGroupByOpen(false)}
        isOpen={yGroupByOpen}
        panelPaddingSize='none'
        style={{ width: '150px' }}
      >
        <EuiSelectable
          options={yGroupByOptions}
          onChange={(newOptions, event, changedOption) => {
            setYGroupByOptions(newOptions)
            setYGroupByOpen(false)
            setYGroupBySelected(changedOption)
          }}
          singleSelection='always'
          listProps={{ css: { '.euiSelectableList__list': { maxBlockSize: 250 } } }}
        >
          {(list, search) => (
            <div style={{ width: 250 }}>
              {list}
            </div>
          )}
        </EuiSelectable>
      </EuiPopover>
    )
  }

  const renderSelectYSortBy = () => {
    return (
      <EuiPopover
        button={
          <EuiFilterButton
            iconType='arrowDown'
            onClick={(e) => setYSortByOpen(!ySortByOpen)}
            isSelected={ySortByOpen}
          >
            {ySortBySelected.label}
          </EuiFilterButton>
        }
        closePopover={(e) => setYSortByOpen(false)}
        isOpen={ySortByOpen}
        panelPaddingSize='none'
        style={{ width: '150px' }}
      >
        <EuiSelectable
          options={ySortByOptions}
          onChange={(newOptions, event, changedOption) => {
            setYSortByOptions(newOptions)
            setYSortByOpen(false)
            setYSortBySelected(changedOption)
          }}
          singleSelection='always'
          listProps={{ css: { '.euiSelectableList__list': { maxBlockSize: 250 } } }}
        >
          {(list, search) => (
            <div style={{ width: 250 }}>
              {list}
            </div>
          )}
        </EuiSelectable>
      </EuiPopover>
    )
  }

  const renderHeatmapControls = () => {
    return (
      <EuiFlexGroup gutterSize='s'>

        {/* Metric */}
        <EuiFlexItem grow={false}>
          <EuiFormRow label='Metric'>
            <EuiFilterGroup>
              {renderSelectMetric()}
            </EuiFilterGroup>
          </EuiFormRow>
        </EuiFlexItem>

        {/* Group by */}
        <EuiFlexItem grow={false}>
          <EuiFormRow label='Group by'>
            <EuiFilterGroup>
              {renderSelectYGroupBy()}
              {renderSelectXGroupBy()}
            </EuiFilterGroup>
          </EuiFormRow>
        </EuiFlexItem>

        {/* Variant */}
        {optimizedList.length > 0 && yGroupBySelected._id === 'strategy_id' && xGroupBySelected._id === 'scenario_id' &&
          <>
            <EuiFlexItem grow={false} style={{ width: '220px' }}>
              <EuiFormRow label='Strategy variant'>
                <EuiSelect
                  aria-label='Strategy to show a variant of'
                  onChange={(e) => setVariantStrategyId(e.target.value)}
                  options={[
                    { value: '', text: 'Winners' },
                    ...optimizedList.map((s) => ({ value: s.strategy_id, text: s.name || s.strategy_id })),
                  ]}
                  value={variantStrategyId}
                />
              </EuiFormRow>
            </EuiFlexItem>
            {variantStrategyId &&
              <EuiFlexItem grow={false} style={{ width: '260px' }}>
                <EuiFormRow label='Variant'>
                  <EuiSelect
                    aria-label='Variant'
                    isLoading={isLoadingVariant}
                    onChange={(e) => setVariantId(e.target.value)}
                    options={[
                      { value: '', text: 'Winner' },
                      ...variantOptions.map((v) => ({
                        value: v.variant_id,
                        text: `#${v.rank} ${v.variant_id.slice(0, 8)}${v.is_baseline ? ' (baseline)' : ''}${v.is_winner ? ' (winner)' : ''}`,
                      })),
                    ]}
                    value={variantId}
                  />
                </EuiFormRow>
              </EuiFlexItem>
            }
          </>
        }

        {/* Sort by */}
        {/*
        <EuiFlexItem grow={false}>
          <EuiFormRow label='Sort by'>
            <EuiFilterGroup>
              {renderSelectYSortBy()}
              {
              //renderSelectXSortBy()
              }
            </EuiFilterGroup>
          </EuiFormRow>
        </EuiFlexItem>
        */}
      </EuiFlexGroup>
    )
  }

  /**
   * Button to open flyout to inspect runtime assets.
   */
  const renderButtonDownload = () => (
    <EuiButton
      iconType='download'
      isLoading={isDownloading}
      onClick={() => downloadRun()}>
      Download run
    </EuiButton>
  )

  /**
   * Button to open flyout to inspect runtime assets.
   */
  const renderButtonRuntime = () => (
    <EuiButton
      iconType='inspect'
      onClick={() => setIsFlyoutRuntimeOpen(!isFlyoutRuntimeOpen)}>
      View runtime assets
    </EuiButton>
  )

  return (
    <Page title={
      <EuiSkeletonTitle isLoading={!isReady} size='l'>
        {!benchmark?.name &&
          <>Not found</>
        }
        {!!benchmark?.name &&
          <>{benchmark.name}</>
        }
      </EuiSkeletonTitle>
    }
      buttons={[renderButtonRuntime(), renderButtonDownload()]}
    >
      {isFlyoutRuntimeOpen &&
        <FlyoutRuntime
          workspaceId={workspace._id}
          benchmarkId={benchmark._id}
          runId={run._id}
          strategies={runtimeStrategies || {}}
          onClose={() => setIsFlyoutRuntimeOpen(false)}
        />
      }

      {/* Error */}
      {!!Object.keys(run?.error ?? {}).length &&
        <>
          <EuiPanel paddingSize='none'>
            <EuiPanel color='transparent'>
              <EuiTitle size='s'>
                <h2>Failure</h2>
              </EuiTitle>
            </EuiPanel>
            <EuiHorizontalRule margin='none' />
            <EuiPanel color='transparent'>
              <p>
                This run failed due to this error:
              </p>
              <br />
              <EuiCallOut color='danger' title={run.error.type || 'Unknown error'}>
                {run.error.traceback &&
                  <EuiCodeBlock language='python'>
                    {run.error.traceback}
                  </EuiCodeBlock>
                }
                {!run.error.traceback &&
                  <p>No other information was given for this error.</p>
                }
              </EuiCallOut>
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer size='m' />
        </>
      }

      {/* Running */}
      {run && run['@meta']?.status == 'running' &&
        <>
          <EuiPanel paddingSize='none'>
            <EuiPanel color='transparent'>
              <EuiTitle size='s'>
                <h2>Running</h2>
              </EuiTitle>
            </EuiPanel>
            <EuiHorizontalRule margin='none' />
            <EuiPanel color='transparent'>
              <EuiCallOut>
                This run is still running. You can return to this page when the run is completed.
              </EuiCallOut>
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer size='m' />
        </>
      }

      {/* Skipped */}
      {run && run['@meta']?.status == 'skipped' &&
        <>
          <EuiPanel paddingSize='none'>
            <EuiPanel color='transparent'>
              <EuiTitle size='s'>
                <h2>Skipped</h2>
              </EuiTitle>
            </EuiPanel>
            <EuiHorizontalRule margin='none' />
            <EuiPanel color='transparent'>
              <EuiCallOut>
                This run was skipped. This happens when the scenarios have no judgements with ratings.
              </EuiCallOut>
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer size='m' />
        </>
      }

      {/* Summary / Chart / Heatmap / Unrated docs, tabbed into a single panel */}
      {run?.summary &&
        <>
          {(() => {
            const tabs = [
              {
                id: 'summary',
                name: 'Summary',
                content: (
                  <>
                    <EuiSpacer size='l' />
                    <EuiFlexGroup>
                      <EuiFlexItem>
                        <TableMetrics
                          evaluation={runWithForensics}
                          optimizationSummary={optimizationSummary}
                          rowOnHover={setStrategyInFocus}
                        />
                      </EuiFlexItem>
                    </EuiFlexGroup>
                  </>
                ),
              },
              {
                id: 'chart',
                name: 'Chart',
                content: (
                  <>
                    <EuiSpacer size='l' />
                    <ChartMetricsTradeoff
                      evaluation={runWithForensics}
                      onStrategyClick={(strategyId) => history.push(`/workspaces/${workspace._id}/strategies/${strategyId}`)}
                    />
                    {isOptimized && optimizationSummary &&
                      <>
                        <EuiSpacer size='xl' />
                        <ChartSensitivity summary={optimizationSummary} />
                      </>
                    }
                  </>
                ),
              },
              {
                id: 'heatmap',
                name: 'Breakdown',
                content: (
                  <>
                    <EuiSpacer size='l' />
                    {renderHeatmapControls()}
                    <EuiSpacer size='m' />
                    {metricSelected &&
                      <ChartMetricsHeatmap
                        evaluation={runWithForensics}
                        metric={metricSelected._id}
                        xGroupBy={xGroupBySelected._id}
                        yGroupBy={yGroupBySelected._id}
                        ySortBy={ySortBySelected._id}
                        variantOverride={variantOverride}
                      />
                    }
                    {isOptimized &&
                      <EuiText color='subdued' size='xs' style={{ marginTop: '8px' }}>
                        <p>
                          Each strategy shows its winning variant on every scenario, so the rows compare like with like.
                          {optimizationSummary?.score_basis === 'holdout' && ' The scenarios include the tuning and holdout sets. Only holdout scores are unbiased.'}
                          {variantOverride && ' The chosen variant ran on tuning scenarios only unless it is the winner or the baseline.'}
                        </p>
                      </EuiText>
                    }
                  </>
                ),
              },
              ...(((unratedPage?.total ?? 0) > 0 || unratedWinnersOnly) ? [{
                id: 'unrated',
                name: <>Unrated docs <EuiNotificationBadge color='subdued'>{unratedPage?.total ?? 0}</EuiNotificationBadge></>,
                content: (
                  <>
                    <EuiSpacer size='l' />
                    <EuiFlexGroup alignItems='center' justifyContent='flexEnd'>
                      {isOptimized &&
                        <EuiFlexItem grow={false}>
                          <EuiSwitch
                            checked={unratedWinnersOnly}
                            compressed
                            label='Documents from winning variants only'
                            onChange={(e) => {
                              setUnratedWinnersOnly(e.target.checked)
                              loadUnratedPage(1, unratedPage.size, e.target.checked)
                            }}
                          />
                        </EuiFlexItem>
                      }
                      <EuiFlexItem grow={false}>
                        <EuiButton onClick={(e) => {
                          const pairs = []
                          ;(unratedPage.items || []).forEach((doc) => {
                            pairs.push(`(_id:"${doc._id}" AND _index:"${doc._index}")`)
                          })
                          const query = encodeURIComponent(pairs.join(' OR '))
                          history.push(`/workspaces/${workspace._id}/judgements?query=${query}`)
                        }}>
                          Judge this page
                        </EuiButton>
                      </EuiFlexItem>
                    </EuiFlexGroup>
                    <EuiSpacer size='m' />
                    <div style={{ height: '600px', overflowY: 'scroll' }}>
                      <PanelUnratedDocs evaluation={runWithForensics} />
                    </div>
                    <EuiSpacer size='m' />
                    <EuiFlexGroup justifyContent='flexEnd' alignItems='center' gutterSize='s'>
                      <EuiFlexItem grow={false}>
                        <small>Page {unratedPage.page} of {Math.max(1, Math.ceil(unratedPage.total / unratedPage.size))}</small>
                      </EuiFlexItem>
                      <EuiFlexItem grow={false}>
                        <EuiButton size='s' iconType='arrowLeft'
                          isDisabled={unratedPage.page <= 1}
                          onClick={() => loadUnratedPage(unratedPage.page - 1, unratedPage.size, unratedWinnersOnly)}>
                          Previous
                        </EuiButton>
                      </EuiFlexItem>
                      <EuiFlexItem grow={false}>
                        <EuiButton size='s' iconType='arrowRight' iconSide='right'
                          isDisabled={unratedPage.page >= Math.ceil(unratedPage.total / unratedPage.size)}
                          onClick={() => loadUnratedPage(unratedPage.page + 1, unratedPage.size, unratedWinnersOnly)}>
                          Next
                        </EuiButton>
                      </EuiFlexItem>
                    </EuiFlexGroup>
                  </>
                ),
              }] : []),
            ]
            const selectedTab = tabs.find((t) => t.id === selectedTabId) || tabs[0]
            return (
              <EuiPanel paddingSize='none'>
                <EuiPanel color='transparent'>
                  <EuiTabbedContent
                    tabs={tabs}
                    selectedTab={selectedTab}
                    onTabClick={onTabClick}
                  />
                </EuiPanel>
              </EuiPanel>
            )
          })()}
          <EuiSpacer size='m' />
        </>
      }

    </Page>
  )
}

export default RunsView