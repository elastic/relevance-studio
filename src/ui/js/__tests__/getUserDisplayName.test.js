/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { getUserDisplayName, getUserInitials } from '../Layout/Page'

describe('getUserDisplayName', () => {
  it('returns full_name when available', () => {
    const user = { full_name: 'Jane Doe', email: 'jane@example.com', username: '3477301940' }
    expect(getUserDisplayName(user)).toBe('Jane Doe')
  })

  it('falls back to email when full_name is absent', () => {
    const user = { email: 'jane@example.com', username: '3477301940' }
    expect(getUserDisplayName(user)).toBe('jane@example.com')
  })

  it('falls back to api_key.name when full_name and email are absent', () => {
    const user = { api_key: { name: 'my-api-key' }, username: '3477301940' }
    expect(getUserDisplayName(user)).toBe('my-api-key')
  })

  it('falls back to username when no other fields are available', () => {
    const user = { username: 'elastic' }
    expect(getUserDisplayName(user)).toBe('elastic')
  })

  it('returns null for null/undefined user', () => {
    expect(getUserDisplayName(null)).toBeNull()
    expect(getUserDisplayName(undefined)).toBeNull()
  })
})

describe('getUserInitials', () => {
  it('returns initials from a two-word name', () => {
    expect(getUserInitials('Dave Moore')).toBe('DM')
  })

  it('returns initials from a multi-word name (first and last)', () => {
    expect(getUserInitials('Mary Jane Watson')).toBe('MW')
  })

  it('returns a single initial for a single-word name', () => {
    expect(getUserInitials('elastic')).toBe('E')
  })

  it('returns "?" for null/undefined', () => {
    expect(getUserInitials(null)).toBe('?')
    expect(getUserInitials(undefined)).toBe('?')
  })
})
