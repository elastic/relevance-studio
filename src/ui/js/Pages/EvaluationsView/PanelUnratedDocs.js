import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButtonGroup,
  EuiButtonIcon,
  EuiCallOut,
  EuiCode,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiHorizontalRule,
  EuiIcon,
  EuiPanel,
  EuiScreenReaderOnly,
  EuiSpacer,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import { usePageResources, useAdditionalResources } from '../../Contexts/ResourceContext'
import { DocCard, SearchCount } from '../../Layout'
import api from '../../api'

const PanelUnratedDocs = ({ evaluation }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project, displays } = usePageResources()
  useAdditionalResources(['displays'])

  ////  State  /////////////////////////////////////////////////////////////////

  const [errorContent, setErrorContent] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [indexPatternMap, setIndexPatternMap] = useState({})
  const [itemsToExpandedRows, setItemIdToExpandedRowMap] = useState({})
  const [isLoadingResults, setIsLoadingResults] = useState(false)
  const [results, setResults] = useState({})
  const [resultsPerRow, setResultsPerRow] = useState(3)

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Get index patterns and source filters from displays,
   * and search unrated docs.
   */
  useEffect(() => {
    if (!displays)
      return
    const _indexPatternMap = {}
    const _sourceFilters = {}
    displays.forEach((display) => {
      _indexPatternMap[display.index_pattern] = {
        display: display,
        regex: new RegExp(`^${display.index_pattern.replace(/\*/g, '.*')}$`)
      }
      display.fields?.forEach((field) => {
        _sourceFilters[field] = true
      })
    })
    setIndexPatternMap(_indexPatternMap)
    onSearchUnratedDocs(Object.keys(_sourceFilters))
  }, [displays])

  /**
   * Handle searching unrated docs
   */
  const onSearchUnratedDocs = (sourceFilters) => {

    // Submit API request(s)
    (async () => {

      // Prepare request body for search
      const body = {
        query: {
          bool: {
            should: [],
            minimum_should_match: 1
          }
        },
        size: 10000
      }
      for (const i in evaluation.unrated_docs) {
        const doc = evaluation.unrated_docs[i]
        body.query.bool.should.push({
          bool: {
            filter: [
              { term: { _index: doc._index } },
              { term: { _id: doc._id } }
            ]
          }
        })
      }
      if (sourceFilters)
        body._source = { includes: sourceFilters }

      // Submit API request(s)
      let response
      try {
        setIsLoadingResults(true)
        const response = await api.content_search(project.index_pattern, body)

        // Handle API response
        setErrorContent(null)
        setHasSearched(true)
        const _results = {}
        response.data?.hits?.hits?.forEach((hit) => {
          _results[hit._id] = hit
          _results[hit._id]._id = hit._id
          _results[hit._id]._index = hit._index
        })
        setResults(_results)
      } catch (e) {
        if (response?.data?.error?.reason) {
          setHasSearched(true)
          if (response?.data?.error?.reason)
            setErrorContent(response.data)
        } else {
          return addToast(api.errorToast(e, { title: 'Failed to get unrated docs' }))
        }
      } finally {
        setIsLoadingResults(false)
      }
    })()
  }

  /**
   * Given an index name, find the display whose index pattern matches it
   * with the most specificity.
   */
  const resolveIndexToDisplay = (index) => {
    const matches = []
    for (const indexPattern in indexPatternMap)
      if (indexPatternMap[indexPattern].regex.test(index))
        matches.push(indexPattern)
    if (matches.length === 0)
      return null
    const bestMatch = matches.reduce((mostSpecific, current) =>
      current.length > mostSpecific.length ? current : mostSpecific
    )
    return indexPatternMap[bestMatch].display
  }

  const runtimeScenario = (scenarioId) => evaluation.runtime?.scenarios[scenarioId]
  const runtimeStrategy = (strategyId) => evaluation.runtime?.strategies[strategyId]

  ////  Render  ////////////////////////////////////////////////////////////////

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
              _itemsToExpandedRows[item._id] ? 'Collapse' : 'Expand'
            }
            iconType={
              _itemsToExpandedRows[item._id] ? 'arrowDown' : 'arrowRight'
            }
          />
        )
      },
    },
    {
      field: 'count',
      name: 'Count',
      sortable: true,
      truncateText: true,
      render: (name, item) => item.count
    },
    {
      field: '_index',
      name: 'Index',
      sortable: true,
      truncateText: true,
      render: (name, item) => item._index
    },
    {
      field: '_id',
      name: '_id',
      sortable: true,
      truncateText: true,
      render: (name, item) => item._id
    },
    {
      field: 'card',
      name: '',
      sortable: false,
      render: (name, item) => {
        const template = resolveIndexToDisplay(item._index)?.template
        return (
          <DocCard
            key={`${item._index}~${item._id}`}
            doc={item}
            panelProps={{
              hasBorder: false,
              hasShadow: false,
              style: {
                borderTopLeftRadius: 0,
                borderTopRightRadius: 0
              }
            }}
            body={template?.body}
            imagePosition={template?.image?.position}
            imageUrl={template?.image?.url}
          />
        )
      }
    },
  ]

  const renderDocs = () => {
    const docs = []
    for (const i in evaluation.unrated_docs) {
      const doc = evaluation.unrated_docs[i]
      const template = resolveIndexToDisplay(doc._index)?.template
      const scenarios = (doc.scenarios || [])
        .map(_id => ({ _id, name: runtimeScenario(_id).name }))
        .sort((a, b) => a.name.localeCompare(b.name))
      const strategies = (doc.strategies || [])
        .map(_id => ({ _id, name: runtimeStrategy(_id).name }))
        .sort((a, b) => a.name.localeCompare(b.name))
      const scenarioList = []
      const strategyList = []
      scenarios.forEach((item) => {
        scenarioList.push(
          <div key={item._id} style={{ margin: '1px' }}>
            <EuiBadge color='hollow'>
              {item.name}
            </EuiBadge>
          </div>
        )
      })
      strategies.forEach((item) => {
        strategyList.push(
          <div key={item._id} style={{ margin: '1px' }}>
            <EuiBadge color='hollow' >
              {item.name}
            </EuiBadge>
          </div>
        )
      })
      docs.push(
        <EuiFlexItem grow={false}>
          {doc._id in results &&
            <EuiPanel paddingSize='none'>

              {/* Display the doc contents */}
              {!!doc &&
                <DocCard
                  key={`${doc._index}~${doc._id}`}
                  doc={results[doc._id]}
                  panelProps={{
                    hasBorder: false,
                    hasShadow: false,
                    style: {
                      borderBottomLeftRadius: 0,
                      borderBottomRightRadius: 0,
                    }
                  }}
                  body={template?.body}
                  imagePosition={template?.image?.position}
                  imageUrl={template?.image?.url}
                />
              }
              {!doc &&
                <DocCard
                  key={`${doc._index}~${doc._id}`}
                  doc={{ _index: doc._index, _id: doc._id, }}
                  panelProps={{
                    hasBorder: false,
                    hasShadow: false,
                    style: {
                      borderBottomLeftRadius: 0,
                      borderBottomRightRadius: 0,
                    }
                  }}
                  body={'Document not found. It might no longer exist.'}
                />
              }

              {/* Display the count of occurrences */}
              <EuiHorizontalRule margin='none' />
              <EuiPanel
                color='primary'
                hasBorder={false}
                hasShadow={false}
                paddingSize='s'
                style={{
                  borderRadius: 0,
                }}>
                <EuiText color='subdued' size='xs' style={{ paddingLeft: '8px', }}>
                  <b style={{ paddingRight: '4px' }}>{doc.count}</b> occurrence{doc.count == 1 ? '' : 's'}
                </EuiText>
              </EuiPanel>

              {/* Display the scenarios and strategies it appeared for */}
              <EuiPanel
                color='subdued'
                hasBorder={false}
                hasShadow={false}
                paddingSize='none'
                style={{
                  borderTopLeftRadius: 0,
                  borderTopRightRadius: 0,
                  borderRightStyle: 'none',
                }}>
                <EuiFlexGroup gutterSize='s'>
                  <EuiFlexItem grow>
                    <EuiPanel color='transparent' paddingSize='m' style={{ paddingTop: '8px' }}>
                      <EuiText color='subdued' size='xs'>
                        <div style={{ fontWeight: 500 }}>
                          Scenarios
                        </div>
                        <EuiSpacer size='xs' />
                        <div style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          margin: '-1px',
                        }}>
                          {scenarioList}
                        </div>
                      </EuiText>
                      <EuiSpacer size='s' />
                      <EuiText color='subdued' size='xs'>
                        <div style={{ fontWeight: 500 }}>
                          Strategies
                        </div>
                        <EuiSpacer size='xs' />
                        <div style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          margin: '-1px',
                        }}>
                          {strategyList}
                        </div>
                      </EuiText>
                    </EuiPanel>
                  </EuiFlexItem>
                </EuiFlexGroup>
              </EuiPanel>
            </EuiPanel>
          }
        </EuiFlexItem>
      )
    }
    return docs
  }

  return (
    <EuiPanel color='transparent' paddingSize='none' style={{ height: '600px', overflowY: 'scroll' }}>
      {!!evaluation.unrated_docs &&
        <>
          {/* Disclaimer */}
          <EuiCallOut>
            You are viewing the <b>current state</b> of the unrated documents for this evaluation. The contents might different from what was matched during the evaluation, but the <EuiCode transparentBackground style={{ padding: 0 }}>_index</EuiCode> and <EuiCode transparentBackground style={{ padding: 0 }}>_id</EuiCode> are the same.
          </EuiCallOut>

          {/* Show number of results and change grid size */}
          <EuiPanel color='transparent' paddingSize='m'>
            <EuiFlexGroup alignItems='center' gutterSize='s'>

              {/* Show number of results */}
              <EuiFlexItem grow={5}>
                <SearchCount showing={evaluation.unrated_docs.length} total={evaluation.unrated_docs.length} />
              </EuiFlexItem>

              {/* Change grid size */}
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
          </EuiPanel>
        </>
      }
      <EuiPanel color='transparent' paddingSize='m'>
        <EuiFlexGrid alignItems='start' columns={resultsPerRow}>
          {renderDocs()}
        </EuiFlexGrid>
      </EuiPanel>
    </EuiPanel>
  )
}

export default PanelUnratedDocs