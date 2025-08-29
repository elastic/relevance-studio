/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  EuiBadge,
  EuiButtonEmpty,
  EuiButtonIcon,
  EuiCallOut,
  EuiCode,
  EuiEmptyPrompt,
  EuiFieldText,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutFooter,
  EuiFlyoutHeader,
  EuiFormRow,
  EuiInMemoryTable,
  EuiPopover,
  EuiPopoverTitle,
  EuiSpacer,
  EuiTabbedContent,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import api from '../../api'

const FormIndices = ({ index_pattern, onChangeIndexPattern }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [hasSearched, setHasSearched] = useState(false)
  const [inspectingIndex, setInspectingIndex] = useState(null)
  const [inspectingTab, setInspectingTab] = useState(null)
  const [isCalloutDismissed, setIsCalloutDismissed] = useState(false)
  const [isLoadingMatches, setIsLoadingMatches] = useState(true)
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)
  const [matches, setMatches] = useState([])

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Autofocus on the index pattern field with the cursor at the beginning
   */
  const inputRef = useRef(null)
  useLayoutEffect(() => {
    const id = requestAnimationFrame(() => {
      if (!inputRef.current)
        return
      inputRef.current.focus()
      inputRef.current.setSelectionRange(0, 0)
    })
    return () => cancelAnimationFrame(id)
  }, [])

  /**
   * Get indices, aliases, and data streams that match the given index pattern
   */
  useEffect(() => {
    if (!index_pattern)
      return
    const handler = setTimeout(async () => {
      try {
        setIsLoadingMatches(true)
        const response = await api.content_resolve(index_pattern)
        const _matches = []
        response.data?.indices?.forEach((match) => {
          _matches.push({
            name: match.name,
            type: 'index',
          })
        })
        response.data?.aliases?.forEach((match) => {
          _matches.push({
            name: match.name,
            type: 'alias',
          })
        })
        response.data?.data_streams?.forEach((match) => {
          _matches.push({
            name: match.name,
            type: 'data_stream',
          })
        })
        setMatches(_matches)
      } catch (e) {
        addToast(api.errorToast(e, { title: 'Failed to find matching indices' }))
      } finally {
        setIsLoadingMatches(false)
        setHasSearched(true)
      }
    }, 250)
    // if index_pattern changes before timeout fires, cancel previous
    return () => clearTimeout(handler)
  }, [index_pattern])

  const getFields = () => {
    
  }

  const openFlyout = (indexName) => {
    setInspectingIndex(indexName)
    setInspectingTab('fields')
  }

  const closeFlyout = () => {
    setInspectingIndex(null)
    setInspectingTab(null)
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFlyout = () => (
    <EuiFlyout onClose={() => setInspectingIndex(null)} ownFocus size='m'>
      <EuiFlyoutHeader>
        <EuiTitle size='m'>
          <h2>{inspectingIndex}</h2>
        </EuiTitle>
      </EuiFlyoutHeader>
      <EuiFlyoutBody>
        <EuiTabbedContent
          tabs={[
            {
              id: 'fields',
              name: (
                <div>
                  Fields
                </div>
              ),
              content: <>test</>
            },
          ]}
        />
      </EuiFlyoutBody>
      <EuiFlyoutFooter>
        <EuiButtonEmpty flush='left' iconType='cross' onClick={() => setInspectingIndex(null)}>
          Close
        </EuiButtonEmpty>
      </EuiFlyoutFooter>
    </EuiFlyout>
  )

  return (
    <>

      {!!inspectingIndex &&
        renderFlyout()
      }

      {/* Index pattern */}
      <EuiFormRow style={{ width: '500px' }}>
        <>
          <EuiFieldText
            aria-label='Index Pattern'
            append={
              <EuiPopover
                button={
                  <EuiButtonIcon
                    aria-level='Index pattern examples'
                    iconType='documentation'
                    onClick={() => setIsPopoverOpen(!isPopoverOpen)}
                  />
                }
                closePopover={() => setIsPopoverOpen(false)}
                isOpen={isPopoverOpen}
                style={{ maxHeight: '200px', overflow: 'scroll' }}
              >
                <EuiPopoverTitle>
                  Index Pattern
                </EuiPopoverTitle>
                <EuiText>
                  <p>An index pattern is a string that you use to match one or more indices, aliases, or data streams.</p>
                  <p>Match multiple sources with a wildcard (<EuiCode>*</EuiCode>).</p>
                  <p><EuiCode>products-*</EuiCode></p>
                  <p>Separate multiple single sources with a comma (<EuiCode>,</EuiCode>).</p>
                  <p><EuiCode>products-a,products-b</EuiCode></p>
                  <p>Exclude a source by preceding it with a minus sign (<EuiCode>-</EuiCode>).</p>
                  <p><EuiCode>products-*,-products-b</EuiCode></p>
                  <p>For cross-cluster search, precede with the cluster name followed by a colon (<EuiCode>:</EuiCode>).</p>
                  <p>
                    <EuiCode>cluster1:products-*</EuiCode><br />
                    <EuiCode>cluster1:products-*,cluster2:products-*</EuiCode><br />
                    <EuiCode>cluster*:products-*,products-*</EuiCode>
                  </p>
                  <p>Spaces and the characters <EuiCode>/?"{'<>'}|</EuiCode> are not allowed.</p>
                </EuiText>
              </EuiPopover>
            }
            autocomplete='off'
            onChange={onChangeIndexPattern}
            inputRef={inputRef}
            isLoading={isLoadingMatches}
            value={index_pattern}
          />

          <EuiSpacer size='m' />

          {!!matches.length && !isCalloutDismissed &&
            <>
              <EuiCallOut onDismiss={() => setIsCalloutDismissed(true)}>
                <EuiText style={{ textAlign: 'center' }} size='xs'>
                  Searches will span <b>all</b> of these indices.<br />Make sure they relate to the purpose of this workspace.
                </EuiText>
              </EuiCallOut>
              <EuiSpacer size='m' />
            </>
          }

          {/* Matches */}
          <EuiInMemoryTable
            className='content-resolve-matches'
            columns={[
              {
                field: 'name',
                width: '350px',
                sortable: true,
                truncateText: true,
                render: (name, item) => (
                  <EuiText size='xs' style={{ fontWeight: 500 }}>{item.name}</EuiText>
                )
              },
              {
                field: 'type',
                align: 'right',
                width: '125px',
                render: (name, item) => (
                  <EuiBadge color='text'>
                    <EuiText size='xs'>{item.type}</EuiText>
                  </EuiBadge>
                )
              },
              {
                name: 'Actions',
                width: '25px',
                actions: [
                  {
                    color: 'primary',
                    name: 'Inspect',
                    description: 'Inspect index',
                    icon: 'eye',
                    isPrimary: true,
                    onClick: (item) => openFlyout(item.name),
                    type: 'icon',
                  },
                ],
              }
            ]}
            rowHeader={null}
            items={matches}
            loading={isLoadingMatches}
            noItemsMessage={
              <EuiEmptyPrompt
                body={hasSearched ? <p>No matching indices found.</p> : <></>}
              />
            }
            pagination={{
              initialPageSize: 5,
              pageSizeOptions: [5, 10, 20]
            }}
            responsiveBreakpoint={false}
            sorting={{
              sort: {
                field: 'name',
                direction: 'asc',
              }
            }}
            tableLayout='auto'
          >
          </EuiInMemoryTable>
        </>
      </EuiFormRow>
    </>
  )
}

export default FormIndices