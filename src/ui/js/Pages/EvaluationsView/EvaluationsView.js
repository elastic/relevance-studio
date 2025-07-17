import { useState } from 'react'
import {
  EuiButton,
  EuiFilterButton,
  EuiFilterGroup,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiFormRow,
  EuiPanel,
  EuiPopover,
  EuiSelectable,
  EuiSkeletonText,
  EuiSkeletonTitle,
  EuiSpacer,
  EuiTitle,
} from '@elastic/eui'
import { Page } from '../../Layout'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import FlyoutRuntime from './FlyoutRuntime'
import ChartMetricsScatterplot from './ChartMetricsScatterplot'
import ChartMetricsHeatmap from './ChartMetricsHeatmap'
import PanelUnratedDocs from './PanelUnratedDocs'
import TableMetrics from './TableMetrics'
import utils from '../../utils'

const EvaluationsView = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { benchmark, evaluation } = usePageResources()
  const isReady = useResources().hasResources(['project', 'benchmark', 'evaluation'])

  ////  State  /////////////////////////////////////////////////////////////////

  const [strategyInFocus, setStrategyInFocus] = useState(null)
  const [isFlyoutRuntimeOpen, setIsFlyoutRuntimeOpen] = useState(false)
  const [metricOpen, setMetricOpen] = useState(false)
  const [metricOptions, setMetricOptions] = useState([
    { _id: 'ndcg', label: 'NDCG', checked: 'on' },
    { _id: 'precision', label: 'Precision' },
    { _id: 'recall', label: 'Recall' },
  ])
  const [metricSelected, setMetricSelected] = useState({
    _id: 'ndcg', label: 'NDCG', checked: 'on'
  })
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

  const downloadEvaluation = () => {
    const blob = new Blob([utils.jsonStringifySortedKeys(evaluation, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `evaluation-${evaluation._id}.json`
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
            {metricSelected.label}
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
      onClick={() => downloadEvaluation()}>
      Download evaluation
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
    <Page panelled={true} title={
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
          runtime={evaluation?.runtime}
          onClose={() => setIsFlyoutRuntimeOpen(false)}
        />
      }

      {/* Metrics */}
      <EuiPanel paddingSize='none'>
        <EuiPanel color='transparent'>
          <EuiTitle size='s'>
            <h2>Summary</h2>
          </EuiTitle>
        </EuiPanel>
        <EuiHorizontalRule margin='none' />
        <EuiPanel color='transparent'>
          <EuiSkeletonText lines={16} isLoading={!isReady}>
            {evaluation?.results &&
              <EuiFlexGroup>

                {/* Table */}
                <EuiFlexItem>
                  <TableMetrics evaluation={evaluation} rowOnHover={setStrategyInFocus} />
                </EuiFlexItem>

                {/* Scatterplot */}
                <EuiFlexItem grow={false}>
                  <EuiPanel hasBorder paddingSize='none'>
                    <EuiPanel color='subdued'>
                      <ChartMetricsScatterplot evaluation={evaluation} strategyInFocus={strategyInFocus} />
                    </EuiPanel>
                  </EuiPanel>
                </EuiFlexItem>
              </EuiFlexGroup>
            }
          </EuiSkeletonText>
        </EuiPanel>
      </EuiPanel>
      <EuiSpacer size='m' />

      {/* Heatmap */}
      <EuiPanel paddingSize='none'>
        <EuiPanel color='transparent'>
          <EuiTitle size='s'>
            <h2>Strategies by scenario</h2>
          </EuiTitle>
        </EuiPanel>
        <EuiHorizontalRule margin='none' />
        <EuiPanel color='transparent'>
          <EuiSkeletonText lines={16} isLoading={!isReady}>
            {evaluation?.results &&
              <>
                {renderHeatmapControls()}
                <EuiSpacer size='m' />
                <ChartMetricsHeatmap
                  evaluation={evaluation}
                  metric={metricSelected._id}
                  xGroupBy={xGroupBySelected._id}
                  yGroupBy={yGroupBySelected._id}
                  ySortBy={ySortBySelected._id}
                />
              </>
            }
          </EuiSkeletonText>
        </EuiPanel>
      </EuiPanel>
      <EuiSpacer size='m' />

      {/* Unrated docs */}
      <EuiPanel paddingSize='none'>
        <EuiPanel color='transparent'>
          <EuiTitle size='s'>
            <h2>Unrated docs</h2>
          </EuiTitle>
        </EuiPanel>
        <EuiHorizontalRule margin='none' />
        <EuiPanel color='transparent'>
          <EuiSkeletonText lines={16} isLoading={!isReady}>
            {evaluation?.results &&
              <PanelUnratedDocs evaluation={evaluation} />
            }
          </EuiSkeletonText>
        </EuiPanel>
      </EuiPanel>
      <EuiSpacer size='m' />
    </Page>
  )
}

export default EvaluationsView