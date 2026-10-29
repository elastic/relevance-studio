/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiBasicTable,
  EuiButton,
  EuiButtonEmpty,
  EuiCallOut,
  EuiFlexGroup,
  EuiFlexItem,
  EuiInMemoryTable,
  EuiLink,
  EuiPanel,
  EuiSelect,
  EuiSpacer,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { VariantsTable } from '../../Layout'
import eb from '../../editorBenchmark'
import hp from '../../hyperparameters'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }

const fmt = (value) => (value === null || value === undefined) ? '–' : Number(value).toFixed(4)

const DeltaBadge = ({ delta }) => {
  if (delta === null || delta === undefined)
    return <EuiText color='subdued' size='xs'>–</EuiText>
  const rounded = Number(delta.toFixed(4))
  const color = rounded > 0 ? 'success' : (rounded < 0 ? 'danger' : 'hollow')
  return <EuiBadge color={color}>{rounded > 0 ? '+' : ''}{rounded.toFixed(4)}</EuiBadge>
}

const describeValues = (values) =>
  Object.entries(values || {}).map(([name, value]) => `${name}=${hp.formatValue(value)}`).join(', ')

/**
 * The results of a Benchmark tab run: the verdict of the draft against the
 * saved strategy, the scores of each scenario, and the draft's variants when
 * the run tested hyperparameter values. `savedId` is null when the run has
 * only the draft.
 */
const BenchmarkResults = ({
  run,
  savedId,
  draftId,
  onOpenScenario,
  onLoadValues,
  onApplyValues,
}) => {
  const metrics = run?.task?.metrics || []
  const objective = run?.task?.optimization?.objective
    || { metric: metrics.includes('ndcg') ? 'ndcg' : metrics[0], aggregation: 'mean' }
  const basis = eb.scoreBasis(run, draftId)
  const counts = eb.scenarioCounts(run)
  const optimization = run?.summary?.strategy_id?.[draftId]?.optimization
  const variants = eb.draftVariants(run, draftId)
  const hasVariants = variants.length > 1
  const winner = variants.find((v) => v.is_winner)
  const resolved = run?.runtime?.strategies?.[draftId]?._resolved_hyperparameters || []

  const [metric, setMetric] = useState(objective.metric)
  const [selectedId, setSelectedId] = useState(winner?.variant_id || null)

  useEffect(() => {
    setMetric(objective.metric)
    setSelectedId(winner?.variant_id || null)
  }, [run])

  const selected = variants.find((v) => v.variant_id === selectedId) || winner

  ////  Verdict  ///////////////////////////////////////////////////////////////

  const renderBasis = () => {
    let text
    if (basis === 'holdout')
      text = `Scores are on the ${counts.holdout} holdout ${counts.holdout === 1 ? 'scenario' : 'scenarios'}, which the hyperparameter search never saw. The draft uses its best variant.`
    else if (basis === 'in_sample')
      text = `Scores cover ${counts.total} judged ${counts.total === 1 ? 'scenario' : 'scenarios'}. The draft uses its best variant on the same scenarios, so its scores are optimistic.`
    else
      text = `Scores cover ${counts.total} judged ${counts.total === 1 ? 'scenario' : 'scenarios'}. Nothing was tuned, so every scenario counts.`
    return <EuiText color='subdued' size='xs'><small>{text}</small></EuiText>
  }

  const renderVerdict = () => {
    // Without the saved strategy to compare, a hyperparameter search compares
    // the draft's best variant against its promoted values.
    const versusBaseline = !savedId && hasVariants
    const comparing = Boolean(savedId) || versusBaseline
    const rows = versusBaseline
      ? eb.compareWinnerToBaseline(run, draftId, metrics)
      : eb.compareStrategies(run, savedId, draftId, metrics)
    const [savedLabel, draftLabel, title] = versusBaseline
      ? ['Promoted', 'Best variant', 'Best variant vs promoted values']
      : ['Saved', 'Draft', savedId ? 'Draft vs saved' : 'Scores']
    const columns = [
      {
        field: 'metric',
        name: 'Metric',
        render: (m) => <EuiText size='xs'>{m === objective.metric ? <b>{METRIC_LABELS[m] || m}</b> : (METRIC_LABELS[m] || m)}</EuiText>,
      },
      ...(comparing ? [{
        field: 'saved',
        name: savedLabel,
        render: (v) => <EuiText size='xs'>{fmt(v)}</EuiText>,
      }] : []),
      {
        field: 'draft',
        name: comparing ? draftLabel : 'Score',
        render: (v, row) => <EuiText size='xs'>{row.metric === objective.metric ? <b>{fmt(v)}</b> : fmt(v)}</EuiText>,
      },
      ...(comparing ? [{
        field: 'delta',
        name: 'Change',
        render: (delta) => <DeltaBadge delta={delta} />,
      }] : []),
    ]
    const notices = optimization ? hp.optimizationNotices(optimization, run, counts) : []
    return (
      <>
        <EuiTitle size='xxs'><h3>{title}</h3></EuiTitle>
        <EuiSpacer size='xs' />
        {renderBasis()}
        <EuiSpacer size='s' />
        <EuiBasicTable columns={columns} items={rows} itemId='metric' responsiveBreakpoint={false} tableLayout='auto' />
        {notices.map((notice) => (
          <div key={notice.type}>
            <EuiSpacer size='s' />
            <EuiCallOut color={notice.color} iconType={notice.color === 'primary' ? 'iInCircle' : 'help'} size='s' title={notice.text} />
          </div>
        ))}
      </>
    )
  }

  ////  Variants  //////////////////////////////////////////////////////////////

  const renderSelectedVariant = () => {
    if (!selected)
      return null
    return (
      <EuiPanel color='subdued' hasBorder={false} hasShadow={false} paddingSize='s'>
        <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false} wrap>
          <EuiFlexItem grow style={{ minWidth: '160px' }}>
            <EuiText size='xs'>
              {selected.is_winner && <EuiBadge color='success'><small>Winner</small></EuiBadge>}
              {selected.is_baseline && <EuiBadge color='hollow'><small>Baseline</small></EuiBadge>}
              {' '}<code style={{ fontSize: '12px' }}>{selected.variant_id.slice(0, 8)}</code>
              {' '}{describeValues(selected.values)}
            </EuiText>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButtonEmpty iconType='search' onClick={() => onLoadValues(selected.values)} size='xs'>
              Use in Search
            </EuiButtonEmpty>
          </EuiFlexItem>
          <EuiFlexItem grow={false}>
            <EuiButton iconType='check' onClick={() => onApplyValues(selected.values)} size='s'>
              Apply to draft
            </EuiButton>
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiPanel>
    )
  }

  const renderVariants = () => (
    <>
      <EuiTitle size='xxs'><h3>Variants of the draft</h3></EuiTitle>
      <EuiText color='subdued' size='xs'>
        <small>Tuning scores. Select a variant to use its values in Search or apply them to the draft.</small>
      </EuiText>
      <EuiSpacer size='s' />
      {renderSelectedVariant()}
      <EuiSpacer size='s' />
      <div style={{ overflowX: 'auto' }}>
        <VariantsTable
          hyperparameters={resolved}
          items={variants}
          metrics={metrics}
          objective={objective}
          onSelect={(item) => setSelectedId(item.variant_id)}
          selectedId={selected?.variant_id}
        />
      </div>
    </>
  )

  ////  Scenarios  /////////////////////////////////////////////////////////////

  const renderScenarios = () => {
    const rows = eb.compareScenarios(run, savedId, draftId, metric)
    const columns = [
      {
        field: 'name',
        name: 'Scenario',
        sortable: true,
        truncateText: true,
        render: (name, row) => (
          <EuiText size='xs'>
            <EuiLink onClick={() => onOpenScenario({ _id: row.scenario_id, name: row.name, values: row.values })}>
              {name}
            </EuiLink>
            {row.split === 'holdout' && <>{' '}<EuiBadge color='hollow'><small>Holdout</small></EuiBadge></>}
          </EuiText>
        ),
      },
      ...(savedId ? [{
        field: 'saved',
        name: 'Saved',
        sortable: true,
        width: '80px',
        render: (v) => <EuiText size='xs'>{fmt(v)}</EuiText>,
      }] : []),
      {
        field: 'draft',
        name: savedId ? 'Draft' : 'Score',
        sortable: true,
        width: '80px',
        render: (v) => <EuiText size='xs'>{fmt(v)}</EuiText>,
      },
      ...(savedId ? [{
        field: 'delta',
        name: 'Change',
        sortable: true,
        width: '90px',
        render: (delta) => <DeltaBadge delta={delta} />,
      }] : []),
    ]
    return (
      <>
        <EuiFlexGroup alignItems='center' gutterSize='s' responsive={false}>
          <EuiFlexItem grow>
            <EuiTitle size='xxs'><h3>Scenarios</h3></EuiTitle>
            <EuiText color='subdued' size='xs'>
              <small>
                {savedId ? 'Biggest regressions first. ' : 'Weakest scores first. '}
                Open a scenario to see its results in Search.
              </small>
            </EuiText>
          </EuiFlexItem>
          <EuiFlexItem grow={false} style={{ width: '130px' }}>
            <EuiSelect
              aria-label='Scenario metric'
              compressed
              onChange={(e) => setMetric(e.target.value)}
              options={metrics.map((m) => ({ value: m, text: METRIC_LABELS[m] || m }))}
              value={metric}
            />
          </EuiFlexItem>
        </EuiFlexGroup>
        <EuiSpacer size='s' />
        <EuiInMemoryTable
          columns={columns}
          itemId='scenario_id'
          items={rows}
          key={`${metric}-${run?.['@meta']?.started_at}`}
          pagination={{ initialPageSize: 10, pageSizeOptions: [10, 25, 50] }}
          responsiveBreakpoint={false}
          sorting={{ sort: { field: savedId ? 'delta' : 'draft', direction: 'asc' } }}
          tableLayout='auto'
        />
      </>
    )
  }

  return (
    <div>
      {renderVerdict()}
      {hasVariants &&
        <>
          <EuiSpacer size='l' />
          {renderVariants()}
        </>
      }
      <EuiSpacer size='l' />
      {renderScenarios()}
    </div>
  )
}

export default BenchmarkResults
