/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import {
  EuiAccordion,
  EuiBadge,
  EuiButton,
  EuiButtonEmpty,
  EuiButtonGroup,
  EuiCallOut,
  EuiFieldNumber,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiLoadingSpinner,
  EuiPanel,
  EuiSpacer,
  EuiSwitch,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { OptimizationControls, SelectTags } from '../../Layout'
import BenchmarkResults from './BenchmarkResults'
import api from '../../api'
import eb from '../../editorBenchmark'
import hp from '../../hyperparameters'
import utils from '../../utils'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }

/**
 * The Benchmark tab of the strategy editor. It runs an ephemeral benchmark of
 * the draft across scenarios and compares it against the saved strategy.
 * With hyperparameter testing, it also searches the draft's hyperparameter
 * values. Results aren't stored.
 *
 * `saved` and `draft` are `{ name, tags, source, hyperparameters }`.
 */
const TabBenchmark = ({
  workspace,
  strategyId,
  saved,
  draft,
  isDraftSaved,
  definitionErrors = [],
  onOpenScenario,
  onLoadValues,
  onApplyValues,
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [form, setForm] = useState(eb.defaultEditorForm())
  const [isSettingsOpen, setIsSettingsOpen] = useState(true)
  const [tagOptions, setTagOptions] = useState([])
  const [isLoadingTags, setIsLoadingTags] = useState(false)
  const [estimate, setEstimate] = useState(null)
  const [estimateError, setEstimateError] = useState(null)
  const [isEstimating, setIsEstimating] = useState(false)
  const [result, setResult] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const estimateRequest = useRef(0)

  const compare = !isDraftSaved
  const hasHyperparameters = (draft.hyperparameters || []).length > 0
  const isTesting = eb.testsHyperparameters(form, draft)
  const pool = hp.hyperparametersOfPool([{ hyperparameters: draft.hyperparameters || [] }])
  const formErrors = [
    ...definitionErrors,
    ...eb.validateEditorForm(form, draft),
    ...(isTesting ? hp.validateOptimizationForm({ ...form.optimization, enabled: true }, pool) : []),
  ]
  const currentKey = eb.staleKey({ saved: compare ? saved : null, draft, form })
  const isStale = Boolean(result) && result.key !== currentKey

  const buildTask = () => eb.buildEditorTask({ strategyId, saved, draft, form, compare })

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Get the scenario tags of the workspace for the tags filter
   */
  useEffect(() => {
    if (!workspace?._id)
      return
    (async () => {
      try {
        setIsLoadingTags(true)
        const response = await api.scenarios_tags(workspace._id)
        const buckets = response.data?.aggregations?.tags?.buckets || []
        setTagOptions(buckets.map((bucket) => bucket.key).sort())
      } catch (e) {
        addToast(api.errorToast(e, { title: 'Failed to get scenario tags' }))
      } finally {
        setIsLoadingTags(false)
      }
    })()
  }, [workspace?._id])

  /**
   * Estimate the run as the settings and the draft describe it (debounced).
   * The estimate sends a few probe searches to measure the duration.
   */
  useEffect(() => {
    const request = ++estimateRequest.current
    if (!workspace?._id || !draft.source || formErrors.length) {
      setEstimate(null)
      setEstimateError(null)
      setIsEstimating(false)
      return
    }
    const timer = setTimeout(async () => {
      try {
        setIsEstimating(true)
        const response = await api.benchmarks_estimate(workspace._id, { task: buildTask(), probe: true })
        if (request !== estimateRequest.current)
          return
        if (response.status > 299) {
          setEstimate(null)
          setEstimateError(response.data?.error?.reason || response.data?.message || response.statusText || 'Failed to estimate the run')
        } else {
          setEstimate(response.data)
          setEstimateError(null)
        }
      } catch (e) {
        if (request !== estimateRequest.current)
          return
        setEstimate(null)
        setEstimateError(e?.response?.data?.error?.reason || e?.message || 'Failed to estimate the run')
      } finally {
        if (request === estimateRequest.current)
          setIsEstimating(false)
      }
    }, 1000)
    return () => clearTimeout(timer)
  }, [workspace?._id, currentKey, formErrors.length])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const setOptimizationForm = (updater) => setForm((prev) => ({
    ...prev,
    optimization: typeof updater === 'function' ? updater(prev.optimization) : updater,
  }))

  const onRun = async () => {
    const key = currentKey
    const run = {
      "@meta": {
        "status": "pending",
        "created_at": new Date().toISOString(),
        "started_at": null,
        "stopped_at": null,
      },
      "workspace_id": workspace._id,
      "task": buildTask(),
    }
    let response
    try {
      setIsRunning(true)
      response = await api.runs_run(workspace._id, run)
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to run the benchmark' }))
    } finally {
      setIsRunning(false)
    }
    if (response.status > 299 || response.data?.error)
      return addToast(utils.toastClientResponse(response))
    setResult({
      run: response.data,
      key,
      savedId: compare ? strategyId : null,
      draftId: compare ? eb.draftIdOf(strategyId) : strategyId,
    })
    setIsSettingsOpen(false)
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderSummary = () => {
    const parts = [
      form.scenario_tags.length ? `Scenarios tagged ${form.scenario_tags.join(', ')}` : 'All compatible scenarios',
      `${form.metrics.map((m) => METRIC_LABELS[m] || m).join('/') || 'No metrics'} @${form.k}`,
    ]
    if (isTesting) {
      if (estimate?.variants)
        parts.push(`${estimate.variants.toLocaleString()} variants`)
      parts.push(`${Number(form.optimization.holdout_percent) || 0}% holdout`)
    }
    return parts.join(' · ')
  }

  const renderSettings = () => (
    <>
      <EuiFormRow display='rowCompressed' fullWidth label='Scenarios'>
        <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false}>
          <EuiFlexItem grow>
            <EuiText size='xs'>
              {form.scenario_tags.length
                ? <>Compatible scenarios tagged {form.scenario_tags.map((t) => <EuiBadge color='hollow' key={t}>{t}</EuiBadge>)}</>
                : 'All compatible scenarios'}
            </EuiText>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <SelectTags
              isLoading={isLoadingTags}
              onChange={(tags) => setForm((prev) => ({ ...prev, scenario_tags: tags }))}
              options={tagOptions}
              selected={form.scenario_tags}
            />
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiFormRow>
      <EuiSpacer size='s' />
      <EuiFormRow display='rowCompressed' fullWidth label='Metrics'>
        <EuiFlexGroup gutterSize='s' responsive={false}>
          <EuiFlexItem grow={3}>
            <EuiButtonGroup
              buttonSize='compressed'
              idToSelectedMap={Object.fromEntries(Object.keys(METRIC_LABELS).map((m) => [m, form.metrics.includes(m)]))}
              isFullWidth
              legend='Metrics'
              onChange={(id) => setForm((prev) => ({
                ...prev,
                metrics: prev.metrics.includes(id) ? prev.metrics.filter((m) => m !== id) : [...prev.metrics, id],
              }))}
              options={Object.entries(METRIC_LABELS).map(([id, label]) => ({ id, label: <EuiText size='xs'>{label}</EuiText> }))}
              type='multi'
            />
          </EuiFlexItem>
          <EuiFlexItem grow={1}>
            <EuiFieldNumber
              aria-label='k'
              compressed
              isInvalid={!(parseInt(form.k) >= 1)}
              min={1}
              onChange={(e) => setForm((prev) => ({ ...prev, k: e.target.value }))}
              prepend='k'
              step={1}
              value={form.k}
            />
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiFormRow>
      <EuiSpacer size='s' />
      <EuiFormRow display='rowCompressed' fullWidth label='Hyperparameters'>
        {hasHyperparameters
          ? (
            <EuiSwitch
              checked={form.optimization.enabled}
              compressed
              label={<small>Test hyperparameter values</small>}
              onChange={(e) => setOptimizationForm((prev) => ({ ...prev, enabled: e.target.checked }))}
            />
          )
          : <EuiText color='subdued' size='xs'><small>Add hyperparameters to the strategy to test their values.</small></EuiText>
        }
      </EuiFormRow>
      {isTesting &&
        <OptimizationControls
          form={form.optimization}
          hyperparameters={pool}
          idPrefix='editor-benchmark-opt'
          metrics={form.metrics}
          setForm={setOptimizationForm}
          showHoldout
          showSwitch={false}
        />
      }
    </>
  )

  const renderEstimate = () => {
    if (formErrors.length)
      return null
    if (estimateError)
      return <EuiText color='danger' size='xs'><small>Failed to estimate the run: {String(estimateError)}</small></EuiText>
    if (!estimate) {
      return (
        <EuiText color='subdued' size='xs'>
          <small><EuiLoadingSpinner size='s' /> Estimating...</small>
        </EuiText>
      )
    }
    const duration = estimate.duration
    return (
      <EuiText color='subdued' size='xs' style={{ opacity: isEstimating ? 0.6 : 1 }}>
        <small>
          <b>{estimate.searches.total.toLocaleString()}</b> searches
          {' · '}<b>{estimate.variants.toLocaleString()}</b> {estimate.variants === 1 ? 'variant' : 'variants'}
          {' · '}<b>{estimate.scenarios.with_judgements.toLocaleString()}</b> judged {estimate.scenarios.with_judgements === 1 ? 'scenario' : 'scenarios'}
          {duration && <>{' · '}<b>~{utils.formatDuration((duration.low_ms + duration.high_ms) / 2)}</b></>}
          {isEstimating && <>{' '}<EuiLoadingSpinner size='s' /></>}
        </small>
      </EuiText>
    )
  }

  const renderMessages = () => {
    const errors = [...formErrors, ...(estimate?.errors || [])]
    // A current result shows its own notices, so the estimate's warnings would repeat them
    const warnings = formErrors.length || (result && !isStale) ? [] : (estimate?.warnings || [])
    return (
      <>
        {errors.length > 0 &&
          <>
            <EuiSpacer size='s' />
            <EuiCallOut color='danger' iconType='warning' size='s' title="This benchmark can't run">
              <ul style={{ margin: 0, paddingLeft: '16px' }}>
                {errors.map((message) => <li key={message}><small>{message}</small></li>)}
              </ul>
            </EuiCallOut>
          </>
        }
        {warnings.map((message) => (
          <div key={message}>
            <EuiSpacer size='s' />
            <EuiCallOut color='warning' iconType='help' size='s' title={message} />
          </div>
        ))}
      </>
    )
  }

  const renderRun = () => (
    <EuiFlexGroup alignItems='center' gutterSize='m' responsive={false}>
      <EuiFlexItem grow={false}>
        <EuiButton
          disabled={isRunning || formErrors.length > 0 || Boolean(estimate?.errors?.length)}
          fill
          iconType='play'
          isLoading={isRunning}
          onClick={onRun}
          size='s'
        >
          {isRunning ? 'Running...' : (result ? 'Rerun' : 'Run benchmark')}
        </EuiButton>
      </EuiFlexItem>
      <EuiFlexItem grow style={{ minWidth: 0 }}>
        {renderEstimate()}
      </EuiFlexItem>
    </EuiFlexGroup>
  )

  return (
    <div>
      <EuiPanel color='subdued' hasBorder={false} hasShadow={false} paddingSize='s'>
        <EuiAccordion
          buttonContent={
            <EuiText size='s'>
              Settings{!isSettingsOpen && <EuiText color='subdued' size='xs' style={{ display: 'inline', marginLeft: '8px' }}><small>{renderSummary()}</small></EuiText>}
            </EuiText>
          }
          forceState={isSettingsOpen ? 'open' : 'closed'}
          id='editor-benchmark-settings'
          onToggle={setIsSettingsOpen}
          paddingSize='s'
        >
          {renderSettings()}
        </EuiAccordion>
      </EuiPanel>
      <EuiSpacer size='s' />
      {renderRun()}
      {renderMessages()}
      <EuiSpacer size='xs' />
      <EuiText color='subdued' size='xs'>
        <small>
          {compare
            ? 'Compares the draft against the saved strategy. '
            : 'The draft matches the saved strategy, so there is nothing to compare. '}
          Results aren't saved.
        </small>
      </EuiText>
      {result &&
        <>
          <EuiSpacer size='m' />
          {isStale &&
            <>
              <EuiCallOut color='warning' iconType='clock' size='s' title='Out of date'>
                <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false}>
                  <EuiFlexItem grow>
                    <p><small>The strategy or the settings changed after this run.</small></p>
                  </EuiFlexItem>
                  <EuiFlexItem grow={false}>
                    <EuiButtonEmpty
                      disabled={isRunning || formErrors.length > 0 || Boolean(estimate?.errors?.length)}
                      iconType='refresh'
                      isLoading={isRunning}
                      onClick={onRun}
                      size='xs'
                    >
                      Rerun
                    </EuiButtonEmpty>
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiCallOut>
              <EuiSpacer size='s' />
            </>
          }
          <div style={{ opacity: isStale ? 0.7 : 1 }}>
            <BenchmarkResults
              draftId={result.draftId}
              onApplyValues={onApplyValues}
              onLoadValues={onLoadValues}
              onOpenScenario={onOpenScenario}
              run={result.run}
              savedId={result.savedId}
            />
          </div>
        </>
      }
    </div>
  )
}

export default TabBenchmark
