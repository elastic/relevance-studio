/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import utils from '../utils'

const display = (index_pattern, fields = []) => ({
  _id: index_pattern, index_pattern, fields, template: { body: index_pattern }
})

describe('utils.makeDisplayMatchers', () => {
  it('makes a matcher per display', () => {
    const matchers = utils.makeDisplayMatchers([display('products-*'), display('movies')])
    expect(matchers.map((m) => m.display.index_pattern)).toEqual(['products-*', 'movies'])
  })

  it('separates excluded index patterns from included ones', () => {
    const [matcher] = utils.makeDisplayMatchers([display('products-*,-products-archive')])
    expect(matcher.includes.map((i) => i.indexPattern)).toEqual(['products-*'])
    expect(matcher.excludes.map((e) => e.indexPattern)).toEqual(['products-archive'])
  })

  it('skips a display that excludes without including anything', () => {
    expect(utils.makeDisplayMatchers([display('-products')])).toEqual([])
  })

  it('returns no matchers when given no displays', () => {
    expect(utils.makeDisplayMatchers(null)).toEqual([])
  })
})

describe('utils.splitIndexPatterns', () => {
  it('splits on commas and trims whitespace', () => {
    expect(utils.splitIndexPatterns('a, b ,c')).toEqual(['a', 'b', 'c'])
  })

  it('drops empty parts and tolerates a missing index pattern', () => {
    expect(utils.splitIndexPatterns('a,,')).toEqual(['a'])
    expect(utils.splitIndexPatterns(undefined)).toEqual([])
  })
})

describe('utils.makeSourceFilters', () => {
  it('deduplicates fields across displays', () => {
    const displays = [display('a', ['title', 'body']), display('b', ['title', 'year'])]
    expect(utils.makeSourceFilters(displays).sort()).toEqual(['body', 'title', 'year'])
  })
})

describe('utils.resolveIndexToDisplay', () => {
  it('matches an index by exact index pattern', () => {
    const matchers = utils.makeDisplayMatchers([display('movies')])
    expect(utils.resolveIndexToDisplay(matchers, 'movies')?.index_pattern).toBe('movies')
  })

  it('matches an index by wildcard index pattern', () => {
    const matchers = utils.makeDisplayMatchers([display('products-*')])
    expect(utils.resolveIndexToDisplay(matchers, 'products-2024')?.index_pattern).toBe('products-*')
  })

  it('returns null when no index pattern matches', () => {
    const matchers = utils.makeDisplayMatchers([display('movies')])
    expect(utils.resolveIndexToDisplay(matchers, 'products-2024')).toBe(null)
  })

  it('prefers the most specific index pattern when several match', () => {
    const matchers = utils.makeDisplayMatchers([display('products-*'), display('products-us-*')])
    expect(utils.resolveIndexToDisplay(matchers, 'products-us-1')?.index_pattern).toBe('products-us-*')
  })

  // https://github.com/elastic/relevance-studio/issues/8
  it('matches a backing index through an alias named by the index pattern', () => {
    const matchers = utils.makeDisplayMatchers([display('products')])
    const aliases = { 'products-000001': ['products'] }
    expect(utils.resolveIndexToDisplay(matchers, 'products-000001', aliases)?.index_pattern).toBe('products')
  })

  it('matches a backing index through a wildcard index pattern on its alias', () => {
    const matchers = utils.makeDisplayMatchers([display('products-*')])
    const aliases = { 'shard-a': ['products-us'] }
    expect(utils.resolveIndexToDisplay(matchers, 'shard-a', aliases)?.index_pattern).toBe('products-*')
  })

  it('prefers a display naming the index over a display naming its alias', () => {
    // The alias pattern is longer, so length alone would pick the wrong display.
    const matchers = utils.makeDisplayMatchers([display('products-catalog-live'), display('products-000001')])
    const aliases = { 'products-000001': ['products-catalog-live'] }
    expect(utils.resolveIndexToDisplay(matchers, 'products-000001', aliases)?.index_pattern)
      .toBe('products-000001')
  })

  it('still resolves through an alias when a wildcard display also matches the index', () => {
    const matchers = utils.makeDisplayMatchers([display('products'), display('products-*')])
    const aliases = { 'products-000001': ['products'] }
    // Both match, but only the wildcard matches the index name itself.
    expect(utils.resolveIndexToDisplay(matchers, 'products-000001', aliases)?.index_pattern)
      .toBe('products-*')
    // With no display on the index name, the alias display still wins.
    const aliasOnly = utils.makeDisplayMatchers([display('products')])
    expect(utils.resolveIndexToDisplay(aliasOnly, 'products-000001', aliases)?.index_pattern)
      .toBe('products')
  })

  it('does not match an index that the index pattern excludes', () => {
    const matchers = utils.makeDisplayMatchers([display('products-*,-products-archive')])
    expect(utils.resolveIndexToDisplay(matchers, 'products-2024')?.index_pattern)
      .toBe('products-*,-products-archive')
    expect(utils.resolveIndexToDisplay(matchers, 'products-archive')).toBe(null)
  })

  it('does not match an index excluded through one of its aliases', () => {
    const matchers = utils.makeDisplayMatchers([display('products-*,-archived')])
    const aliases = { 'products-000001': ['archived'] }
    expect(utils.resolveIndexToDisplay(matchers, 'products-000001', aliases)).toBe(null)
  })

  it('keeps both displays when two share an index pattern part', () => {
    const a = display('products')
    const b = display('products,movies')
    const matchers = utils.makeDisplayMatchers([a, b])
    // Neither display is dropped, and the more specific part wins for movies.
    expect(utils.resolveIndexToDisplay(matchers, 'movies')?.index_pattern).toBe('products,movies')
    expect(utils.resolveIndexToDisplay(matchers, 'products')).not.toBe(null)
  })

  it('tolerates index and alias names that collide with Object prototype members', () => {
    const matchers = utils.makeDisplayMatchers([display('movies'), display('__proto__')])
    expect(utils.resolveIndexToDisplay(matchers, 'constructor', {})).toBe(null)
    expect(utils.resolveIndexToDisplay(matchers, 'toString')).toBe(null)
    expect(utils.resolveIndexToDisplay(matchers, '__proto__')?.index_pattern).toBe('__proto__')
  })

  it('ignores an alias entry that is not a list of names', () => {
    const matchers = utils.makeDisplayMatchers([display('products')])
    expect(utils.resolveIndexToDisplay(matchers, 'products-000001', { 'products-000001': 'products' }))
      .toBe(null)
  })

  it('tolerates an absent or empty alias map', () => {
    const matchers = utils.makeDisplayMatchers([display('movies')])
    expect(utils.resolveIndexToDisplay(matchers, 'movies', undefined)?.index_pattern).toBe('movies')
    expect(utils.resolveIndexToDisplay(matchers, 'movies', {})?.index_pattern).toBe('movies')
  })

  it('matches an index against any comma-separated part of an index pattern', () => {
    const matchers = utils.makeDisplayMatchers([display('products-a, products-b')])
    expect(utils.resolveIndexToDisplay(matchers, 'products-b')?.index_pattern).toBe('products-a, products-b')
    expect(utils.resolveIndexToDisplay(matchers, 'products-c')).toBe(null)
  })

  it('matches an alias against a comma-separated part of an index pattern', () => {
    const matchers = utils.makeDisplayMatchers([display('movies,products')])
    const aliases = { 'products-000001': ['products'] }
    expect(utils.resolveIndexToDisplay(matchers, 'products-000001', aliases)?.index_pattern)
      .toBe('movies,products')
  })

  it('does not treat regex metacharacters in an index pattern as wildcards', () => {
    const matchers = utils.makeDisplayMatchers([display('.ds-logs-1')])
    expect(utils.resolveIndexToDisplay(matchers, 'xds-logs-1')).toBe(null)
    expect(utils.resolveIndexToDisplay(matchers, '.ds-logs-1')?.index_pattern).toBe('.ds-logs-1')
  })

  it('returns null for a missing index name even when a display matches everything', () => {
    // A '*' display would otherwise match undefined, since /^.*$/.test(undefined) is true.
    const matchers = utils.makeDisplayMatchers([display('*')])
    expect(utils.resolveIndexToDisplay(matchers, undefined)).toBe(null)
    expect(utils.resolveIndexToDisplay(matchers, '')).toBe(null)
    expect(utils.resolveIndexToDisplay(matchers, 'anything')?.index_pattern).toBe('*')
  })
})
