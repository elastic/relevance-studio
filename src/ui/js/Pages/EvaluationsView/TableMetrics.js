import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButtonIcon,
  EuiCodeBlock,
  EuiInMemoryTable,
  EuiPanel,
  EuiProgress,
  EuiScreenReaderOnly,
  EuiText,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources } from '../../Contexts/ResourceContext'
import { getHistory } from '../../history'

const TableMetrics = ({ evaluation, rowOnHover }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { darkMode } = useAppContext()
  const { project } = usePageResources()

  ////  State  /////////////////////////////////////////////////////////////////

  const [items, setItems] = useState([])
  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})
  const [sort, setSort] = useState({
    field: 'name',
    direction: 'asc',
  })

  const toggleDetails = (item) => {
    setItemIdToExpandedRowMap(prev => {
      const next = { ...prev }
      next[item.strategy_id] ? delete next[item.strategy_id] : (next[item.strategy_id] = renderDetails(item))
      return next
    })
  }

  /**
   * Configure color bands
   */
  const numBands = 5
  const colors = [
    '#E55940', // Dark Poppy
    '#FFAD18', // Dark Yellow
    '#FEC514', // Yellow
    '#02BCB7', // Teal
    darkMode ? '#48EFCF' : '#128D91', // Light Teal : Dark Teal
  ]
  const min = 0.0
  const max = 1.0
  const breakpoints = [min, 0.5, 0.7, 0.9, max]
  const bands = colors.map((color, i) => ({
    color,
    start: i === 0 ? -Infinity : breakpoints[i],
    end: i === numBands - 1 ? Infinity : breakpoints[i + 1],
  }))
  const getColorBand = (value) => {
    return bands.find(b => value >= b.start && value < b.end)?.color || colors[colors.length - 1]
  }

  const runtimeStrategy = (strategyId) => evaluation.runtime?.strategies[strategyId]

  const sortPriority = ['ndcg', 'precision', 'recall']

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Create chart data from evaluation results.
   */
  useEffect(() => {
    if (!evaluation.results)
      return
    const rows = []
    for (const _id in evaluation.summary.strategy_id) {
      let row = {
        strategy_id: _id,
        name: runtimeStrategy(_id).name,
        tags: runtimeStrategy(_id).tags,
        metrics: evaluation.summary.strategy_id[_id]._total.metrics,
        unrated_docs: evaluation.summary.strategy_id[_id]._total.unrated_docs,
      }
      row['rated_docs'] = {
        percent: 100 - row.unrated_docs.percent
      }
      rows.push(row)
    }
    setItems(rows)

    // Sort by preferred metric, otherwise by strategy name.
    // Only auto-apply sort if user hasn't changed it yet.
    if (sort.field === 'name') {
      for (const metric of sortPriority) {
        if ((evaluation.task?.metrics || []).includes(metric)) {
          setSort({
            field: `metrics.${metric}.avg`,
            direction: 'desc',
          });
          break;
        }
      }
    }
  }, [evaluation])

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderDetails = (item) => {
    return (
      <EuiPanel color='transparent' paddingSize='none'>
        <EuiCodeBlock
          isCopyable
          language='json'
          paddingSize='m'
          overflowHeight={400}
          style={{ width: '100%' }}
        >
          {runtimeStrategy(item.strategy_id)?.template?.source}
        </EuiCodeBlock>
      </EuiPanel>
    )
  }

  const columns = [
    {
      align: 'left',
      width: '40px',
      isExpander: true,
      name: (
        <EuiScreenReaderOnly>
          <span>Expand row</span>
        </EuiScreenReaderOnly>
      ),
      mobileOptions: { header: false },
      render: (item) => {
        const _itemsToExpandedRows = { ...itemsToExpandedRows }
        return (
          <EuiButtonIcon
            onClick={() => toggleDetails(item)}
            aria-label={
              _itemsToExpandedRows[item.strategy_id] ? 'Collapse' : 'Expand'
            }
            iconType={
              _itemsToExpandedRows[item.strategy_id] ? 'arrowDown' : 'arrowRight'
            }
          />
        )
      },
    },
    {
      field: 'name',
      name: 'Strategy',
      sortable: true,
      render: (name, item) => item.name
    },
    {
      field: 'tags',
      name: 'Tags',
      width: '100px',
      render: (name, item) => {
        const tags = []
        for (var i in item.tags)
          tags.push(
            <EuiBadge color='hollow' key={item.tags[i]}>
              {item.tags[i]}
            </EuiBadge>
          )
        return tags
      },
    },
  ]
  if ((evaluation.task?.metrics || []).includes('ndcg')) {
    columns.push({
      field: 'metrics.ndcg.avg',
      name: (
        <>
          NDCG <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
        </>
      ),
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => (
        <div style={{ position: 'relative', width: '100%' }}>
          <EuiProgress
            color={getColorBand(item.metrics.ndcg.avg)}
            label={item.metrics.ndcg.avg ? item.metrics.ndcg.avg.toFixed(4) : '-'}
            max={1}
            size='s'
            value={item.metrics.ndcg.avg}
          />
        </div>
      )
    })
  }
  if ((evaluation.task?.metrics || []).includes('precision')) {
    columns.push({
      field: 'metrics.precision.avg',
      name: (
        <>
          Precision <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
        </>
      ),
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => (
        <div style={{ position: 'relative', width: '100%' }}>
          <EuiProgress
            color={getColorBand(item.metrics.precision.avg)}
            label={item.metrics.precision.avg ? item.metrics.precision.avg.toFixed(4) : '-'}
            max={1}
            size='s'
            value={item.metrics.precision.avg}
          />
        </div>
      )
    })
  }
  if ((evaluation.task?.metrics || []).includes('recall')) {
    columns.push({
      field: 'metrics.recall.avg',
      name: (
        <>
          Recall <EuiText component='span' size='xs'><small>(avg)</small></EuiText>
        </>
      ),
      sortable: true,
      style: { width: '100px' },
      render: (name, item) => (
        <div style={{ position: 'relative', width: '100%' }}>
          <EuiProgress
            color={getColorBand(item.metrics.recall.avg)}
            label={item.metrics.recall.avg ? item.metrics.recall.avg.toFixed(4) : '-'}
            max={1}
            size='s'
            value={item.metrics.recall.avg}
          />
        </div>
      )
    })
  }
  columns.push({
    field: 'rated_docs.percent',
    name: (
      <>
        Rated docs
      </>
    ),
    sortable: true,
    style: { width: '100px' },
    render: (name, item) => (
      <div style={{ position: 'relative', width: '100%' }}>
        <EuiProgress
          color={getColorBand(item.rated_docs.percent / 100)}
          label={item.rated_docs.percent.toFixed(0) + '%'}
          max={1}
          size='s'
          value={item.rated_docs.percent / 100.0}
        />
      </div>
    )
  })
  columns.push({
    name: 'Actions',
    actions: [
      {
        color: 'primary',
        description: 'Edit current strategy',
        icon: 'editorLink',
        isPrimary: true,
        name: 'Edit',
        onClick: (item) => {
          history.push({ pathname: `/projects/${project._id}/strategies/${item.strategy_id}` })
        },
        type: 'icon'
      },
    ],
  })

  return (
    <div className='evaluations-table-metrics' style={{ height: '390px', overflow: 'auto' }}>
      <EuiInMemoryTable
        allowNeutralSort={false}
        columns={columns}
        itemId='strategy_id'
        itemIdToExpandedRowMap={itemsToExpandedRows}
        items={items}
        onTableChange={({ sort: newSort }) => {
          if (newSort) setSort(newSort)
        }}
        pagination={false}
        rowProps={(item) => ({
          onMouseEnter: () => rowOnHover(item.strategy_id),
          onMouseLeave: () => rowOnHover(null),
        })}
        search={{
          box: {
            incremental: true,
            schema: true,
          },
          filters: [
            {
              autoSortOptions: false,
              field: 'tags',
              multiSelect: 'or',
              name: 'Tags',
              options: Array.from(new Set(items.flatMap(item => item?.tags || []))).map(tag => ({ value: tag })),
              type: 'field_value_selection',
            },
          ]
        }}
        sorting={{
          sort: sort
        }}
        tableLayout='auto'
      />
    </div>
  )
}

export default TableMetrics