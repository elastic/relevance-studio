/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { renderHook, waitFor } from '@testing-library/react'
import useDisplays from '../Hooks/useDisplays'
import api from '../api'

jest.mock('../api', () => ({ __esModule: true, default: { content_aliases: jest.fn() } }))

const displays = [{ _id: 'd1', index_pattern: 'products', fields: ['name'], template: { body: '# {{ name }}' } }]

const ok = (data) => Promise.resolve({ status: 200, data })

describe('useDisplays', () => {
  beforeEach(() => jest.clearAllMocks())

  it('resolves a backing index to a display through its alias', async () => {
    api.content_aliases.mockReturnValue(ok({ 'products-000001': ['products'] }))
    const { result } = renderHook(() => useDisplays(displays, 'products'))
    await waitFor(() =>
      expect(result.current.resolveIndexToDisplay('products-000001')?._id).toBe('d1')
    )
    expect(result.current.sourceFilters).toEqual(['name'])
  })

  it('falls back to index names alone when the alias request fails', async () => {
    api.content_aliases.mockReturnValue(Promise.reject(new Error('boom')))
    const { result } = renderHook(() => useDisplays(displays, 'products'))
    await waitFor(() => expect(api.content_aliases).toHaveBeenCalled())
    expect(result.current.resolveIndexToDisplay('products-000001')).toBe(null)
    expect(result.current.resolveIndexToDisplay('products')?._id).toBe('d1')
  })

  it('ignores a non-2xx response, which the client resolves rather than throws', async () => {
    // The body of a 404 must never reach the alias map, so give it content that
    // would resolve a display if the status guard were dropped.
    api.content_aliases.mockReturnValue(
      Promise.resolve({ status: 404, data: { 'products-000001': ['products'] } })
    )
    const { result } = renderHook(() => useDisplays(displays, 'products'))
    await waitFor(() => expect(api.content_aliases).toHaveBeenCalled())
    expect(result.current.resolveIndexToDisplay('products-000001')).toBe(null)
  })

  it('sends a trimmed index pattern, which Elasticsearch reads literally', async () => {
    api.content_aliases.mockReturnValue(ok({}))
    renderHook(() => useDisplays(displays, 'products-a, products-b'))
    await waitFor(() => expect(api.content_aliases).toHaveBeenCalledWith('products-a,products-b'))
  })

  it('does not request aliases without an index pattern', () => {
    renderHook(() => useDisplays(displays, undefined))
    expect(api.content_aliases).not.toHaveBeenCalled()
  })

  it('drops the aliases of a prior index pattern when the index pattern is cleared', async () => {
    api.content_aliases.mockReturnValue(ok({ 'products-000001': ['products'] }))
    const { result, rerender } = renderHook(
      ({ p }) => useDisplays(displays, p),
      { initialProps: { p: 'products' } }
    )
    await waitFor(() =>
      expect(result.current.resolveIndexToDisplay('products-000001')?._id).toBe('d1')
    )
    rerender({ p: undefined })
    expect(result.current.resolveIndexToDisplay('products-000001')).toBe(null)
  })

  it('ignores a stale response that lost the race with a newer index pattern', async () => {
    let resolveSlow
    api.content_aliases.mockImplementation((indexPattern) =>
      indexPattern === 'products'
        ? new Promise((resolve) => { resolveSlow = resolve })
        : ok({ 'movies-000001': ['movies'] })
    )
    const moviesDisplays = [{ _id: 'd2', index_pattern: 'movies', fields: [], template: {} }]
    const { result, rerender } = renderHook(
      ({ d, p }) => useDisplays(d, p),
      { initialProps: { d: displays, p: 'products' } }
    )

    // Switch workspaces before the first request resolves, then let it land.
    rerender({ d: moviesDisplays, p: 'movies' })
    await waitFor(() =>
      expect(result.current.resolveIndexToDisplay('movies-000001')?._id).toBe('d2')
    )
    resolveSlow({ status: 200, data: { 'products-000001': ['products'] } })

    // The stale aliases of the previous workspace must not be applied.
    await waitFor(() => expect(api.content_aliases).toHaveBeenCalledTimes(2))
    expect(result.current.resolveIndexToDisplay('products-000001')).toBe(null)
    expect(result.current.resolveIndexToDisplay('movies-000001')?._id).toBe('d2')
  })
})
