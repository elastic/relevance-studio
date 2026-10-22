/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useMemo, useState } from 'react'
import {
  EuiButton,
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
  EuiSelectable,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiTitle,
} from '@elastic/eui'
import { Page } from '../../Layout'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import FlyoutRuntime from './FlyoutRuntime'
import ChartMetricsHeatmap from './ChartMetricsHeatmap'
import PanelUnratedDocs from './PanelUnratedDocs'
import TableMetrics from './TableMetrics'
import { getHistory } from '../../history'
import api from '../../api'
import utils from '../../utils'

const RunsView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { workspace, benchmark, run } = usePageResources()
  const isReady = useResources().hasResources(['workspace', 'benchmark', 'run'])

  ////  State  /////////////////////////////////////////////////////////////////

  const [strategyInFocus, setStrategyInFocus] = useState(null)
  const [isFlyoutRuntimeOpen, setIsFlyoutRuntimeOpen] = useState(false)
  // Forensics (runtime + unrated_docs) live in a separate store and are loaded
  // on demand to keep the run doc (and this page's initial load) small.
  const [forensics, setForensics] = useState(null)
  const [isForensicsLoading, setIsForensicsLoading] = useState(false)
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

  // Lazy-load the forensics doc (runtime + unrated_docs) once the run is ready.
  // Skipped runs have no forensics; the endpoint simply returns found: false.
  useEffect(() => {
    if (!workspace?._id || !benchmark?._id || !run?._id) return
    if (forensics !== null || isForensicsLoading) return
    let cancelled = false
    setIsForensicsLoading(true)
    api.runs_get_forensics(workspace._id, benchmark._id, run._id)
      .then((response) => {
        if (cancelled) return
        setForensics(response?.data?._source ?? {})
      })
      .catch(() => { if (!cancelled) setForensics({}) })
      .finally(() => { if (!cancelled) setIsForensicsLoading(false) })
    return () => { cancelled = true }
  }, [workspace?._id, benchmark?._id, run?._id])

  // A run-shaped object that merges the small run doc with the lazily-loaded
  // forensics (runtime + unrated_docs), so the existing child components (which
  // expect those fields together) keep working unchanged.
  const runWithForensics = useMemo(() => {
    if (!run) return run
    return {
      ...run,
      runtime: forensics?.runtime,
      unrated_docs: forensics?.unrated_docs ?? [],
    }
  }, [run, forensics])

  const downloadRun = () => {
    const blob = new Blob([utils.jsonStringifySortedKeys(runWithForensics, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `run-${run._id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
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
          runtime={forensics?.runtime}
          isLoading={isForensicsLoading}
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

      {/* Metrics */}
      {run?.summary &&
        <>
          <EuiPanel paddingSize='none'>
            <EuiPanel color='transparent'>
              <EuiTitle size='s'>
                <h2>Summary</h2>
              </EuiTitle>
            </EuiPanel>
            <EuiHorizontalRule margin='none' />
            <EuiPanel color='transparent'>
              <EuiFlexGroup>

                {/* Table */}
                <EuiFlexItem>
                  <TableMetrics evaluation={runWithForensics} rowOnHover={setStrategyInFocus} />
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer size='m' />
        </>
      }

      {/* Heatmap */}
      {run?.summary &&
        <>
          <EuiPanel paddingSize='none'>
            <EuiPanel color='transparent'>
              <EuiTitle size='s'>
                <h2>Strategies by scenario</h2>
              </EuiTitle>
            </EuiPanel>
            <EuiHorizontalRule margin='none' />
            <EuiPanel color='transparent'>
              <>
                {renderHeatmapControls()}
                <EuiSpacer size='m' />
                {metricSelected &&
                  <ChartMetricsHeatmap
                    evaluation={runWithForensics}
                    metric={metricSelected._id}
                    xGroupBy={xGroupBySelected._id}
                    yGroupBy={yGroupBySelected._id}
                    ySortBy={ySortBySelected._id}
                  />
                }
              </>
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer size='m' />
        </>
      }

      {/* Unrated docs (from the forensics store) */}
      {run?.summary && (forensics?.unrated_docs?.length ?? 0) > 0 &&
        <>
          <EuiPanel paddingSize='none'>
            <EuiFlexGroup>
              <EuiFlexItem grow>
                <EuiPanel color='transparent'>
                  <EuiTitle size='s'>
                    <h2>Unrated docs</h2>
                  </EuiTitle>
                </EuiPanel>
              </EuiFlexItem>
              <EuiFlexItem grow={false}>
                <EuiPanel color='transparent' paddingSize='none'>
                  <EuiButton style={{ margin: '8px 16px' }} onClick={(e) => {
                    const pairs = []
                    forensics.unrated_docs.forEach((doc) => {
                      pairs.push(`(_id:"${doc._id}" AND _index:"${doc._index}")`)
                    })
                    const query = encodeURIComponent(pairs.join(' OR '))
                    history.push(`/workspaces/${workspace._id}/judgements?query=${query}`)
                  }}>
                    Judge
                  </EuiButton>
                </EuiPanel>
              </EuiFlexItem>
            </EuiFlexGroup>
            <EuiHorizontalRule margin='none' />
            <EuiPanel color='transparent' style={{ height: '600px', overflowY: 'scroll' }}>
              <PanelUnratedDocs evaluation={runWithForensics} />
            </EuiPanel>
          </EuiPanel>
          <EuiSpacer size='m' />
        </>
      }


    </Page>
  )
}

export default RunsView