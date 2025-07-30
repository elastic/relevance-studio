/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License;
 * you may not use this file except in compliance with the Elastic License.
 */

import { useEffect, useState } from 'react'
import {
  EuiBadge,
  EuiButton,
  EuiCallOut,
  EuiLink,
  EuiSpacer,
  EuiText,
} from '@elastic/eui'
import { usePageResources, useResources } from '../../Contexts/ResourceContext'
import { useSearchHandler } from '../../Hooks'
import { ModalDelete, Page, SearchTable } from '../../Layout'
import FlyoutForm from './FlyoutForm'
import { getHistory } from '../../history'
import api from '../../api'

const Benchmarks = () => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const history = getHistory()
  const { workspace } = usePageResources()
  const isReady = useResources().hasResources(['workspace'])

  ////  State  /////////////////////////////////////////////////////////////////

  /**
   * null:   close flyout
   * true:   open flyout to create a new doc
   * object: open flyout to update a given doc (object)
   */
  const [flyout, setFlyout] = useState(null)

  /**
   * null:   close modal
   * object: open modal to delete a given doc (object)
   */
  const [modalDelete, setModalDelete] = useState(null)

  /**
   * Whether a doc is being updated or deleted
   */
  const [isProcessing, setIsProcessing] = useState(false)

  /**
   * Search state
   */
  const [hasEverSearched, setHasEverSearched] = useState(false)
  const [isIndexEmpty, setIsIndexEmpty] = useState(null)
  const [isSearchLoading, setIsSearchLoading] = useState(false)
  const [searchAggs, setSearchAggs] = useState({})
  const [searchDocs, setSearchDocs] = useState([])
  const [searchPage, setSearchPage] = useState(1)
  const [searchSize, setSearchSize] = useState(10)
  const [searchSortField, setSearchSortField] = useState("name")
  const [searchSortOrder, setSearchSortOrder] = useState("asc")
  const [searchText, setSearchText] = useState("")
  const [searchTotal, setSearchTotal] = useState(null)

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Automatically submit the search and return to page one either when the
   * workspace is ready or when the user changes pagination settings.
   */
  useEffect(() => {
    if (!isReady)
      return
    onSubmitSearch()
    setSearchPage(1)
  }, [isReady, searchSize, searchSortField, searchSortOrder])

  /**
   * Automatically submit the search when the user selects a different page in
   * the search results.
   */
  useEffect(() => {
    if (!isReady)
      return
    onSubmitSearch()
  }, [searchPage])

  /**
   * Search handler
   */
  const onSubmitSearch = useSearchHandler({
    searchFn: api.benchmarks_search, // search benchmarks
    workspaceId: workspace?._id,
    searchText,
    searchPage,
    searchSize,
    searchSortField,
    searchSortOrder,
    useAggs: true, // benchmarks have aggs
    setDocs: setSearchDocs,
    setAggs: setSearchAggs,
    setTotal: setSearchTotal,
    setLoading: setIsSearchLoading,
    setHasEverSearched: setHasEverSearched,
    setIsIndexEmpty: setIsIndexEmpty,
  })

  ////  Render  ////////////////////////////////////////////////////////////////

  const columns = [
    {
      field: 'name',
      name: 'Benchmark',
      sortable: true,
      truncateText: true,
      render: (name, doc) => (
        <EuiLink href={`#/workspaces/${workspace._id}/benchmarks/${doc._id}`}>
          {doc.name}
        </EuiLink>
      )
    },
    {
      field: 'evaluations',
      name: 'Evaluations',
      width: '100px',
      render: (name, doc) => {
        const count = searchAggs?.[doc._id]?.evaluations ?? 0
        return (
          <EuiLink onClick={(e) => {
            history.push({
              pathname: `/workspaces/${workspace._id}/bencharms/${doc._id}/evaluations`,
            })
          }}>
            {count.toLocaleString()}
          </EuiLink>
        )
      }
    },
    {
      field: 'tags',
      name: 'Tags',
      width: '100px',
      render: (name, doc) => {
        const tags = []
        for (var i in doc.tags)
          tags.push(
            <EuiBadge color='hollow' key={doc.tags[i]}>
              {doc.tags[i]}
            </EuiBadge>
          )
        return tags
      },
    },
    {
      field: 'metrics',
      name: 'Metrics',
      width: '100px',
      render: (name, doc) => {
        const tags = []
        for (var i in doc.task?.metrics)
          tags.push(
            <EuiBadge color='hollow' key={doc.task.metrics[i]}>
              {doc.task.metrics[i]}
            </EuiBadge>
          )
        return tags
      },
    },
    {
      field: 'k',
      name: 'k',
      width: '100px',
      render: (name, doc) => doc.task?.k,
    },
    {
      name: 'Actions',
      width: '100px',
      actions: [
        {
          color: 'text',
          description: 'Update this benchmark',
          icon: 'documentEdit',
          name: 'update',
          onClick: (doc) => setFlyout(doc),
          type: 'icon',
        },
        {
          color: 'danger',
          description: 'Delete this benchmark',
          icon: 'trash',
          name: 'delete',
          onClick: (doc) => setModalDelete(doc),
          type: 'icon',
        }
      ],
    }
  ]

  const renderFlyout = () => (
    <FlyoutForm
      action={flyout === true ? 'create' : 'update'}
      doc={flyout}
      isProcessing={isProcessing}
      onClose={() => setFlyout(null)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderModalDelete = () => (
    <ModalDelete
      description={
        !!searchAggs[modalDelete._id]?.evaluations &&
        <EuiText>
          This will delete {searchAggs[modalDelete._id]?.evaluations == 1 ? ' ' : 'all '}{searchAggs[modalDelete._id]?.evaluations} evaluation{searchAggs[modalDelete._id]?.evaluations == 1 ? '' : 's'} related to this benchmark.
        </EuiText>
      }
      doc={modalDelete}
      docType='benchmark'
      isLoading={isProcessing}
      onClose={() => setModalDelete(null)}
      onDelete={async () => await api.benchmarks_delete(workspace._id, modalDelete._id)}
      onSuccess={onSubmitSearch}
      setIsProcessing={setIsProcessing}
    />
  )

  const renderButtonCreate = () => (
    <EuiButton fill iconType='plusInCircle' onClick={() => setFlyout(true)}>
      Create a new benchmark
    </EuiButton>
  )

  return (
    <Page title='Benchmarks' buttons={[renderButtonCreate()]}>
      {modalDelete && renderModalDelete()}
      {flyout && renderFlyout()}
      {hasEverSearched &&
        <>
          {isIndexEmpty &&
            <EuiCallOut
              color='primary'
              title='Welcome!'
            >
              <EuiText>
                Create your first benchmark to get started.
              </EuiText>
              <EuiSpacer size='m' />
              {renderButtonCreate()}
            </EuiCallOut>
          }
          {isIndexEmpty === false &&
            <SearchTable
              docs={searchDocs}
              total={searchTotal}
              page={searchPage}
              size={searchSize}
              sortField={searchSortField}
              sortOrder={searchSortOrder}
              isLoading={isSearchLoading}
              columns={columns}
              searchText={searchText}
              onChangeText={setSearchText}
              onChangePage={setSearchPage}
              onChangeSize={setSearchSize}
              onChangeSort={(field, order) => {
                setSearchSortField(field)
                setSearchSortOrder(order)
              }}
              onSubmit={() => {
                onSubmitSearch()
                setSearchPage(1)
              }}
            />
          }
        </>
      }
    </Page>
  )
}

export default Benchmarks