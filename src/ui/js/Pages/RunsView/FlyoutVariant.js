/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useMemo, useState } from 'react'
import {
  EuiBadge,
  EuiBasicTable,
  EuiButton,
  EuiButtonEmpty,
  EuiButtonGroup,
  EuiCallOut,
  EuiCodeBlock,
  EuiFieldText,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutFooter,
  EuiFlyoutHeader,
  EuiFormRow,
  EuiLink,
  EuiSpacer,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import api from '../../api'
import hp from '../../hyperparameters'
import utils from '../../utils'

const METRIC_LABELS = { mrr: 'MRR', ndcg: 'NDCG', precision: 'Precision', recall: 'Recall' }
const fmt = (value, digits = 4) =>
  (value === null || value === undefined) ? '–' : Number(value).toFixed(digits)

/**
 * Flyout for one hyperparameter variant of a strategy in a run: its values,
 * its scores, the template it ran with, and a way to promote it.
 *
 * Promotion updates the promoted values of the strategy's hyperparameters, or
 * forks the strategy as it was in the run. Either way the strategy keeps its
 * valid testable values, so the next round can tune around the new promoted
 * values.
 */
const FlyoutVariant = ({
  workspaceId,
  benchmarkId,
  runId,
  strategyId,
  variant,
  runtimeStrategy,
  metrics = [],
  objective = { metric: 'ndcg', aggregation: 'mean' },
  onClose,
  onPromoted,
}) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [mode, setMode] = useState('update_values')
  const [name, setName] = useState('')
  const [isPromoting, setIsPromoting] = useState(false)
  const [promoted, setPromoted] = useState(null)

  ////  Derived  ///////////////////////////////////////////////////////////////

  const strategyName = runtimeStrategy?.name || strategyId
  const definitions = runtimeStrategy?._resolved_hyperparameters || runtimeStrategy?.hyperparameters || []
  const runPromoted = hp.promotedValues(definitions)

  // The template with this variant's values bound, ready for production
  const rendered = useMemo(() => {
    const source = runtimeStrategy?.template?.source
    if (!source)
      return null
    try {
      return utils.formatJsonWithMustache(hp.renderHyperparameters(source, variant.values || {}))
    } catch (e) {
      return null
    }
  }, [runtimeStrategy, variant])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onPromote = async () => {
    let response
    try {
      setIsPromoting(true)
      const body = {
        run_id: runId,
        variant_id: variant.variant_id,
        strategy_id: strategyId,
        mode,
      }
      if (mode === 'fork' && name.trim())
        body.name = name.trim()
      response = await api.strategies_promote(workspaceId, body)
    } catch (e) {
      return addToast(api.errorToast(e, { title: 'Failed to promote the variant' }))
    } finally {
      setIsPromoting(false)
    }
    if (response.status > 299) {
      return addToast({
        color: 'danger',
        title: 'Failed to promote the variant',
        text: response.data?.error?.reason || response.data?.message || response.statusText,
      })
    }
    setPromoted(response.data)
    addToast({
      color: 'success',
      iconType: 'check',
      title: mode === 'fork' ? 'Forked the strategy' : 'Updated the strategy promoted values',
      text: (
        <EuiLink href={`#/workspaces/${workspaceId}/strategies/${response.data.strategy_id}`}>
          Open the strategy
        </EuiLink>
      ),
    })
    onPromoted?.(response.data)
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderValues = () => (
    <EuiBasicTable
      columns={[
        { field: 'name', name: 'Hyperparameter', render: (n) => <EuiText size='xs'><b>{n}</b></EuiText> },
        {
          field: 'value',
          name: 'Value',
          render: (_, row) => <EuiText size='xs'>{hp.formatValue(row.value)}</EuiText>,
        },
        {
          field: 'promoted',
          name: 'Promoted value in the run',
          render: (_, row) => (
            <EuiText color={row.changed ? 'default' : 'subdued'} size='xs'>
              {hp.formatValue(row.promoted)}{row.changed && <EuiBadge color='accent'><small>Changed</small></EuiBadge>}
            </EuiText>
          ),
        },
      ]}
      items={Object.entries(variant.values || {}).map(([n, value]) => ({
        name: n,
        value,
        promoted: runPromoted[n],
        changed: n in runPromoted && JSON.stringify(runPromoted[n]) !== JSON.stringify(value),
      }))}
      itemId='name'
      responsiveBreakpoint={false}
    />
  )

  const renderScores = () => {
    const tuning = variant.aggregates?.tuning
    const holdout = variant.aggregates?.holdout
    const rows = metrics.map((metric) => ({
      metric,
      tuning: tuning?.metrics?.[metric]?.avg,
      holdout: holdout?.metrics?.[metric]?.avg,
    }))
    return (
      <>
        <EuiBasicTable
          columns={[
            {
              field: 'metric',
              name: 'Metric',
              render: (metric) => (
                <EuiText size='xs'>
                  {METRIC_LABELS[metric] || metric}
                  {metric === objective.metric && <> <EuiBadge color='hollow'><small>Objective</small></EuiBadge></>}
                </EuiText>
              ),
            },
            { field: 'tuning', name: 'Tuning (in-sample)', render: (v) => <EuiText size='xs'>{fmt(v)}</EuiText> },
            { field: 'holdout', name: 'Holdout', render: (v) => <EuiText size='xs'>{fmt(v)}</EuiText> },
          ]}
          itemId='metric'
          items={rows}
          responsiveBreakpoint={false}
        />
        <EuiSpacer size='xs' />
        <EuiText color='subdued' size='xs'>
          <small>
            Latency (median): {tuning?.took?.median != null ? `${Math.round(tuning.took.median)} ms` : '–'}
            {' · '}
            Judgement coverage: {tuning?.coverage != null ? `${Math.round(tuning.coverage * 100)}%` : '–'}
          </small>
        </EuiText>
        {!holdout &&
          <EuiText color='subdued' size='xs'>
            <small>Only the winner and the baseline variant run on the holdout.</small>
          </EuiText>
        }
      </>
    )
  }

  const renderPromote = () => (
    <>
      <EuiButtonGroup
        buttonSize='compressed'
        idSelected={mode}
        isFullWidth
        legend='Promotion mode'
        onChange={setMode}
        options={[
          { id: 'update_values', label: 'Update promoted values' },
          { id: 'fork', label: 'Fork as new strategy' },
        ]}
      />
      <EuiSpacer size='s' />
      {mode === 'update_values' &&
        <EuiText color='subdued' size='s'>
          <p>
            Sets the promoted values of the hyperparameters of <b>{strategyName}</b> to these values. The strategy keeps its
            valid testable values. It warns you if the template changed since this run.
          </p>
        </EuiText>
      }
      {mode === 'fork' &&
        <>
          <EuiText color='subdued' size='s'>
            <p>
              Creates a new strategy from <b>{strategyName}</b> as it was in this run, with these values as its promoted values.
            </p>
          </EuiText>
          <EuiSpacer size='s' />
          <EuiFormRow display='rowCompressed' fullWidth label='Name (optional)'>
            <EuiFieldText
              compressed
              fullWidth
              onChange={(e) => setName(e.target.value)}
              placeholder={`${strategyName} (${variant.variant_id.slice(0, 8)})`}
              value={name}
            />
          </EuiFormRow>
        </>
      }
      <EuiSpacer size='m' />
      <EuiButton fill iconType='sortUp' isLoading={isPromoting} onClick={onPromote}>
        {mode === 'fork' ? 'Fork' : 'Update promoted values'}
      </EuiButton>
      {promoted?.warnings?.length > 0 &&
        <>
          <EuiSpacer size='s' />
          <EuiCallOut color='warning' iconType='help' size='s' title='Check the promotion'>
            <ul style={{ margin: 0, paddingLeft: '16px' }}>
              {promoted.warnings.map((message) => <li key={message}><small>{message}</small></li>)}
            </ul>
          </EuiCallOut>
        </>
      }
    </>
  )

  return (
    <EuiFlyout onClose={onClose} ownFocus size='m'>
      <EuiFlyoutHeader hasBorder>
        <EuiTitle size='m'>
          <h2>
            Variant <code style={{ fontSize: 'inherit' }}>{variant.variant_id.slice(0, 8)}</code>
          </h2>
        </EuiTitle>
        <EuiSpacer size='xs' />
        <EuiText color='subdued' size='s'>
          {strategyName}{' '}
          {variant.is_baseline && <EuiBadge color='hollow'>Baseline</EuiBadge>}
          {variant.is_run_winner && <EuiBadge color='success'>Winner</EuiBadge>}
          {variant.violates_constraint && <EuiBadge color='warning'>Too slow to win</EuiBadge>}
        </EuiText>
      </EuiFlyoutHeader>
      <EuiFlyoutBody>
        <EuiTitle size='xs'><h3>Values</h3></EuiTitle>
        <EuiSpacer size='s' />
        {renderValues()}
        <EuiSpacer size='l' />

        <EuiTitle size='xs'><h3>Scores</h3></EuiTitle>
        <EuiSpacer size='s' />
        {renderScores()}
        <EuiSpacer size='l' />

        <EuiTitle size='xs'><h3>Promote</h3></EuiTitle>
        <EuiSpacer size='s' />
        {renderPromote()}
        <EuiSpacer size='l' />

        {rendered &&
          <>
            <EuiTitle size='xs'><h3>Production template</h3></EuiTitle>
            <EuiText color='subdued' size='xs'>
              <p>The strategy template with these values applied. Scenario params stay as Mustache variables.</p>
            </EuiText>
            <EuiSpacer size='s' />
            <EuiCodeBlock isCopyable language='json' overflowHeight={400} paddingSize='m' style={{ width: '100%' }}>
              {rendered}
            </EuiCodeBlock>
          </>
        }
      </EuiFlyoutBody>
      <EuiFlyoutFooter>
        <EuiFlexGroup justifyContent='spaceBetween'>
          <EuiFlexItem grow={false}>
            <EuiButtonEmpty flush='left' iconType='cross' onClick={onClose}>
              Close
            </EuiButtonEmpty>
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiFlyoutFooter>
    </EuiFlyout>
  )
}

export default FlyoutVariant
